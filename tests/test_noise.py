import unittest
import numpy as np
from duplo.noise import NoiseSuppressor


def filtered(samples, chunks=(1024,)):
    processor = NoiseSuppressor()
    parts = {level: [] for level in (100,)}
    k = index = 0
    while k < len(samples):
        end = min(len(samples), k + chunks[index % len(chunks)])
        output = processor.process(samples[k:end].tobytes(), 1000000 + k * 1000000 // 48000)
        if output:
            for level, data in output[1].items():
                parts[level].append(np.frombuffer(data, np.int16).reshape(-1, 2))
        k, index = end, index + 1
    output = processor.drain()
    if output:
        for level, data in output[1].items():
            parts[level].append(np.frombuffer(data, np.int16).reshape(-1, 2))
    return processor, {level: np.concatenate(blocks) for level, blocks in parts.items()}


class NoiseTests(unittest.TestCase):
    def test_noise_reduction_increases_and_preserves_main_signal(self):
        rng = np.random.default_rng(12)
        time = np.arange(144000) / 48000
        data = rng.normal(0, 650, (144000, 2))
        data[48000:] += (3500 * np.sin(2 * np.pi * 1000 * time[48000:]))[:, None]
        data = np.rint(data).astype(np.int16)
        _, outputs = filtered(data)
        ratios = []
        for percent in (35, 65, 100):
            clean = np.rint(data.astype(float) + percent / 100 * (outputs[100].astype(float) - data))
            self.assertEqual(len(clean), len(data))
            ratio = np.sqrt(np.mean(clean[24000:47000].astype(float)**2)) / np.sqrt(np.mean(data[24000:47000].astype(float)**2))
            ratios.append(ratio)
            amplitude = 2 * np.mean(clean[72000:120000, 0] * np.sin(2*np.pi*1000*time[72000:120000])) / 3500
            self.assertGreater(amplitude, .9)
        self.assertLess(ratios[0], .85)
        self.assertLess(ratios[1], ratios[0])
        self.assertLess(ratios[2], ratios[1])
        self.assertLess(ratios[2], .5)

    def test_irregular_chunks_have_identical_samples_and_exact_duration(self):
        samples = np.random.default_rng(23).integers(-2000, 2000, (48017, 2), dtype=np.int16)
        _, a = filtered(samples)
        processor, b = filtered(samples, (13, 771, 1011, 4096, 63))
        for level in (100,):
            np.testing.assert_array_equal(a[level], b[level])
            self.assertEqual(len(b[level]), 48017)
        self.assertIsNone(processor.drain())

    def test_shared_gain_preserves_stereo_phase(self):
        mono = np.rint(5000 * np.sin(2*np.pi*700*np.arange(48000)/48000)).astype(np.int16)
        samples = np.column_stack((mono, -mono))
        _, outputs = filtered(samples)
        for clean in outputs.values():
            np.testing.assert_array_equal(clean[:, 0], -clean[:, 1])

    def test_discontinuity_does_not_reuse_previous_audio(self):
        processor = NoiseSuppressor()
        processor.process(np.full((4096,2), 12000, dtype=np.int16).tobytes(), 1000000)
        result = processor.process(bytes(4096 * 4), 4000000)
        self.assertEqual(result[0], 4000000)
        self.assertTrue(all(not any(data) for data in result[1].values()))

    def test_silence_and_reset_are_safe(self):
        processor, outputs = filtered(np.zeros((4096, 2), dtype=np.int16))
        self.assertTrue(all(not output.any() for output in outputs.values()))
        processor.reset()
        self.assertIsNone(processor.drain())
