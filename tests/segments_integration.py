"""Real segments recorded with Ctrl+G, joined into one MP4 with Ctrl+Shift+G."""
import json
import os
import shutil
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
shutil.rmtree(output, ignore_errors=True)  # fresh T1, T2… numbering on every run
output.mkdir(parents=True)
segments_dir, joined_dir = output / 'trechos', output / 'joined'
results = []
errors = []

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
        # Ctrl+G records to C:\Videos\trechos; keep the test files in test-output.
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
            assert [path.name for path in segments] == ['teste_principal_T1.mp4', 'teste_principal_T2.mp4',
                                                        'teste_principal_T3.mp4'], segments
            assert all(path.parent == segments_dir for path in segments), segments
            assert window.join_button.isEnabled()
            probes = [probe(path) for path in segments]
            assert len({size for size, _, _ in probes}) == 1, probes
            joined = []
            window.recorder.joined.connect(lambda *args: joined.append(args))
            window.join_recordings()
            wait(lambda: joined)
            path, error, count = joined[0]
            assert path and not error and count == 3, joined
            size, duration, audio = probe(path)
            total = sum(item[1] for item in probes)
            assert size == probes[0][0] and audio, (size, audio)
            assert abs(duration - total) < .35, (duration, total)
            # The join creates a new file only: every segment recording is kept, only temporaries go.
            assert all(path.is_file() for path in segments), 'a segment recording was deleted'
            assert Path(path) == joined_dir / 'teste_principal_joined.mp4', path
            assert not list(output.rglob('.*.work')), list(output.rglob('.*.work'))
            assert window.recorder.segments == [] and not window.join_button.isEnabled()
            assert window.record_info.text().endswith(path), window.record_info.text()
            results.append({'joined_mp4': path, 'segments': 3, 'size': list(size), 'duration': duration,
                            'segment_durations': [item[1] for item in probes], 'aac_audio': audio,
                            'fullscreen_and_split_between_segments': True})
            # Ctrl+Shift+G while recording finishes that segment, then joins.
            joined.clear()
            first = record(window, .6)
            window.toggle_recording()
            pump(.6)
            window.join_recordings()
            wait(lambda: joined)
            path, error, count = joined[0]
            assert path and not error and count == 2, joined
            assert first.is_file() and window.recorder.path.is_file()
            assert first.name == 'teste_principal_T4.mp4', first
            assert Path(path) == joined_dir / 'teste_principal_joined_2.mp4', path
            results.append('join while recording finishes the segment first; segments kept')
            # A joined file shorter than its segments is discarded and the segments are kept.
            joined.clear()
            kept = [record(window, .6), record(window, .6)]
            joined_before = len(list(joined_dir.glob('*.mp4')))
            with patch('duplo.recording.media_duration', side_effect=lambda path: 0.0 if '_joined' in str(path) else 5.0):
                window.join_recordings()
                wait(lambda: joined)
            path, error, count = joined[0]
            assert not path and error and all(item.exists() for item in kept), joined
            assert len(list(joined_dir.glob('*.mp4'))) == joined_before, 'partial join left behind'
            assert not list(output.rglob('.*.work'))
            assert window.recorder.segments == kept
            errors.clear()
            results.append('incomplete join keeps the segments')
            window.recorder.segments = kept[:1]
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

with patch.object(QMessageBox, 'warning', side_effect=lambda *args: errors.append(str(args[-1]))):
    run()
