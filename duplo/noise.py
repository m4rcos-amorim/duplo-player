"""Stereo streaming spectral suppression. Original PCM remains available.

A shared spectral gain preserves stereo phase/balance. Window overlap is
compensated in the sample timestamps; no Qt objects or file I/O are used here.
"""
import numpy as np

class NoiseSuppressor:
    RATE = 48000
    SIZE = 1024
    HOP = 512

    def __init__(self):
        self.window = np.sqrt(.5 - .5 * np.cos(2 * np.pi * np.arange(self.SIZE) / self.SIZE))[:, None]
        self.reset()

    def reset(self):
        self.pending = np.zeros((self.HOP, 2), dtype=np.float64)
        self.overlap = np.zeros((self.SIZE, 2), dtype=np.float64)
        self.base_pts = None
        self.input_frames = self.output_frames = 0
        self.discard = self.HOP
        self.drained = False
        self.noise = self.power = None
        self.last_gain = np.ones(self.SIZE // 2 + 1)

    def process(self, data, pts):
        if self.drained:
            self.reset()
        samples = np.frombuffer(data, dtype=np.int16).reshape(-1, 2).astype(np.float64)
        if self.base_pts is not None:
            expected = self.base_pts + self.input_frames * 1000000 // self.RATE
            if abs(pts - expected) > 2000:
                self.reset()
        if self.base_pts is None:
            self.base_pts = pts
        self.input_frames += len(samples)
        self.pending = np.concatenate((self.pending, samples))
        original, filtered = [], []
        while len(self.pending) >= self.SIZE:
            frame = self.pending[:self.SIZE]
            spectrum = np.fft.rfft(frame * self.window, axis=0)
            power = np.mean(np.abs(spectrum) ** 2, axis=1)
            if self.power is None:
                self.power = power.copy()
            else:
                self.power = .7 * self.power + .3 * power
            # Robust local floor avoids treating isolated voice harmonics as
            # noise. Slow updates retain a noise estimate during louder sounds.
            padded = np.pad(self.power, (0, (-len(power)) % 16), mode='edge')
            floor = np.repeat(np.quantile(padded.reshape(-1, 16), .4, axis=1), 16)[:len(power)] * 1.5
            if self.noise is None:
                self.noise = floor
            else:
                alpha = np.where(floor < self.noise * 1.5, .08, .002)
                self.noise += alpha * (floor - self.noise)
            gain = np.clip(1 - 1.25 * self.noise / (self.power + 1e-12), .12, 1.0)
            gain = np.convolve(np.pad(gain, (1, 1), mode='edge'), [.15, .7, .15], mode='valid')
            self.last_gain = .55 * self.last_gain + .45 * gain
            clean = np.fft.irfft(spectrum * self.last_gain[:, None], n=self.SIZE, axis=0) * self.window
            self.overlap += clean
            segment = self.overlap[:self.HOP].copy()
            self.overlap[:-self.HOP] = self.overlap[self.HOP:]
            self.overlap[-self.HOP:] = 0
            if self.discard:
                self.discard = 0
            else:
                original.append(frame[:self.HOP].copy())
                filtered.append(segment)
            self.pending = self.pending[self.HOP:]
        if not original:
            return None
        raw, clean = np.concatenate(original), np.concatenate(filtered)
        start = self.base_pts + self.output_frames * 1000000 // self.RATE
        self.output_frames += len(raw)
        pcm = np.clip(np.rint(clean), -32768, 32767).astype(np.int16)
        return start, {100: pcm.tobytes()}

    def drain(self):
        if self.base_pts is None or self.drained:
            return None
        remaining = self.input_frames - self.output_frames
        if remaining <= 0:
            return None
        pts = self.base_pts + self.input_frames * 1000000 // self.RATE
        result = self.process(bytes(self.SIZE * 4), pts)
        if result is None:
            return None
        start, outputs = result
        self.drained = True
        return start, {level: data[:remaining * 4] for level, data in outputs.items()}
