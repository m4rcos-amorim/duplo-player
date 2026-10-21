"""Real composed MP4, decoded pixels, audio, pause, zoom, repeat and slow motion."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from array import array
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import imageio_ffmpeg
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox
from duplo.window import PlayerWindow, vlc
from duplo.model import Repeat
from duplo.recording import compose_video

app = QApplication([])
output = ROOT / 'test-output' / 'recording'
output.mkdir(parents=True, exist_ok=True)
results = []
errors = []

def pump(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(.005)

def wait(predicate, timeout=12):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        pump(.01)
        if predicate():
            return
    raise AssertionError('Timeout waiting for media')

def run():
    window = PlayerWindow(silent=True, settings=False)
    window.show()
    try:
        window.noise_strength.setValue(100)
        window.noise_button.click()
        window.add_paths([ROOT / 'test-output' / 'teste_principal.mp4'])
        wait(lambda: window.views[0].frame is not None and window.engine.audio.sample_count > 0)
        window.toggle_split()
        pump(.2)
        window.views[0].crop = QRectF(.05,.1,.35,.7)
        window.views[1].crop = QRectF(.6,.2,.35,.6)
        window.views[0].rotate_clockwise()
        for _ in range(3):
            window.views[1].rotate_clockwise()
        saved = [QRectF(view.crop) for view in window.views]
        window.repeat.setCurrentIndex(window.repeat.findData(Repeat.ONE))
        window.engine.seek(6400)
        wait(lambda: window.engine.player.get_state() == vlc.State.Playing and 0 < window.engine.player.get_time() < 2000 and window.views[0].frame is not None)
        assert window.split and [view.crop for view in window.views] == saved
        assert window.engine.audio.noise_level == 100
        assert [view.rotation for view in window.views] == [90, 270]
        results.append('real repeat preserves division, crops and independent rotations')
        window.speed.setCurrentIndex(window.speed.findData(.5))
        captured = []
        def capture(*args):
            image = compose_video(*args)
            if not captured:
                captured.append(image.copy())
            return image
        with patch('duplo.recording.compose_video', side_effect=capture):
            window.recorder.start(output)
            pump(2)
            window.engine.player.set_pause(1)
            pump(.5)
            window.engine.player.set_pause(0)
            window.toggle_fullscreen()
            pump(1)
            window.recorder.stop()
            wait(lambda: not window.recorder.finishing)
            pump(.3)
        assert not window.recorder.error, window.recorder.error
        assert not errors, errors
        path = window.recorder.path
        assert path.is_file() and path.stat().st_size > 10000
        reader = imageio_ffmpeg.read_frames(str(path), pix_fmt='rgb24')
        meta = next(reader)
        pixels = next(reader)
        reader.close()
        w,h = meta['size']
        decoded = QImage(pixels,w,h,w*3,QImage.Format.Format_RGB888).copy()
        decoded.save(str(output / 'first-recorded-frame.png'))
        expected = captured[0].convertToFormat(QImage.Format.Format_RGB888)
        assert (w,h) == (expected.width(),expected.height())
        a,b=bytes(decoded.constBits()),bytes(expected.constBits())
        # Ignore row padding; both sides have equal stride for this output.
        error=sum(abs(x-y) for x,y in zip(a,b))/len(a)
        assert error < 12, error
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        pcm=subprocess.run([ffmpeg,'-v','error','-i',str(path),'-vn','-f','f32le','-ac','1','-ar','48000','pipe:1'],capture_output=True,check=True).stdout
        samples=array('f');samples.frombytes(pcm)
        rms=(sum(x*x for x in samples)/len(samples))**.5
        assert rms > .01, rms
        pause_samples = samples[int(2.15*48000):int(2.35*48000)]
        pause_rms=(sum(x*x for x in pause_samples)/len(pause_samples))**.5
        assert pause_rms < .001, pause_rms
        assert 3.0 < meta['duration'] < 4.5, meta
        results.append({'composed_mp4':str(path),'size':[w,h],'duration':meta['duration'],
            'pixel_mean_error':round(error,2),'audio_rms':round(rms,4),
            'noise_suppression':100,'dual_zoom':True,'rotations':[view.rotation for view in window.views],'slow_motion':True,'pause':True,'fullscreen_transition':True})
        # No source audio also yields a valid silent AAC track.
        window.engine.player.set_pause(1)
        pump(.1)
        window.recorder.start(output)
        pump(.5)
        window.recorder.stop()
        wait(lambda: not window.recorder.finishing)
        assert window.recorder.path.is_file()
        results.append('second recording finalized')
        window.recorder.start(output)
        pump(.5)
        window.close()
        wait(lambda: not window.isVisible() and not window.recorder.finishing)
        assert window.recorder.path.is_file() and not window.recorder.error
        results.append('closing player finalizes active recording')
    finally:
        window.close()
        pump(.2)
    (output/'results.json').write_text(json.dumps({'result':'PASS','checks':results},indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2),flush=True)

with patch.object(QMessageBox,'warning',side_effect=lambda *args: errors.append(str(args[-1]))):
    run()
