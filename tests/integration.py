"""Run with the real VLC, synthetic video files, and an offscreen Qt window."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import imageio_ffmpeg
from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from duplo.i18n import tr
from duplo.model import Repeat
from duplo.window import PlayerWindow, vlc

OUTPUT = ROOT / 'test-output'
OUTPUT.mkdir(exist_ok=True)
app = QApplication([])
# The offscreen Windows plugin has no system font database. Load installed
# fonts explicitly for readable screenshots; fonts are not redistributed.
for font in ('segoeui.ttf', 'segoeuib.ttf', 'seguisb.ttf'):
    QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / font))
results = []


def record(name, details='OK'):
    print(f'PASS: {name}: {details}', flush=True)
    results.append({'test': name, 'result': 'PASS', 'details': details})


def pump(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError('Timeout waiting for condition')


def make_fixture(name, codec, extra=(), duration=2, size='320x180', audio='aac'):
    path = OUTPUT / name
    if path.exists():
        return path
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    args = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi',
            '-i', f'testsrc2=size={size}:rate=30', '-f', 'lavfi', '-i',
            'sine=frequency=440:sample_rate=44100', '-t', str(duration),
            '-c:v', codec, *extra, '-pix_fmt', 'yuv420p', '-c:a', audio, str(path)]
    subprocess.run(args, check=True, capture_output=True, timeout=90)
    return path


def main():
    formats = [
        ('teste_principal.mp4', 'libx264', ('-preset', 'ultrafast'), 7, '960x540', 'aac'),
        ('teste_mkv.mkv', 'libx264', (), 2, '320x180', 'aac'),
        ('teste_avi.avi', 'mpeg4', (), 2, '320x180', 'mp3'),
        ('teste_mov.mov', 'libx264', (), 2, '320x180', 'aac'),
        ('teste_webm.webm', 'libvpx-vp9', ('-deadline', 'realtime'), 2, '320x180', 'libopus'),
        ('teste_wmv.wmv', 'wmv2', (), 2, '320x180', 'wmav2'),
        ('teste_mpeg.mpg', 'mpeg2video', (), 2, '320x180', 'mp2'),
        ('teste_ts.ts', 'libx264', (), 2, '320x180', 'aac'),
        ('teste_flv.flv', 'flv', (), 2, '320x180', 'mp3'),
        ('teste_hevc.mp4', 'libx265', ('-preset', 'ultrafast', '-x265-params', 'log-level=error'), 2, '320x180', 'aac'),
        ('teste_av1.mkv', 'libaom-av1', ('-cpu-used', '8', '-crf', '45'), 2, '320x180', 'aac'),
    ]
    fixtures = [make_fixture(*spec) for spec in formats]
    errors = []
    with patch.object(QMessageBox, 'warning', side_effect=lambda *args: errors.append(str(args[-1]))):
        window = PlayerWindow(silent=True, settings=False)
        window.show()
        pump(0.2)
        try:
            for fixture in fixtures:
                window.stop()
                if fixture not in window.playlist.items:
                    window.playlist.add([fixture])
                window.playlist.select(window.playlist.items.index(fixture))
                window.load_current()
                wait_for(lambda: window.views[0].frame is not None)
                assert not window.engine.callback_error, window.engine.callback_error
                assert window.views[0].frame.width() > 0
                assert window.engine.player.get_state() in (vlc.State.Playing, vlc.State.Paused)
                record('decoding ' + fixture.name,
                       f'{window.views[0].frame.width()}×{window.views[0].frame.height()}')

            window.playlist.select(0)
            window.load_current()
            wait_for(lambda: window.views[0].frame is not None)
            window.toggle_split()
            pump(0.1)
            for _ in range(20):
                pump(0.02)
                assert window.views[0].frame is window.views[1].frame
            record('sincronia das duas perspectivas', 'mesmo objeto QImage em 20 amostras')

            window.toggle_zoom()
            view = window.views[0]
            target = view.video_rect()
            start = QPoint(int(target.left() + target.width() * .1), int(target.top() + target.height() * .1))
            end = QPoint(int(target.left() + target.width() * .5), int(target.top() + target.height() * .6))
            QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseMove(view, end, delay=10)
            QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=end)
            assert view.crop.width() < .5
            assert window.views[1].crop == QRectF(0, 0, 1, 1)
            second = window.views[1]
            target2 = second.video_rect()
            second.apply_selection(QRectF(target2.x() + target2.width() * .6, target2.y() + target2.height() * .4,
                                          target2.width() * .3, target2.height() * .4))
            assert second.crop.x() > .59
            assert view.crop != second.crop
            # Ignore tiny clicks and selections completely outside the video.
            old = QRectF(view.crop)
            assert not view.apply_selection(QRectF(-200, -200, 10, 10))
            assert view.crop == old
            window.grab().save(str(OUTPUT / 'duas-perspectivas.png'))
            record('zoom por arraste e recortes independentes')
            window.activate_view(second)
            window.reset_zoom()
            assert second.crop == QRectF(0, 0, 1, 1)
            assert view.crop == old
            window.reset_all_zoom()
            window.toggle_zoom()
            record('restaurar somente a perspectiva ativa')

            window.play_pause()
            wait_for(lambda: window.engine.player.get_state() == vlc.State.Paused)
            paused_frame = window.engine.frame_number
            pump(.3)
            assert window.engine.player.get_state() == vlc.State.Paused
            # next_frame may produce a few queued decoder frames, then settles paused.
            window.frame_step()
            wait_for(lambda: window.engine.frame_number > paused_frame)
            assert window.engine.player.get_state() == vlc.State.Paused
            window.play_pause()
            wait_for(lambda: window.engine.player.get_state() == vlc.State.Playing)
            record('pause, step one frame and resume')

            window.speed.setCurrentIndex(window.speed.findData(.25))
            assert abs(window.engine.player.get_rate() - .25) < .01
            window.engine.seek(500)
            wait_for(lambda: 1000 <= window.engine.player.get_time() <= 2000, timeout=12)
            pump(.3)
            start_time = window.engine.player.get_time()
            start_frame = window.engine.frame_number
            pump(1.2)
            elapsed = window.engine.player.get_time() - start_time
            frames = window.engine.frame_number - start_frame
            assert 50 <= elapsed <= 650, (elapsed, frames)
            assert window.views[0].frame is window.views[1].frame
            record('slow motion 0.25×', f'advanced {elapsed} ms in 1.2 s after the seek settled')
            window.speed.setCurrentIndex(window.speed.findData(1.0))

            window.engine.seek(1000)
            wait_for(lambda: 800 <= window.engine.player.get_time() <= 1300)
            window.mark_a()
            wait_for(lambda: window.engine.player.get_time() >= window.loop.a + 650)
            window.mark_b()
            assert window.loop.enabled
            wraps = 0
            previous = window.engine.player.get_time()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                pump(.04)
                value = window.engine.player.get_time()
                if value < previous - 200:
                    wraps += 1
                previous = value
            assert wraps >= 2, wraps
            assert window.views[0].frame is window.views[1].frame
            record('A–B loop', f'{wraps} returns to point A')
            window.clear_ab()

            window.repeat.setCurrentIndex(1)
            current = window.playlist.current
            window.engine.seek(window.engine.player.get_length() - 450)
            pump(1.3)
            assert window.playlist.current == current
            assert window.engine.player.get_time() < 1800
            record('repeat video at the end')
            window.repeat.setCurrentIndex(0)
            window.engine.seek(window.engine.player.get_length() - 450)
            wait_for(lambda: window.playlist.index == 1)
            record('advance the list at the end')

            window.stop()
            window.playlist.select(len(window.playlist.items) - 1)
            window.repeat.setCurrentIndex(2)
            window.load_current()
            wait_for(lambda: window.engine.player.get_length() > 0)
            window.engine.seek(window.engine.player.get_length() - 400)
            wait_for(lambda: window.playlist.index == 0)
            record('repeat the list at the end')

            with patch('duplo.window.reveal_in_explorer') as explorer:
                window.reveal_file()
                explorer.assert_called_once_with(window.playlist.current)
            record('open folder selects the right file', 'Explorer call verified')

            def click_confirmation(text):
                for widget in app.topLevelWidgets():
                    if isinstance(widget, QMessageBox) and widget.isVisible():
                        for button in widget.buttons():
                            if button.text() == text:
                                button.click()
                                return
                raise AssertionError('Confirmation dialog not found')

            wait_for(lambda: window.engine.player.get_state() == vlc.State.Playing)
            old_file = window.playlist.current
            with patch('duplo.recycle.recycle') as recycle_call:
                QTimer.singleShot(100, lambda: click_confirmation(tr('trash.cancel')))
                window.trash_current()
                recycle_call.assert_not_called()
            assert old_file.exists()
            wait_for(lambda: window.engine.player.get_state() == vlc.State.Playing)
            record('cancelling the delete keeps the file and playback')

            with patch('duplo.recycle.recycle', side_effect=OSError('Simulated recycle failure')):
                QTimer.singleShot(100, lambda: click_confirmation(tr('trash.confirm')))
                window.trash_current()
            assert old_file.exists()
            assert old_file in window.playlist.items
            assert errors and 'Simulated recycle failure' in errors[-1]
            errors.pop()
            wait_for(lambda: window.engine.player.get_state() == vlc.State.Playing)
            record('Recycle Bin failure keeps the file and resumes playback')

            # Disposable, explicitly created copy only; never a personal video.
            trash_file = OUTPUT / 'DESCARTAVEL_TESTE_LIXEIRA.mp4'
            shutil.copyfile(fixtures[0], trash_file)
            window.playlist.add([trash_file])
            window.playlist.select(window.playlist.items.index(trash_file))
            window.load_current()
            wait_for(lambda: window.views[0].frame is not None)
            QTimer.singleShot(100, lambda: click_confirmation(tr('trash.confirm')))
            window.trash_current()
            assert not trash_file.exists()
            assert trash_file not in window.playlist.items
            record('real Windows Recycle Bin', 'disposable copy recycled; file removed from the list')

            assert not errors, errors
            window.stop()
            window.grab().save(str(OUTPUT / 'player-inicial.png'))
            record('stop releases playback')
        finally:
            window.close()
            app.processEvents()
    (OUTPUT / 'integration-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(results)} integration checks passed.', flush=True)


if __name__ == '__main__':
    main()
