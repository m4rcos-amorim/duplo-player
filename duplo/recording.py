"""Record the two video crops onto one timeline, without player controls."""
from collections import deque
from datetime import datetime
import os
import queue
import subprocess
import threading
import wave
import imageio_ffmpeg
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QSize, QTimer, Signal

from .i18n import tr
from PySide6.QtGui import QImage, QPainter


RECORDINGS = Path('C:/Videos')


def compose_video(views, split, size, canvas_size):
    image = QImage(size, QImage.Format.Format_RGB32)
    image.fill(0xff000000)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    scale = min(size.width() / max(1, canvas_size.width()),
                size.height() / max(1, canvas_size.height()))
    painter.translate((size.width() - canvas_size.width() * scale) / 2,
                      (size.height() - canvas_size.height() * scale) / 2)
    painter.scale(scale, scale)
    for view in (views if split else views[:1]):
        if view.frame is None:
            continue
        target = QRectF(view.video_rect()).translated(view.pos())
        view.draw_video(painter, target)
    painter.end()
    return image


class ViewRecorder(QObject):
    changed = Signal(bool)
    saved = Signal(str)
    failed = Signal(str)
    completed = Signal(str, str)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.timer = QTimer(self)
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.pump)
        self.completed.connect(self._complete)
        self.active = self.finishing = False
        self.path = self.error = None
        self.video_number = self.audio_number = 0

    def start(self, folder=RECORDINGS):
        if self.active or self.finishing:
            return
        if self.window.views[0].frame is None:
            raise RuntimeError(tr('rec.no_frame'))
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        name = 'Duplo_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')
        self.path = folder / (name + '.mp4')
        self.work = folder / ('.' + name + '.work')
        self.work.mkdir()
        self.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        canvas = self.window.video_splitter.size()
        scale = min(1, 1920 / max(1, canvas.width()), 1080 / max(1, canvas.height()))
        self.size = QSize(max(2, int(canvas.width() * scale) // 2 * 2),
                          max(2, int(canvas.height() * scale) // 2 * 2))
        self.start_clock = self.window.engine.audio.clock()
        self.video_number = self.audio_number = 0
        self._capture_number = -1
        self._captures = deque()
        self._last_raw = self._capture()
        self.queue = queue.Queue(maxsize=10)
        self.stopping = threading.Event()
        self.error = None
        self.active = True
        self.worker = threading.Thread(target=self._encode, daemon=True, name='Duplo recording')
        self.worker.start()
        self.changed.emit(True)
        self.timer.start()

    def _capture(self):
        image = compose_video(self.window.views, self.window.split, self.size,
                              self.window.video_splitter.size())
        converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
        return bytes(converted.constBits())

    def pump(self):
        if not self.active:
            return
        elapsed = self.window.engine.audio.clock() - self.start_clock
        capture_number = max(0, elapsed) * 30 // 1000000
        if capture_number != self._capture_number:
            self._captures.append((capture_number, self._capture()))
            self._capture_number = capture_number
        # Delay enqueueing by 100 ms, allowing VLC's asynchronous decoded PCM
        # to arrive. Both the image and PCM retain their presentation time.
        due = max(0, elapsed - 100000) * 30 // 1000000
        self._enqueue_until(due)

    def _enqueue_until(self, due):
        while self.video_number <= due:
            while self._captures and self._captures[0][0] <= self.video_number:
                _, self._last_raw = self._captures.popleft()
            pts = self.start_clock + self.video_number * 1000000 // 30
            pcm = self.window.engine.audio.recording_pcm(pts, 1600)
            try:
                self.queue.put_nowait((self._last_raw, pcm))
            except queue.Full:
                self.error = tr('rec.fell_behind')
                self.stop(flush=False)
                return
            self.video_number += 1
            self.audio_number += 1

    def stop(self, flush=True):
        if not self.active:
            return
        if flush:
            self.pump()
            elapsed = self.window.engine.audio.clock() - self.start_clock
            self._enqueue_until(max(0, elapsed) * 30 // 1000000)
        self.timer.stop()
        self.active = False
        self.finishing = True
        self.stopping.set()
        self.changed.emit(False)

    def _encode(self):
        video = self.work / 'video.mp4'
        audio = self.work / 'audio.wav'
        log_path = self.work / 'encoder.log'
        process = None
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            with log_path.open('wb') as log, wave.open(str(audio), 'wb') as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(48000)
                command = [self.ffmpeg, '-hide_banner', '-loglevel', 'error', '-n',
                    '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{self.size.width()}x{self.size.height()}',
                    '-r', '30', '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
                    '-crf', '20', '-pix_fmt', 'yuv420p', str(video)]
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                           stderr=log, creationflags=flags)
                while True:
                    try:
                        raw, pcm = self.queue.get(timeout=.05)
                    except queue.Empty:
                        if self.stopping.is_set():
                            break
                        continue
                    process.stdin.write(raw)
                    wav.writeframesraw(pcm)
                process.stdin.close()
                if process.wait(timeout=30) != 0:
                    raise RuntimeError(tr('rec.encoder_failed'))
            mux = subprocess.run([self.ffmpeg, '-hide_banner', '-loglevel', 'error', '-n',
                '-i', str(video), '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart',
                str(self.path)], capture_output=True, timeout=120, creationflags=flags)
            if mux.returncode:
                raise RuntimeError(mux.stderr.decode('utf-8', errors='replace')[-1000:])
            # Remove only the three temporary files created by this recording.
            for temporary in (video, audio, log_path):
                temporary.unlink(missing_ok=True)
            self.work.rmdir()
            self.completed.emit(str(self.path), self.error or '')
        except Exception as exc:
            if process and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            self.completed.emit('', tr('rec.temp_kept', error=exc, work=self.work))

    def _complete(self, path, error):
        self.timer.stop()
        self.active = self.finishing = False
        self.error = error or None
        self.changed.emit(False)
        if path:
            self.saved.emit(path)
        if error:
            self.failed.emit(error)
