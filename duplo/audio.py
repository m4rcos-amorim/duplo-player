"""Timestamped VLC PCM shared by local playback and the composed recording.

VLC callbacks filter PCM into bounded rings; Qt objects stay on the UI thread.
No microphone or other application's sound is captured.
"""
from array import array
from collections import deque
import ctypes
import threading
import numpy as np

from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

from .i18n import tr
from .noise import NoiseSuppressor


class AudioBridge:
    RATE = 48000
    CHANNELS = 2
    BYTES_PER_FRAME = 4

    def __init__(self, player, vlc, silent=False):
        self.clock = vlc.libvlc_clock
        self.silent = silent
        self.format = QAudioFormat()
        self.format.setSampleRate(self.RATE)
        self.format.setChannelCount(self.CHANNELS)
        self.format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self._lock = threading.Lock()
        self._blocks = deque()
        self._record_blocks = deque()
        self._filtered_blocks = {level: deque() for level in (100,)}
        self._record_filtered_blocks = {level: deque() for level in (100,)}
        self._suppressor = NoiseSuppressor()
        self.noise_level = 0
        self._noise_changes = deque([(0, 0)])
        self.volume = 80
        self.muted = False
        self._gain_changes = deque([(0, self.gain)])
        self.paused = False
        self.generation = 0
        self._output_generation = -1
        self.sink = self.device = None
        self.cursor = 0
        self.sample_count = 0
        self.error = None
        Play = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.c_uint, ctypes.c_int64)
        Timed = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
        Drain = ctypes.CFUNCTYPE(None, ctypes.c_void_p)

        def play(opaque, samples, count, pts):
            try:
                data = ctypes.string_at(samples, count * self.BYTES_PER_FRAME)
                with self._lock:
                    self._blocks.append((pts, data))
                    if not self.paused:
                        self._record_blocks.append((pts, data))
                    while self._record_blocks and pts - self._record_blocks[0][0] > 3000000:
                        self._record_blocks.popleft()
                    self._append_filtered(self._suppressor.process(data, pts))
                    self.sample_count += count
                    # Retain at most three seconds, including scheduled samples.
                    while self._blocks and (len(self._blocks) > 300 or
                            pts - self._blocks[0][0] > 3000000):
                        self._blocks.popleft()
            except Exception as exc:
                self.error = str(exc)

        def pause(opaque, pts):
            with self._lock:
                self.paused = True
                self._trim_recording(pts)

        def resume(opaque, pts):
            self.paused = False

        def flush(opaque, pts):
            self.clear()

        def drain(opaque):
            try:
                with self._lock:
                    self._append_filtered(self._suppressor.drain())
            except Exception as exc:
                self.error = str(exc)

        self.callbacks = (Play(play), Timed(pause), Timed(resume), Timed(flush), Drain(drain))
        player.audio_set_callbacks(*self.callbacks, None)
        player.audio_set_format('S16N', self.RATE, self.CHANNELS)
        # Keep decoded PCM at native gain. The UI owns playback volume in Qt;
        # startup notifications from VLC must not reset it or scale PCM twice.
        Volume = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_bool)
        self.volume_callback = Volume(lambda opaque, volume, muted: None)
        player.audio_set_volume_callback(self.volume_callback)

    def _append_filtered(self, result):
        if result is None:
            return
        pts, outputs = result
        for level, data in outputs.items():
            blocks = self._filtered_blocks[level]
            blocks.append((pts, data))
            while blocks and pts - blocks[0][0] > 3000000:
                blocks.popleft()
            if not self.paused:
                recorded = self._record_filtered_blocks[level]
                recorded.append((pts, data))
                while recorded and pts - recorded[0][0] > 3000000:
                    recorded.popleft()

    def set_noise(self, level):
        level = max(0, min(100, int(level)))
        now = self.clock()
        with self._lock:
            self.noise_level = level
            if self._noise_changes[-1][1] != level:
                self._noise_changes.append((now, level))
            while len(self._noise_changes) > 1 and self._noise_changes[1][0] < now - 3000000:
                self._noise_changes.popleft()

    @property
    def gain(self):
        return 0.0 if self.muted else self.volume / 100.0

    def set_volume(self, value):
        self.volume = max(0, min(100, int(value)))
        self._update_gain()

    def set_muted(self, muted):
        self.muted = bool(muted)
        self._update_gain()

    def _update_gain(self):
        gain, now = self.gain, self.clock()
        with self._lock:
            if self._gain_changes[-1][1] != gain:
                self._gain_changes.append((now, gain))
            while len(self._gain_changes) > 1 and self._gain_changes[1][0] < now - 3000000:
                self._gain_changes.popleft()
        if self.sink is not None:
            self.sink.setVolume(gain)

    def _trim_recording(self, cutoff):
        self._record_blocks = self._trim_blocks(self._record_blocks, cutoff)
        for level in (100,):
            self._record_filtered_blocks[level] = self._trim_blocks(self._record_filtered_blocks[level], cutoff)

    def _trim_blocks(self, blocks, cutoff):
        kept = deque()
        for pts, data in blocks:
            frames = min(len(data) // 4, max(0, (cutoff - pts) * self.RATE // 1000000))
            if frames and pts > cutoff - 3000000:
                kept.append((pts, data[:frames * 4]))
        return kept

    def clear(self):
        with self._lock:
            # A seek/loop discards future output, but pending recording frames
            # still need the samples that already played before that transition.
            self._trim_recording(self.clock())
            self._blocks.clear()
            for blocks in self._filtered_blocks.values():
                blocks.clear()
            self._suppressor.reset()
            self.generation += 1
        self.paused = False

    def pcm(self, start, frames):
        if self.paused:
            return bytes(frames * self.BYTES_PER_FRAME)
        with self._lock:
            blocks = list(self._blocks)
            filtered = {level: list(items) for level, items in self._filtered_blocks.items()}
            changes = list(self._noise_changes)
        return self._noise_pcm(blocks, filtered, changes, start, frames)

    def recording_pcm(self, start, frames):
        with self._lock:
            blocks = list(self._record_blocks)
            filtered = {level: list(items) for level, items in self._record_filtered_blocks.items()}
            changes = list(self._noise_changes)
        raw = self._noise_pcm(blocks, filtered, changes, start, frames)
        with self._lock:
            gains = list(self._gain_changes)
        # The recorder runs slightly behind playback. Apply the gain that was
        # active at each sample timestamp, including changes and mute mid-block.
        samples = array('h')
        samples.frombytes(raw)
        current, offset = gains[0][1], 0
        for pts, gain in gains:
            target = max(0, min(frames, round((pts - start) * self.RATE / 1000000)))
            if target > offset:
                self._scale_samples(samples, offset * 2, target * 2, current)
                offset = target
            current = gain
        self._scale_samples(samples, offset * 2, frames * 2, current)
        return samples.tobytes()

    def _noise_pcm(self, blocks, filtered, changes, start, frames):
        raw = self._render(blocks, start, frames)
        clean = None
        result = bytearray(frames * 4)
        level, offset = changes[0][1], 0
        def copy_until(end):
            nonlocal clean
            a, b = offset * 4, end * 4
            if level == 0:
                result[a:b] = raw[a:b]
                return
            if clean is None:
                clean = self._render(filtered[100], start, frames)
            if level == 100:
                result[a:b] = clean[a:b]
                return
            original = np.frombuffer(raw[a:b], np.int16).astype(np.float64)
            reduced = np.frombuffer(clean[a:b], np.int16).astype(np.float64)
            mixed = np.rint(original + (level / 100) * (reduced - original))
            result[a:b] = mixed.astype(np.int16).tobytes()
        for pts, value in changes:
            target = max(0, min(frames, round((pts - start) * self.RATE / 1000000)))
            if target > offset:
                copy_until(target)
                offset = target
            level = value
        copy_until(frames)
        return bytes(result)

    @staticmethod
    def _scale_samples(samples, start, end, gain):
        if gain != 1.0:
            for i in range(start, end):
                samples[i] = round(samples[i] * gain)

    def _render(self, blocks, start, frames):
        result = bytearray(frames * self.BYTES_PER_FRAME)
        end = start + frames * 1000000 // self.RATE
        for pts, data in blocks:
            count = len(data) // self.BYTES_PER_FRAME
            if pts >= end or pts + count * 1000000 // self.RATE <= start:
                continue
            offset = round((pts - start) * self.RATE / 1000000)
            source = max(0, -offset)
            target = max(0, offset)
            copied = min(count - source, frames - target)
            if copied > 0:
                a, b = target * 4, source * 4
                result[a:a + copied * 4] = data[b:b + copied * 4]
        return bytes(result)

    def pump(self):
        if self.silent:
            return
        if self.sink is None:
            with self._lock:
                if not self._blocks:
                    return
            output = QMediaDevices.defaultAudioOutput()
            if output.isNull() or not output.isFormatSupported(self.format):
                self.error = tr('audio.unavailable')
                return
            self.sink = QAudioSink(output, self.format)
            self.sink.setBufferSize(48000 * 4 // 10)
        if self._output_generation != self.generation:
            self.sink.reset()
            self.sink.setVolume(self.gain)
            self.device = self.sink.start()
            self.sink.setVolume(self.gain)
            self.cursor = self.clock()
            self._output_generation = self.generation
        if self.paused:
            self.sink.suspend()
            return
        if self.sink.state().name == 'SuspendedState':
            self.sink.resume()
            self.cursor = self.clock()
        now = self.clock()
        if self.cursor < now - 100000:
            self.cursor = now
        # Maintain ~40 ms of scheduling headroom rather than filling a huge
        # sound buffer. This keeps seek/AB and the displayed image responsive.
        ahead = max(0, now + 40000 - self.cursor)
        frames = min(self.sink.bytesFree() // 4, ahead * self.RATE // 1000000)
        if frames and self.device:
            written = self.device.write(self.pcm(self.cursor, frames))
            if written > 0:
                self.cursor += (written // 4) * 1000000 // self.RATE

    def close(self):
        if self.sink:
            self.sink.stop()
            self.sink = self.device = None
        self.clear()
