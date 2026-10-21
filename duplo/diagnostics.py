"""Opt-in smoke test of the actual distributed app. Never deletes files."""
import json
from pathlib import Path
import time
import traceback

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from .engine import vlc


def run_packaged_smoke(app, window, video, output):
    folder = Path(output) if output else Path(video).resolve().parent
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = {'result': 'RUNNING', 'vlc': vlc.libvlc_get_version().decode()}
    timer = QTimer(window)
    timer.setInterval(50)
    errors = []
    # Prevent a modal error dialog from hiding a failure in unattended tests.
    original_warning = QMessageBox.warning
    QMessageBox.warning = lambda *args: errors.append(str(args[-1]))

    def finish(code):
        timer.stop()
        QMessageBox.warning = original_warning
        (folder / 'packaged-smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        window.close()
        app.exit(code)

    def check():
        try:
            if errors:
                raise RuntimeError(errors[0])
            if time.monotonic() - started > 15:
                raise TimeoutError('Sem quadro decodificado em 15 segundos.')
            frame = window.views[0].frame
            if frame is None or window.engine.frame_number < 12:
                return
            if window.engine.audio.sink is None:
                return
            assert abs(window.engine.audio.sink.volume() - .07) < .001
            assert window.engine.volume == window.volume.value() == 7
            window.toggle_mute()
            assert window.engine.audio.sink.volume() == 0.0
            window.toggle_mute()
            assert abs(window.engine.audio.sink.volume() - .07) < .001
            report['low_volume_from_start_and_mute'] = True
            window.engine.player.set_pause(1)
            window.activateWindow()
            window.raise_()
            window.views[0].setFocus()
            QTest.qWait(100)
            QTest.keyClick(window.views[0], Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
            assert window.split and window.views[1].isVisible()
            for view, x in zip(window.views, (.05, .55)):
                target = view.video_rect()
                view.apply_selection(QRectF(target.x() + target.width() * x,
                                            target.y() + target.height() * .15,
                                            target.width() * .4, target.height() * .55))
            window.activate_view(window.views[1])
            assert window.views[0].frame is window.views[1].frame
            assert window.views[0].crop != window.views[1].crop
            window.activate_view(window.views[0])
            window.views[0].setFocus()
            for expected in (90, 180, 270, 0, 90):
                QTest.keyClick(window.views[0], Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
                assert window.views[0].rotation == expected
                assert window.views[1].rotation == 0
            QTest.mouseClick(window.views[1], Qt.MouseButton.LeftButton, pos=window.views[1].rect().center())
            for expected in (90, 180, 270):
                QTest.keyClick(window.views[1], Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
                assert window.views[1].rotation == expected
                assert window.views[0].rotation == 90
            report['ctrl_r_independent_rotation'] = [view.rotation for view in window.views]
            for expected in (.75, .5, .25, .25):
                QTest.keyClick(window.views[0], Qt.Key.Key_Minus)
                assert window.speed.currentData() == expected
                assert abs(window.engine.player.get_rate() - expected) < .01
            report['minus_slow_motion_limit'] = True
            for expected in (.5, .75, 1.0, 1.25, 1.5, 2.0, 2.0):
                QTest.keyClick(window.views[0], Qt.Key.Key_Plus)
                assert window.speed.currentData() == expected
                assert abs(window.engine.player.get_rate() - expected) < .01
            report['plus_restores_normal_and_limit_2x'] = True
            window.speed.setCurrentIndex(window.speed.findData(.5))
            assert abs(window.engine.player.get_rate() - .5) < .01
            # Verify native COM dependencies are present in the frozen build.
            import pythoncom
            from win32com.shell import shell
            pythoncom.CoInitialize()
            try:
                operation = pythoncom.CoCreateInstance(shell.CLSID_FileOperation, None,
                    pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IFileOperation)
                assert operation is not None
                operation = None
            finally:
                pythoncom.CoUninitialize()
            timer.stop()

            def capture():
                window.grab().save(str(folder / 'player-preview.png'))
                report.update(result='PASS', shared_frame=True,
                              resolution=[frame.width(), frame.height()],
                              independent_zoom=True, slow_motion=True,
                              recycle_api_available=True,
                              elapsed_seconds=round(time.monotonic() - started, 2))
                window.toggle_fullscreen()
                QTimer.singleShot(200, capture_fullscreen)

            def capture_fullscreen():
                try:
                    assert window.isFullScreen()
                    assert [view.rotation for view in window.views] == [90, 270]
                    window.activate_view(window.views[1])
                    window.views[1].setFocus()
                    for expected in (0, 90, 180, 270):
                        QTest.keyClick(window.views[1], Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
                        assert window.views[1].rotation == expected
                        assert window.views[0].rotation == 90
                    report['ctrl_r_fullscreen_cycle'] = True
                    assert window.engine.audio.noise_level == 100
                    QTest.keyClick(window.views[1], Qt.Key.Key_H, Qt.KeyboardModifier.ControlModifier)
                    assert window.engine.audio.noise_level == 0
                    QTest.keyClick(window.views[1], Qt.Key.Key_H, Qt.KeyboardModifier.ControlModifier)
                    assert window.engine.audio.noise_level == 100
                    report['noise_shortcut_fullscreen'] = True
                    window.speed.setCurrentIndex(window.speed.findData(1.0))
                    QTest.keyClick(window.views[0], Qt.Key.Key_Minus, Qt.KeyboardModifier.KeypadModifier)
                    assert window.speed.currentData() == .75
                    for expected in (.5, .25, .25):
                        QTest.keyClick(window.views[0], Qt.Key.Key_Minus)
                        assert window.speed.currentData() == expected
                        assert abs(window.engine.player.get_rate() - expected) < .01
                    report['minus_fullscreen_and_keypad'] = True
                    for modifiers in (Qt.KeyboardModifier.ShiftModifier, Qt.KeyboardModifier.KeypadModifier):
                        window.speed.setCurrentIndex(window.speed.findData(.25))
                        for expected in (.5, .75, 1.0, 1.25, 1.5, 2.0, 2.0):
                            QTest.keyClick(window.views[0], Qt.Key.Key_Plus, modifiers)
                            assert window.speed.currentData() == expected
                            assert abs(window.engine.player.get_rate() - expected) < .01
                    report['plus_fullscreen_shift_and_keypad'] = True
                    window.speed.setCurrentIndex(window.speed.findData(.5))
                    assert window.split and window.views[1].isVisible()
                    assert all(view.presentation for view in window.views)
                    assert not window.sidebar.isVisible()
                    assert all(not widget.isVisible() for widget in window._chrome_widgets)
                    saved_crops = [QRectF(view.crop) for view in window.views]
                    QTest.keyClick(window.active_view, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
                    assert not window.split and not window.views[1].isVisible()
                    QTest.keyClick(window.active_view, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
                    assert window.split and window.views[1].isVisible()
                    assert window.isFullScreen()
                    assert [view.crop for view in window.views] == saved_crops
                    report['ctrl_d_toggle_window_and_fullscreen'] = True
                    window.reset_all_zoom()
                    QTest.keyClick(window.active_view, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
                    assert all(view.selecting for view in window.views)
                    for view, x in zip(window.views, (.05, .55)):
                        target = view.video_rect()
                        start = QPoint(int(target.x() + target.width() * x), int(target.y() + target.height() * .15))
                        end = QPoint(int(start.x() + target.width() * .35), int(start.y() + target.height() * .5))
                        QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
                        QTest.mouseMove(view, end, delay=10)
                        QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=end)
                        assert view.crop.width() < .6 and view.crop.height() < .6
                    assert window.views[0].crop != window.views[1].crop
                    assert window._loaded
                    QTest.keyClick(window.active_view, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
                    assert all(not view.selecting for view in window.views)
                    report.update(video_only_fullscreen=True, fullscreen_division=True,
                                  playlist_hidden_by_default=not window._sidebar_before_fullscreen,
                                  ctrl_s_fullscreen_drag_zoom=True)
                    window.clear_ab()
                    window.activateWindow()
                    window.raise_()
                    window.active_view.setFocus()
                    QTest.qWait(80)
                    QTest.keyClick(window.active_view, Qt.Key.Key_3)
                    assert window.loop.a is not None and window.loop.b is None
                    window.engine.player.set_pause(0)
                    QTimer.singleShot(1200, capture_ab_end)
                except Exception as exc:
                    report.update(result='FAIL', error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
                    finish(1)
            def capture_ab_end(attempts=30):
                try:
                    if window.engine.player.get_time() < window.loop.a + 200:
                        if attempts:
                            QTimer.singleShot(100, lambda: capture_ab_end(attempts - 1))
                            return
                        raise TimeoutError('Playback did not advance far enough to set B.')
                    # A delayed diagnostic runs after OS focus may have moved.
                    # Restore player focus before dispatching a window shortcut.
                    for _ in range(3):
                        window.activateWindow()
                        window.raise_()
                        window.active_view.setFocus()
                        QTest.qWait(80)
                        QTest.keyClick(window.active_view, Qt.Key.Key_3)
                        if window.loop.enabled:
                            break
                    assert window.loop.enabled, f'A–B did not activate: A={window.loop.a}, B={window.loop.b}, position={window.engine.player.get_time()}' 
                    window.engine.player.set_pause(1)
                    assert window.views[0].frame is window.views[1].frame
                    window.grab().save(str(folder / 'fullscreen-preview.png'))
                    report['three_key_ab_marks'] = [window.loop.a, window.loop.b]
                    window.escape()
                    assert not window.isFullScreen()
                    assert window.views[0].crop != window.views[1].crop
                    report['fullscreen_exit_preserves_zoom'] = True
                    saved_crop = QRectF(window.views[0].crop)
                    QTest.mouseClick(window.views[1], Qt.MouseButton.LeftButton)
                    QTest.keyClick(window.views[1], Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
                    assert window.views[1].crop == QRectF(0, 0, 1, 1)
                    assert window.views[0].crop == saved_crop
                    report['ctrl_z_selected_zoom_only'] = True
                    window.views[1].crop = QRectF(.55, .15, .35, .5)
                    window.clear_ab()
                    window.engine.player.set_pause(0)
                    window.recorder.start()
                    QTimer.singleShot(2500, stop_recording)
                except Exception as exc:
                    report.update(result='FAIL', error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
                    finish(1)
            def stop_recording():
                window.recorder.stop()
                QTimer.singleShot(100, recording_done)

            def recording_done(attempts=300):
                try:
                    if window.recorder.active or window.recorder.finishing:
                        if attempts:
                            QTimer.singleShot(100, lambda: recording_done(attempts - 1))
                            return
                        raise TimeoutError('Recording did not finish within 30 seconds.')
                    assert not window.recorder.error, window.recorder.error
                    assert window.recorder.path.is_file()
                    assert window.recorder.path.stat().st_size > 10000
                    assert [view.rotation for view in window.views] == [90, 270]
                    report['recording_rotations'] = [view.rotation for view in window.views]
                    assert window.engine.audio.noise_level == 100
                    assert window.engine.audio._record_filtered_blocks[100]
                    report['recording_noise_suppression'] = 100
                    assert not window.engine.audio.error, window.engine.audio.error
                    assert window.engine.audio.sample_count > 0
                    report.update(recording_path=str(window.recorder.path),
                        recording_frames=window.recorder.video_number,
                        recording_audio_samples=window.engine.audio.sample_count,
                        compact_controls_below_video=window.controls.y() >= window.main_splitter.height(),
                        result='PASS')
                    finish(0)
                except Exception as exc:
                    report.update(result='FAIL', error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
                    finish(1)
            QTimer.singleShot(200, capture)
        except Exception as exc:
            report.update(result='FAIL', error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
            finish(1)

    window.noise_strength.setValue(100)
    window.noise_button.click()
    window.volume.setValue(7)
    window.add_paths([video])
    timer.timeout.connect(check)
    timer.start()
