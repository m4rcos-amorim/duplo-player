"""LibVLC decodes once. Both views receive the exact same immutable QImage.

Callbacks run on VLC threads; a single latest-frame slot avoids accumulating
frames if the UI is busy. No Qt widget is accessed from the decoder threads.
"""
import ctypes
import os
from pathlib import Path
import sys
import threading

from PySide6.QtGui import QImage
from PySide6.QtCore import Qt

from .i18n import tr

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
VLC_DIR = ROOT / 'vendor' / 'vlc'
if not VLC_DIR.exists():
    VLC_DIR = Path(os.environ.get('DUPLO_VLC_DIR', r'C:\Program Files\VideoLAN\VLC'))
if sys.platform == 'win32' and VLC_DIR.exists():
    os.environ['PYTHON_VLC_LIB_PATH'] = str(VLC_DIR / 'libvlc.dll')
    os.environ['PYTHON_VLC_MODULE_PATH'] = str(VLC_DIR)
    os.environ['VLC_PLUGIN_PATH'] = str(VLC_DIR / 'plugins')
    _dll_handle = os.add_dll_directory(str(VLC_DIR))

import vlc  # environment and DLL search must be set first


class _NativeMediaTrack(ctypes.Structure):
    # libvlc_media_track_t contains ONE union pointer. The generated Python
    # binding models it as three consecutive pointers; don't use tracks_get.
    _fields_ = [('codec', ctypes.c_uint32), ('original_fourcc', ctypes.c_uint32),
                ('id', ctypes.c_int), ('type', ctypes.c_int), ('profile', ctypes.c_int),
                ('level', ctypes.c_int), ('detail', ctypes.c_void_p),
                ('bitrate', ctypes.c_uint), ('language', ctypes.c_char_p),
                ('description', ctypes.c_char_p)]


def _display_geometry(media):
    Tracks = ctypes.POINTER(ctypes.POINTER(_NativeMediaTrack))
    get_tracks = ctypes.CFUNCTYPE(ctypes.c_uint, ctypes.c_void_p, ctypes.POINTER(Tracks))(
        ('libvlc_media_tracks_get', vlc.dll))
    release_tracks = ctypes.CFUNCTYPE(None, Tracks, ctypes.c_uint)(
        ('libvlc_media_tracks_release', vlc.dll))
    tracks = Tracks()
    count = get_tracks(media._as_parameter_, ctypes.byref(tracks))
    try:
        for i in range(count):
            track = tracks[i].contents
            if track.type == vlc.TrackType.video.value and track.detail:
                video = ctypes.cast(track.detail, ctypes.POINTER(vlc.VideoTrack)).contents
                w, h = video.width, video.height
                if video.sar_num > 0 and video.sar_den > 0:
                    w = round(w * video.sar_num / video.sar_den)
                if video.orientation.value >= 4:
                    w, h = h, w
                return (w, h) if w > 0 and h > 0 else None
        return None
    finally:
        if count:
            release_tracks(tracks, count)


