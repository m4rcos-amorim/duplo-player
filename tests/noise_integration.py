"""Real VLC noise reduction, timestamps, controls, seeks and recorded AAC."""
import os
from pathlib import Path
import sys
import subprocess
import time
import wave
import json
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import imageio_ffmpeg
from PySide6.QtWidgets import QApplication
from duplo.window import PlayerWindow
app=QApplication([])
output=ROOT/'test-output/noise';output.mkdir(exist_ok=True)
wav=output/'noisy-stereo.wav';video=output/'noisy-stereo.mkv'
if not video.exists():
    rng=np.random.default_rng(41)
    n=24*48000;t=np.arange(n)/48000
    pcm=rng.normal(0,650,(n,2))
    pcm[10*48000:]+=(3500*np.sin(2*np.pi*1000*t[10*48000:]))[:,None]
    with wave.open(str(wav),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(48000)
        f.writeframes(np.rint(pcm).astype(np.int16).tobytes())
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-n','-f','lavfi','-i',
        'color=c=gray:s=320x180:r=30','-i',str(wav),'-shortest','-c:v','libx264',
        '-preset','ultrafast','-c:a','pcm_s16le',str(video)],check=True,timeout=90)
window=PlayerWindow(silent=True,settings=False)
window.show()

def pump(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        app.processEvents();time.sleep(.005)

def wait(predicate,timeout=20):
    end=time.monotonic()+timeout
    while not predicate():
        pump(.02)
        assert time.monotonic()<end,'Timed out'

def compare():
    audio=window.engine.audio;start=audio.clock()-200000
    with audio._lock:blocks=list(audio._blocks)
    raw=audio._render(blocks,start,4800)
    heard=audio.pcm(start,4800)
    recorded=audio.recording_pcm(start,4800)
    rms=lambda b:float(np.sqrt(np.mean(np.frombuffer(b,np.int16).astype(float)**2)))
    original,clean=rms(raw),rms(heard)
    assert original>300,original
    assert abs(rms(recorded)/max(1,clean)-.2)<.005
    return clean/original,original,clean

try:
    window.volume.setValue(20)
    window.add_paths([video])
    wait(lambda:window.engine.audio.sample_count>48000 and window.views[0].frame is not None)
    wait(lambda: window.engine.player.get_time() >= 500)
    pump(.3)
    ratio,_,_=compare();assert ratio==1.0,ratio
    window.noise_button.click()
    ratios=[]
    for strength in (35,65,100):
        window.noise_strength.setValue(strength)
        pump(.4)
        ratio,raw,clean=compare();ratios.append(ratio)
    assert ratios[0]<.85 and ratios[1]<ratios[0] and ratios[2]<ratios[1],ratios
    window.recorder.start(output)
    pump(.9)
    window.recorder.stop()
    wait(lambda:not window.recorder.finishing)
    assert not window.recorder.error,window.recorder.error
    path=window.recorder.path
    pcm=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(path),'-vn',
        '-f','f32le','-ar','48000','-ac','2','pipe:1'],capture_output=True,check=True).stdout
    samples=np.frombuffer(pcm,np.float32).reshape(-1,2)
    rms=float(np.sqrt(np.mean(samples**2)))
    expected=650/32768*.2
    assert .02 < rms/expected < .55,(rms,expected)
    window.engine.seek(13000)
    pump(.7)
    ratio,_,_=compare();assert ratio>.85,ratio
    window.speed.setCurrentIndex(window.speed.findData(.5))
    pump(.4)
    assert window.engine.audio.noise_level==100
    window.noise_button.click()
    pump(.4)
    audio=window.engine.audio;start=audio.clock()-100000
    with audio._lock:blocks=list(audio._blocks)
    assert audio.pcm(start,2400)==audio._render(blocks,start,2400)
    assert not audio.error,audio.error
    report={'result':'PASS','noise_ratios':ratios,'preserved_tone_ratio':ratio,
        'recorded_mp4':str(path),'recorded_noise_rms':rms,'stereo':True,
        'seek_slow_motion_disable':True}
    (output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
finally:
    window.close();app.processEvents()
