"""Real VLC/Qt volume, mute, reload, seek and recorded PCM regression checks."""
import os
from array import array
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from duplo.engine import Engine
app = QApplication([])
e = Engine()
checks = []

def pump(seconds, expected):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        e.audio.pump()
        if e.audio.sink is not None:
            assert abs(e.audio.sink.volume() - expected) < .001, e.audio.sink.volume()
        time.sleep(.005)

def wait_audio(expected):
    old = e.audio.sample_count
    end = time.monotonic() + 8
    while e.audio.sample_count <= old + 4800 or e.audio.sink is None:
        pump(.02, expected)
        assert time.monotonic() < end, 'No real PCM/output'
    pump(.5, expected)

def rms(data):
    samples = array('h')
    samples.frombytes(data)
    return (sum(x*x for x in samples) / len(samples)) ** .5

def check_recording_gain(gain):
    start = e.audio.clock() - 200000
    raw = rms(e.audio.pcm(start, 4800))
    recorded = rms(e.audio.recording_pcm(start, 4800))
    assert raw > 500, raw
    if gain:
        assert abs(recorded/raw - gain) < .002, (raw, recorded, gain)
    else:
        assert recorded == 0, recorded
    checks.append({'gain':gain,'raw_rms':round(raw,3),'recorded_rms':round(recorded,3)})

try:
    e.set_volume(7)
    for path in [ROOT/'test-output/teste_principal.mp4',
                 ROOT/'test-output/teste_principal.mp4',
                 ROOT/'test-output/teste_mkv.mkv']:
        e.load(path)
        wait_audio(.07)
        check_recording_gain(.07)
    e.set_muted(True)
    e.set_volume(3)
    pump(.4, 0.0)
    check_recording_gain(0.0)
    e.load(ROOT/'test-output/teste_principal.mp4')
    wait_audio(0.0)
    check_recording_gain(0.0)
    e.seek(1500)
    pump(.5, 0.0)
    e.set_muted(False)
    pump(.4, .03)
    check_recording_gain(.03)
    e.set_volume(0)
    pump(.4, 0.0)
    check_recording_gain(0.0)
    assert not e.audio.error, e.audio.error
    report={'result':'PASS','checks':checks,'first_output_volume':.07,
            'repeat_and_different_file':True,'mute_survives_reload_seek':True,
            'volume_zero_is_silent':True}
    (ROOT/'test-output/volume-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
finally:
    e.close()