class Engine:
    def __init__(self, silent=False):
        options = ['--no-video-title-show', '--no-osd', '--no-snapshot-preview',
                   '--avcodec-hw=none', '--quiet', '--no-stats']
        if silent:
            options.append('--aout=dummy')
        self.instance = vlc.Instance(*options)
        if self.instance is None:
            raise RuntimeError(tr('engine.init_failed'))
        self.player = self.instance.media_player_new()
        self._mutex = threading.Lock()
        self._latest = None
        self._serial = 0
        self._consumed = -1
        self._buffers = {}
        self._pool = []
        self._width = self._height = self._pitch = 0
        self._media = None
        self.rate = 1.0
        self.volume = 80
        self.callback_error = None
        self._video_geometry = None

        # c_void_p for chroma is deliberate: c_char_p converts to Python bytes
        # and would make writing the four-byte format unsafe.
        Format = ctypes.CFUNCTYPE(ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p),
                                 ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint),
                                 ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint),
                                 ctypes.POINTER(ctypes.c_uint))
        Lock = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
        Unlock = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p,
                                 ctypes.POINTER(ctypes.c_void_p))
        Display = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)
        Cleanup = ctypes.CFUNCTYPE(None, ctypes.c_void_p)

        def setup(opaque, chroma, width, height, pitches, lines):
            try:
                w, h = self._video_geometry or (width[0], height[0])
                if not (0 < w <= 16384 and 0 < h <= 16384):
                    return 0
                # Input dimensions can include codec padding. Request the
                # display dimensions from parsed tracks instead.
                width[0], height[0] = w, h
                ctypes.memmove(chroma, b'RV32', 4)
                pitch = (w * 4 + 31) & ~31
                line_count = (h + 31) & ~31
                pitches[0], lines[0] = pitch, line_count
                with self._mutex:
                    self._width, self._height, self._pitch = w, h, pitch
                    self._pool = [self._allocate(w, h, pitch, line_count) for _ in range(3)]
                return 3
            except Exception as exc:
                self.callback_error = str(exc)
                return 0

        def lock(opaque, planes):
            with self._mutex:
                record = self._pool.pop() if self._pool else self._allocate(
                    self._width, self._height, self._pitch, (self._height + 31) & ~31)
                address = record[1]
                self._buffers[address] = record
                planes[0] = address
                return address

        def unlock(opaque, picture, planes):
            pass

        def display(opaque, picture):
            try:
                with self._mutex:
                    record = self._buffers.pop(picture, None)
                    if record is None:
                        return
                    raw, address, w, h, pitch = record
                    # RV32 has an unused fourth byte; Format_RGB32 ignores alpha.
                    pixels = ctypes.string_at(address, pitch * h)
                    self._latest = QImage(pixels, w, h, pitch, QImage.Format.Format_RGB32).copy()
                    self._serial += 1
                    if (w, h, pitch) == (self._width, self._height, self._pitch):
                        self._pool.append(record)
            except Exception as exc:
                self.callback_error = str(exc)

        self._callbacks = (Format(setup), Lock(lock), Unlock(unlock), Display(display), Cleanup(lambda _: None))
        setup_cb, lock_cb, unlock_cb, display_cb, cleanup_cb = self._callbacks
        self.player.video_set_callbacks(lock_cb, unlock_cb, display_cb, None)
        self.player.video_set_format_callbacks(setup_cb, cleanup_cb)

        from .audio import AudioBridge
        self.audio = AudioBridge(self.player, vlc, silent=silent)
        self.set_volume(self.volume)

    @staticmethod
    def _allocate(w, h, pitch, lines):
        raw = ctypes.create_string_buffer(pitch * lines + 31)
        address = (ctypes.addressof(raw) + 31) & ~31
        return raw, address, w, h, pitch

    def take_frame(self):
        with self._mutex:
            if self._consumed == self._serial:
                return None
            self._consumed = self._serial
            image = self._latest
        if image is None:
            return None
        # Some demuxers expose visible dimensions only once playback starts.
        if self._video_geometry is None and self._media is not None:
            self._video_geometry = _display_geometry(self._media)
        if self._video_geometry and (image.width(), image.height()) != self._video_geometry:
            image = image.scaled(*self._video_geometry, Qt.AspectRatioMode.IgnoreAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        return image

    @property
    def frame_number(self):
        with self._mutex:
            return self._serial

    def load(self, path):
        self.stop()
        self.callback_error = None
        self._media = self.instance.media_new_path(str(path))
        self._video_geometry = None
        self._media.parse()
        self._video_geometry = _display_geometry(self._media)
        self.player.set_media(self._media)
        self.set_volume(self.volume)
        self.player.play()
        self.player.set_rate(self.rate)

    def stop(self):
        self.player.stop()
        self.audio.clear()
        self.player.set_media(None)
        if self._media is not None:
            self._media.release()
            self._media = None
        with self._mutex:
            self._latest = None
            self._buffers.clear()
            self._pool.clear()
            self._serial += 1

    def seek(self, ms):
        length = self.player.get_length()
        self.player.set_time(max(0, min(int(ms), max(0, length - 1))))

    def set_volume(self, value):
        self.volume = max(0, min(100, int(value)))
        self.audio.set_volume(self.volume)

    @property
    def muted(self):
        return self.audio.muted

    def set_muted(self, muted):
        self.audio.set_muted(muted)

    def set_rate(self, rate):
        if self.player.set_rate(rate) == 0:
            self.rate = rate
            return True
        return False

    def close(self):
        self.stop()
        self.audio.close()
        self.player.release()
        self.instance.release()
