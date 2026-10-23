"""Real segments recorded with Ctrl+G, joined into one MP4 with Ctrl+Shift+G."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import imageio_ffmpeg
from PySide6.QtWidgets import QApplication, QMessageBox
from duplo.window import PlayerWindow

app = QApplication([])
output = ROOT / 'test-output' / 'segments'
output.mkdir(parents=True, exist_ok=True)
results = []
errors = []
discarded = []

def pump(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(.005)

def wait(predicate, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        pump(.01)
        if predicate():
            return
    raise AssertionError('Timeout waiting for the recorder')

def probe(path):
    reader = imageio_ffmpeg.read_frames(str(path), pix_fmt='rgb24')
    meta = next(reader)
    reader.close()
    streams = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-i', str(path)],
                             capture_output=True).stderr.decode('utf-8', errors='replace')
    return meta['size'], meta['duration'], 'Audio: aac' in streams

def record(window, seconds):
    window.toggle_recording()
    pump(seconds)
    window.toggle_recording()
    wait(lambda: not window.recorder.finishing)
    assert not window.recorder.error, window.recorder.error
    return window.recorder.path

def run():
    window = PlayerWindow(silent=True, settings=False)
    window.show()
    try:
        window.add_paths([ROOT / 'test-output' / 'teste_principal.mp4'])
        wait(lambda: window.views[0].frame is not None and window.engine.audio.sample_count > 0)
        start = window.recorder.start
        # Ctrl+G records to C:\Videos; keep the test files in test-output.
        with patch.object(window.recorder, 'start', lambda: start(output)):
            segments = [record(window, 1.0)]
            # A different window size and layout between segments still joins losslessly.
            window.toggle_fullscreen()
            pump(.3)
            segments.append(record(window, 1.2))
            window.toggle_fullscreen()
            window.toggle_split()
            pump(.3)
            segments.append(record(window, .8))
            assert window.recorder.segments == segments, window.recorder.segments
            assert window.join_button.isEnabled()
            probes = [probe(path) for path in segments]
            assert len({size for size, _, _ in probes}) == 1, probes
            joined = []
            window.recorder.joined.connect(lambda *args: joined.append(args))
            window.join_recordings()
            wait(lambda: joined)
            path, error, count, kept = joined[0]
            assert path and not error and count == 3 and not kept, joined
            size, duration, audio = probe(path)
            total = sum(item[1] for item in probes)
            assert size == probes[0][0] and audio, (size, audio)
            assert abs(duration - total) < .35, (duration, total)
            assert discarded == segments, discarded
            assert window.recorder.segments == [] and not window.join_button.isEnabled()
            assert window.record_info.text().endswith(path), window.record_info.text()
            results.append({'joined_mp4': path, 'segments': 3, 'size': list(size), 'duration': duration,
                            'segment_durations': [item[1] for item in probes], 'aac_audio': audio,
                            'fullscreen_and_split_between_segments': True})
            # Ctrl+Shift+G while recording finishes that segment, then joins.
            discarded.clear()
            joined.clear()
            first = record(window, .6)
            window.toggle_recording()
            pump(.6)
            window.join_recordings()
            wait(lambda: joined)
            path, error, count, kept = joined[0]
            assert path and not error and count == 2, joined
            assert discarded[0] == first and len(discarded) == 2, discarded
            results.append('join while recording finishes the segment first')
            window.join_recordings()
            assert not window.recorder.joining
            results.append('joining needs at least two segments')
        assert not errors, errors
    finally:
        window.close()
        pump(.2)
    (output / 'results.json').write_text(json.dumps({'result': 'PASS', 'checks': results}, indent=2),
                                         encoding='utf-8')
    print(json.dumps(results, indent=2), flush=True)

# The test keeps the segment files instead of sending them to the Recycle Bin.
with patch.object(QMessageBox, 'warning', side_effect=lambda *args: errors.append(str(args[-1]))), \
     patch('duplo.recording.ViewRecorder.discard_segment', side_effect=discarded.append):
    run()
