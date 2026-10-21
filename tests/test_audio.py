from array import array
from collections import deque
import threading
import unittest
from unittest.mock import MagicMock, patch
from duplo.audio import AudioBridge


class PCMTests(unittest.TestCase):
    def setUp(self):
        self.audio = AudioBridge.__new__(AudioBridge)
        self.audio._lock = threading.Lock()
        self.audio._blocks = deque()
        self.audio._record_blocks = deque()
        self.audio._filtered_blocks = {level: deque() for level in (100,)}
        self.audio._record_filtered_blocks = {level: deque() for level in (100,)}
        self.audio._suppressor = MagicMock()
        self.audio.noise_level = 0
        self.audio._noise_changes = deque([(0, 0)])
        self.audio.clock = lambda: 1005000
        self.audio.paused = False
        self.audio.generation = 0
        self.audio.volume = 100
        self.audio.muted = False
        self.audio.sink = None
        self.audio._gain_changes = deque([(0, 1.0)])

    def test_scheduled_pcm_and_gap_have_correct_samples(self):
        self.audio._blocks.append((1000000, bytes([1,2,3,4]) * 480))
        self.audio._blocks.append((1020000, bytes([5,6,7,8]) * 480))
        result = self.audio.pcm(1000000, 1440)
        self.assertEqual(result[:1920], bytes([1,2,3,4]) * 480)
        self.assertEqual(result[1920:3840], bytes(1920))
        self.assertEqual(result[3840:], bytes([5,6,7,8]) * 480)
        self.assertEqual(self.audio.pcm(1005000, 240), bytes([1,2,3,4]) * 240)

    def test_pause_and_seek_do_not_reuse_audio(self):
        self.audio._blocks.append((1000000, bytes([1,2,3,4]) * 480))
        self.audio.paused = True
        self.assertEqual(self.audio.pcm(1000000,480), bytes(1920))
        self.audio.clear()
        self.assertEqual(self.audio.generation,1)
        self.assertFalse(self.audio.paused)
        self.assertEqual(self.audio.pcm(1000000,480), bytes(1920))

    def test_seek_keeps_already_played_samples_for_recording_only(self):
        self.audio._blocks.append((1000000, bytes([1,2,3,4]) * 480))
        self.audio._record_blocks.extend(self.audio._blocks)
        self.audio._record_blocks.append((2000000, bytes([5,6,7,8]) * 480))
        self.audio.clear()
        self.assertEqual(self.audio.pcm(1000000,480), bytes(1920))
        self.assertEqual(self.audio.recording_pcm(1000000,480), bytes([1,2,3,4]) * 240 + bytes(960))
        self.assertEqual(self.audio.recording_pcm(2000000,480), bytes(1920))

    def test_recording_tracks_volume_and_mute_at_sample_timestamps(self):
        raw = array('h', [20000, -20000] * 480).tobytes()
        self.audio._record_blocks.append((1000000, raw))
        self.audio._gain_changes = deque([(0, 1.0), (1002500, .1), (1007500, 0.0)])
        samples = array('h')
        samples.frombytes(self.audio.recording_pcm(1000000, 480))
        self.assertEqual(samples[:240], array('h', [20000, -20000] * 120))
        self.assertEqual(samples[240:720], array('h', [2000, -2000] * 240))
        self.assertEqual(samples[720:], array('h', [0, 0] * 120))

    def test_mute_preserves_selected_volume_and_updates_live_output(self):
        self.audio.sink = MagicMock()
        self.audio.set_volume(12)
        self.audio.sink.setVolume.assert_called_with(.12)
        self.audio.set_muted(True)
        self.audio.set_volume(7)
        self.audio.sink.setVolume.assert_called_with(0.0)
        self.assertEqual(self.audio.volume, 7)
        self.audio.set_muted(False)
        self.audio.sink.setVolume.assert_called_with(.07)

    def test_output_never_starts_at_full_volume_on_load_or_reset(self):
        class Sink:
            def __init__(self, *args):
                self.level = 1.0
                self.started_at = []
            def setBufferSize(self, value): pass
            def setVolume(self, value): self.level = value
            def reset(self): self.level = 1.0
            def start(self):
                self.started_at.append(self.level)
                self.level = 1.0  # Simulate a backend restoring its own default.
                return MagicMock()
            def state(self): return type('State', (), {'name': 'IdleState'})()
            def bytesFree(self): return 0
        self.audio.silent = False
        self.audio.format = None
        self.audio._output_generation = -1
        self.audio._blocks.append((1000000, bytes(1920)))
        output = MagicMock()
        output.isNull.return_value = False
        output.isFormatSupported.return_value = True
        with patch('duplo.audio.QMediaDevices.defaultAudioOutput', return_value=output), \
             patch('duplo.audio.QAudioSink', Sink):
            self.audio.set_volume(9)
            self.audio.pump()
            self.assertEqual(self.audio.sink.level, .09)
            self.audio.clear()
            self.audio.pump()
            self.assertEqual(self.audio.sink.started_at, [.09, .09])
            self.assertEqual(self.audio.sink.level, .09)
            self.audio.set_muted(True)
            self.audio.clear()
            self.audio.pump()
            self.assertEqual(self.audio.sink.started_at[-1], 0.0)
            self.assertEqual(self.audio.sink.level, 0.0)

    def test_vlc_startup_volume_callback_cannot_override_slider(self):
        player, vlc = MagicMock(), MagicMock()
        vlc.libvlc_clock.return_value = 1000000
        audio = AudioBridge(player, vlc, silent=True)
        audio.set_volume(4)
        audio.volume_callback(None, 1.0, False)
        self.assertEqual(audio.gain, .04)
        audio.set_muted(True)
        audio.volume_callback(None, 1.0, False)
        self.assertEqual(audio.gain, 0.0)

    def test_noise_change_timeline_is_identical_for_playback_and_recording(self):
        raw = array('h', [4000, -4000] * 480).tobytes()
        clean = array('h', [1000, -1000] * 480).tobytes()
        self.audio._blocks.append((1000000, raw))
        self.audio._record_blocks.append((1000000, raw))
        self.audio._filtered_blocks[100].append((1000000, clean))
        self.audio._record_filtered_blocks[100].append((1000000, clean))
        self.audio._noise_changes = deque([(0, 0), (1002500, 50), (1007500, 0)])
        samples = array('h')
        samples.frombytes(self.audio.pcm(1000000, 480))
        self.assertEqual(samples[:240], array('h', [4000, -4000] * 120))
        self.assertEqual(samples[240:720], array('h', [2500, -2500] * 240))
        self.assertEqual(samples[720:], array('h', [4000, -4000] * 120))
        self.assertEqual(self.audio.recording_pcm(1000000, 480), samples.tobytes())

    def test_every_percentage_is_applied_and_clamped(self):
        raw = array('h', [4000, -4000] * 480).tobytes()
        clean = array('h', [1000, -1000] * 480).tobytes()
        self.audio._blocks.append((1000000, raw))
        self.audio._record_blocks.append((1000000, raw))
        self.audio._filtered_blocks[100].append((1000000, clean))
        self.audio._record_filtered_blocks[100].append((1000000, clean))
        for percent in range(101):
            self.audio._noise_changes = deque([(0, percent)])
            expected = array('h', [4000 - 30 * percent, -4000 + 30 * percent] * 480).tobytes()
            self.assertEqual(self.audio.pcm(1000000, 480), expected)
            self.assertEqual(self.audio.recording_pcm(1000000, 480), expected)
        self.audio.set_noise(135)
        self.assertEqual(self.audio.noise_level, 100)
        self.audio.set_noise(-5)
        self.assertEqual(self.audio.noise_level, 0)

    def test_seek_clears_filtered_future_and_keeps_recorded_past(self):
        data = array('h', [1000, -1000] * 480).tobytes()
        self.audio._filtered_blocks[100].append((1000000, data))
        self.audio._record_filtered_blocks[100].append((1000000, data))
        self.audio._record_filtered_blocks[100].append((2000000, data))
        self.audio._noise_changes = deque([(0, 100)])
        self.audio.clear()
        self.audio._suppressor.reset.assert_called_once()
        self.assertEqual(self.audio.pcm(1000000,480), bytes(1920))
        self.assertEqual(self.audio.recording_pcm(1000000,480), data[:960] + bytes(960))
        self.assertEqual(self.audio.recording_pcm(2000000,480), bytes(1920))
