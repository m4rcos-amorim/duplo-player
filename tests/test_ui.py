"""Behavior checks for video-only fullscreen and keyboard navigation."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QMimeData, QPoint, QPointF, QRectF, Qt, QUrl
from PySide6.QtGui import QDropEvent, QFontDatabase, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton
from duplo import i18n
from duplo.i18n import tr
from duplo.model import PlaybackOrder, Repeat
from duplo.window import PlayerWindow

app = QApplication.instance() or QApplication([])
for font in ('segoeui.ttf', 'segoeuib.ttf', 'seguisb.ttf'):
    QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / font))

class PlayerUITests(unittest.TestCase):
    def setUp(self):
        i18n.set_language('pt')  # assertions below check the Portuguese interface text
        self.window = PlayerWindow(silent=True, settings=False)
        self.window.show()
        self.window.activateWindow()
        self.window.views[0].setFocus()
        QTest.qWait(50)
        image = QImage(640, 360, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.blue)
        for view in self.window.views:
            view.set_frame(image)

    def tearDown(self):
        self.window.close()
        app.processEvents()

    def test_sidebar_hidden_by_default_and_optional_only_in_window(self):
        self.assertFalse(self.window.sidebar.isVisible())
        self.window.toggle_sidebar()
        self.assertTrue(self.window.sidebar.isVisible())
        self.window.toggle_fullscreen()
        self.assertFalse(self.window.sidebar.isVisible())
        self.window.toggle_sidebar()
        self.assertFalse(self.window.sidebar.isVisible())
        self.window.toggle_fullscreen()
        self.assertTrue(self.window.sidebar.isVisible())

    def test_fullscreen_has_only_video_and_preserves_division_and_zoom(self):
        window = self.window
        window.toggle_split()
        window.views[0].crop = QRectF(.1, .2, .4, .5)
        window.views[1].crop = QRectF(.5, .1, .3, .6)
        saved = [QRectF(view.crop) for view in window.views]
        window.toggle_fullscreen()
        QTest.qWait(50)
        self.assertTrue(window.isFullScreen())
        self.assertFalse(window.statusBar().isVisible())
        self.assertTrue(all(not widget.isVisible() for widget in window._chrome_widgets))
        self.assertTrue(all(view.isVisible() and view.presentation for view in window.views))
        self.assertTrue(window.split)
        self.assertEqual([view.crop for view in window.views], saved)
        margins = window.outer_layout.contentsMargins()
        self.assertEqual((margins.left(), margins.top(), margins.right(), margins.bottom()), (0, 0, 0, 0))
        self.assertEqual(window.video_splitter.geometry().size(), window.centralWidget().size())
        output = Path(__file__).resolve().parent.parent / 'test-output'
        output.mkdir(exist_ok=True)
        window.grab().save(str(output / 'fullscreen-ui.png'))
        window.toggle_fullscreen()
        QTest.qWait(20)
        self.assertFalse(window.isFullScreen())
        self.assertTrue(all(widget.isVisible() for widget in window._chrome_widgets))
        self.assertFalse(window.sidebar.isVisible())
        self.assertEqual([view.crop for view in window.views], saved)

    def test_f11_escape_and_division_shortcuts_in_fullscreen(self):
        window = self.window
        QTest.keyClick(window.views[0], Qt.Key.Key_F11)
        self.assertTrue(window.isFullScreen())
        QTest.keyClick(window.views[0], Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(window.split)
        self.assertTrue(window.views[1].isVisible())
        QTest.keyClick(window.views[1], Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        self.assertFalse(window.split)
        self.assertFalse(window.views[1].isVisible())
        self.assertTrue(window.isFullScreen())
        QTest.keyClick(window.views[0], Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(window.split)
        QTest.keyClick(window.views[0], Qt.Key.Key_Z)
        self.assertTrue(window.views[0].selecting)
        QTest.keyClick(window.views[0], Qt.Key.Key_Escape)
        self.assertFalse(window.isFullScreen())
        self.assertTrue(window.split)
        QTest.keyClick(window.views[0], Qt.Key.Key_Escape)
        self.assertFalse(window.views[0].selecting)
        QTest.keyClick(window.views[0], Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        self.assertFalse(window.split)
        QTest.keyClick(window.views[0], Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(window.split)

    def test_arrows_seek_even_when_volume_or_speed_has_focus(self):
        for widget in (self.window.views[0], self.window.volume, self.window.speed):
            widget.setFocus()
            QTest.qWait(10)
            with patch.object(self.window, 'seek_relative') as seek:
                QTest.keyClick(widget, Qt.Key.Key_Right)
                QTest.keyClick(widget, Qt.Key.Key_Left)
                self.assertEqual([call.args for call in seek.call_args_list], [(5000,), (-5000,)])

    def test_up_down_change_volume_in_window_and_fullscreen(self):
        window = self.window
        window.volume.setValue(50)
        for fullscreen in (False, True):
            if fullscreen:
                window.toggle_fullscreen()
                QTest.qWait(30)
            targets = [window.views[0]] if fullscreen else [window.views[0], window.volume, window.speed]
            for widget in targets:
                widget.setFocus()
                QTest.qWait(10)
                start = window.volume.value()
                QTest.keyClick(widget, Qt.Key.Key_Up)
                self.assertEqual(window.volume.value(), start + 5, (fullscreen, widget))
                QTest.keyClick(widget, Qt.Key.Key_Down)
                QTest.keyClick(widget, Qt.Key.Key_Down)
                self.assertEqual(window.volume.value(), start - 5, (fullscreen, widget))
                self.assertEqual(window.speed.currentData(), 1.0)
        window.volume.setValue(98)
        window.volume_step(5)
        self.assertEqual(window.volume.value(), 100)
        window.volume.setValue(3)
        window.volume_step(-5)
        self.assertEqual(window.volume.value(), 0)

    def test_up_unmutes_and_list_keeps_arrow_navigation(self):
        window = self.window
        window.toggle_mute()
        self.assertTrue(window.engine.muted)
        window.volume_step(-5)
        self.assertTrue(window.engine.muted)
        window.volume_step(5)
        self.assertFalse(window.engine.muted)
        self.assertFalse(window.mute_button.isChecked())
        with tempfile.TemporaryDirectory() as folder:
            files = [Path(folder) / name for name in ('a.mp4', 'b.mp4', 'c.mp4')]
            for path in files:
                path.touch()
            with patch.object(window.engine, 'load'):
                window.add_paths(files)
            window.toggle_sidebar()
            window.list_widget.setCurrentRow(0)
            window.list_widget.setFocus()
            QTest.qWait(10)
            volume = window.volume.value()
            QTest.keyClick(window.list_widget, Qt.Key.Key_Down)
            self.assertEqual(window.list_widget.currentRow(), 1)
            self.assertEqual(window.volume.value(), volume)

    def test_recording_badge_shows_while_recording_but_is_not_recorded(self):
        from duplo.recording import compose_video
        window = self.window
        window.timer.stop()
        window.update_recording_badge()
        self.assertFalse(window.recording_badge.isVisible())
        QTest.qWait(30)
        size = window.video_splitter.size()
        before = compose_video(window.views, window.split, size, size)
        for fullscreen in (False, True):
            if fullscreen:
                window.toggle_fullscreen()
                QTest.qWait(30)
            with patch.object(window.recorder, 'active', True), patch.object(window.recorder, 'video_number', 30 * 75):
                window.update_recording_badge()
                badge = window.recording_badge
                self.assertTrue(badge.isVisible())
                self.assertIn(tr('rec.badge'), badge.text())
                self.assertIn('00:01:15', badge.text())
                self.assertTrue(window.video_splitter.geometry().contains(badge.geometry()))
                self.assertFalse(any(view.isAncestorOf(badge) for view in window.views))
                if not fullscreen:
                    # The same picture is recorded with or without the badge on screen.
                    self.assertEqual(compose_video(window.views, window.split, size, size), before)
            window.update_recording_badge()
            self.assertFalse(window.recording_badge.isVisible())

    def test_one_and_two_navigate_playlist_in_window_and_fullscreen(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / f'video{i}.mp4' for i in range(3)]
            for path in paths:
                path.write_bytes(b'disposable fixture')
            self.window.playlist.add(paths)
            for fullscreen in (False, True):
                if fullscreen:
                    self.window.toggle_fullscreen()
                self.window.playlist.select(1)
                self.window.views[0].setFocus()
                with patch.object(self.window, 'load_current') as load:
                    QTest.keyClick(self.window.views[0], Qt.Key.Key_1)
                    self.assertEqual(self.window.playlist.current, paths[0])
                    QTest.keyClick(self.window.views[0], Qt.Key.Key_2)
                    self.assertEqual(self.window.playlist.current, paths[1])
                    self.assertEqual(load.call_count, 2)

    def test_ctrl_s_zoom_drag_in_fullscreen_has_independent_crops(self):
        window = self.window
        window.toggle_split()
        window.toggle_fullscreen()
        QTest.qWait(40)
        with patch.object(window.engine, 'stop') as stop:
            QTest.keyClick(window.views[0], Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
            self.assertTrue(all(view.selecting for view in window.views))
            self.assertTrue(all(view.cursor().shape() == Qt.CursorShape.CrossCursor for view in window.views))
            for view, x in zip(window.views, (.05, .55)):
                target = view.video_rect()
                start = QPoint(int(target.x() + target.width() * x), int(target.y() + target.height() * .15))
                end = QPoint(int(start.x() + target.width() * .35), int(start.y() + target.height() * .5))
                QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
                QTest.mouseMove(view, end, delay=10)
                QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=end)
                self.assertLess(view.crop.width(), .4)
            self.assertNotEqual(window.views[0].crop, window.views[1].crop)
            self.assertTrue(window.isFullScreen())
            self.assertFalse(window.statusBar().isVisible())
            self.assertTrue(all(not widget.isVisible() for widget in window._chrome_widgets))
            QTest.keyClick(window.views[1], Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
            self.assertTrue(all(not view.selecting for view in window.views))
            stop.assert_not_called()

    def test_three_marks_a_then_b_in_window_and_fullscreen(self):
        window = self.window
        window.timer.stop()
        window._loaded = True
        current = [1000]
        with patch.object(window.engine.player, 'is_seekable', return_value=True), \
             patch.object(window.engine.player, 'get_time', side_effect=lambda: current[0]), \
             patch.object(window.engine, 'seek') as seek:
            for fullscreen in (False, True):
                window.clear_ab()
                if fullscreen:
                    window.toggle_fullscreen()
                target = window.views[0] if fullscreen else window.speed
                target.setFocus()
                current[0] = 1000
                QTest.keyClick(target, Qt.Key.Key_3)
                self.assertEqual(window.loop.a, 1000)
                self.assertIsNone(window.loop.b)
                current[0] = 2000
                QTest.keyClick(target, Qt.Key.Key_3)
                self.assertEqual((window.loop.a, window.loop.b), (1000, 2000))
                self.assertTrue(window.loop.enabled)
                seek.assert_called_with(1000)
                current[0] = 1500
                QTest.keyClick(target, Qt.Key.Key_3)
                self.assertEqual(window.loop.a, 1500)
                self.assertIsNone(window.loop.b)
                QTest.keyClick(target, Qt.Key.Key_C)
                self.assertIsNone(window.loop.a)

    def test_three_without_video_and_invalid_second_press(self):
        window = self.window
        window.timer.stop()
        QTest.keyClick(window.views[0], Qt.Key.Key_3)
        self.assertIsNone(window.loop.a)
        window._loaded = True
        current = [1000]
        with patch.object(window.engine.player, 'is_seekable', return_value=True), \
             patch.object(window.engine.player, 'get_time', side_effect=lambda: current[0]), \
             patch.object(window.engine, 'seek') as seek:
            QTest.keyClick(window.views[0], Qt.Key.Key_3)
            current[0] = 1050
            QTest.keyClick(window.views[0], Qt.Key.Key_3)
            self.assertEqual(window.loop.a, 1000)
            self.assertIsNone(window.loop.b)
            seek.assert_not_called()
            current[0] = 1250
            QTest.keyClick(window.views[0], Qt.Key.Key_3)
            self.assertTrue(window.loop.enabled)
            self.assertEqual(window.loop.b, 1250)

    def test_controls_are_below_video_and_use_icons(self):
        window = self.window
        self.assertGreaterEqual(window.controls.y(), window.main_splitter.y() + window.main_splitter.height())
        self.assertGreater(window.main_splitter.height(), window.height() * .65)
        buttons = window.findChildren(QPushButton)
        self.assertGreater(len(buttons), 20)
        for button in buttons:
            self.assertTrue(window.controls.isAncestorOf(button))
            self.assertFalse(button.icon().isNull())
            self.assertTrue(button.toolTip())
        window.grab().save(str(Path(__file__).resolve().parent.parent / 'test-output' / 'compact-ui.png'))

    def test_ctrl_z_only_restores_selected_perspective_in_fullscreen(self):
        window = self.window
        window.toggle_split()
        window.toggle_fullscreen()
        saved = QRectF(.1, .2, .4, .5)
        window.views[0].crop = QRectF(saved)
        window.views[1].crop = QRectF(.5, .1, .3, .6)
        QTest.mouseClick(window.views[1], Qt.MouseButton.LeftButton)
        QTest.keyClick(window.views[1], Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(window.views[1].crop, QRectF(0, 0, 1, 1))
        self.assertEqual(window.views[0].crop, saved)
        self.assertFalse(window.views[0].selecting)
        self.assertTrue(window.isFullScreen())

    def test_same_video_repeat_preserves_split_and_both_zooms(self):
        window = self.window
        window.timer.stop()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'repeat.mp4'
            path.write_bytes(b'disposable fixture')
            window.playlist.add([path])
            window.playlist.select(0)
            window.playlist.repeat = Repeat.ONE
            window._displayed_path = path
            window.toggle_split()
            window.views[0].crop = QRectF(.1, .2, .4, .5)
            window.views[1].crop = QRectF(.5, .1, .3, .6)
            saved = [QRectF(view.crop) for view in window.views]
            with patch.object(window.engine, 'load') as load:
                window.next(automatic=True)
                load.assert_called_once_with(path)
            self.assertEqual([view.crop for view in window.views], saved)
            self.assertTrue(window.split)

    def test_order_and_repeat_icons_cycle_independently(self):
        window = self.window
        window.repeat_button.click()
        self.assertEqual(window.playlist.repeat, Repeat.ONE)
        expected = [PlaybackOrder.RANDOM_VIDEO, PlaybackOrder.SHUFFLE_LIST, PlaybackOrder.SEQUENTIAL]
        for order in expected:
            window.shuffle_button.click()
            self.assertEqual(window.playlist.order, order)
            self.assertIn(order.label, window.shuffle_button.toolTip())
            self.assertEqual(window.playlist.repeat, Repeat.ONE)
        window.repeat_button.click()
        self.assertEqual(window.playlist.repeat, Repeat.ALL)
        self.assertIn(Repeat.ALL.label, window.repeat_button.toolTip())
        window.repeat_button.click()
        self.assertEqual(window.playlist.repeat, Repeat.OFF)

    def test_reveal_uses_playing_file_even_when_playlist_points_elsewhere(self):
        window = self.window
        with tempfile.TemporaryDirectory() as folder:
            files = [Path(folder) / name for name in ('vídeo, espaço & (A).mp4', 'outro.mp4')]
            for path in files:
                path.write_bytes(b'disposable fixture')
            window.playlist.add(files)
            window.playlist.select(1)
            window._loaded = True
            window._displayed_path = files[0]
            with patch('duplo.window.reveal_in_explorer') as reveal:
                window.reveal_file()
                reveal.assert_called_once_with(files[0])
            window._loaded = False
            with patch('duplo.window.reveal_in_explorer') as reveal:
                window.reveal_file()
                reveal.assert_called_once_with(files[1])

    def test_reveal_reports_missing_file_and_shell_failure(self):
        window = self.window
        window._loaded = True
        window._displayed_path = Path('missing fixture.mp4')
        for exception, title in [(FileNotFoundError('Video moved'), tr('dlg.unavailable_title')),
                                 (OSError('Windows failure'), tr('dlg.cannot_open_folder'))]:
            with patch('duplo.window.reveal_in_explorer', side_effect=exception), \
                 patch('duplo.window.QMessageBox.warning') as warning:
                window.reveal_file()
                self.assertEqual(warning.call_args.args[1], title)
                self.assertIn(str(exception), warning.call_args.args[2])

    def test_slider_and_mute_control_actual_audio_output(self):
        w = self.window
        w.volume.setValue(8)
        self.assertEqual(w.engine.volume, 8)
        self.assertEqual(w.engine.audio.gain, .08)
        w.toggle_mute()
        self.assertTrue(w.mute_button.isChecked())
        self.assertTrue(w.engine.muted)
        self.assertEqual(w.engine.audio.gain, 0.0)
        w.volume.setValue(3)
        w.engine.stop()
        self.assertEqual(w.engine.audio.gain, 0.0)
        w.toggle_mute()
        self.assertFalse(w.mute_button.isChecked())
        self.assertEqual(w.engine.audio.gain, .03)
        w.volume.setValue(0)
        self.assertEqual(w.engine.audio.gain, 0.0)


    def test_restored_low_volume_is_applied_before_playback(self):
        with patch('duplo.window.QSettings') as settings:
            settings.return_value.value.side_effect = lambda key, default=None: 6 if key == 'volume' else default
            restored = PlayerWindow(silent=True)
            try:
                self.assertEqual(restored.volume.value(), 6)
                self.assertEqual(restored.engine.volume, 6)
                self.assertEqual(restored.engine.audio.gain, .06)
            finally:
                restored.close()

    def test_minus_slow_motion_with_focus_fullscreen_and_keypad(self):
        window = self.window
        for fullscreen in (False, True):
            if fullscreen:
                window.toggle_fullscreen()
            targets = [window.views[0]] if fullscreen else [window.views[0], window.volume, window.speed]
            for target in targets:
                window.speed.setCurrentIndex(window.speed.findData(1.0))
                target.setFocus()
                QTest.qWait(10)
                for expected in (.75, .5, .25, .25):
                    QTest.keyClick(target, Qt.Key.Key_Minus)
                    self.assertEqual(window.speed.currentData(), expected)
                    self.assertEqual(window.engine.rate, expected)
                window.speed.setCurrentIndex(window.speed.findData(1.0))
                QTest.keyClick(target, Qt.Key.Key_Minus, Qt.KeyboardModifier.KeypadModifier)
                self.assertEqual(window.speed.currentData(), .75)
                window.speed.setCurrentIndex(window.speed.findData(.1))
                QTest.keyClick(target, Qt.Key.Key_Minus)
                self.assertEqual(window.speed.currentData(), .1)
        for shortcut in window._shortcuts:
            if shortcut.key().toString() in ('-', 'Num+-'):
                self.assertFalse(shortcut.autoRepeat())

    def test_plus_restores_speed_and_accelerates_in_window_and_fullscreen(self):
        window = self.window
        for fullscreen in (False, True):
            if fullscreen:
                window.toggle_fullscreen()
            targets = [window.views[0]] if fullscreen else [window.views[0], window.volume, window.speed]
            for target in targets:
                target.setFocus()
                QTest.qWait(10)
                for modifiers in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ShiftModifier,
                                  Qt.KeyboardModifier.KeypadModifier):
                    window.speed.setCurrentIndex(window.speed.findData(.25))
                    for expected in (.5, .75, 1.0, 1.25, 1.5, 2.0, 2.0):
                        QTest.keyClick(target, Qt.Key.Key_Plus, modifiers)
                        self.assertEqual(window.speed.currentData(), expected, (fullscreen, modifiers))
                        self.assertEqual(window.engine.rate, expected)
        for shortcut in window._shortcuts:
            if shortcut.key().toString() in ('+', 'Shift++', 'Num++'):
                self.assertFalse(shortcut.autoRepeat())

    def test_ctrl_r_rotates_only_selected_view_in_window_and_fullscreen(self):
        window = self.window
        window.toggle_split()
        for fullscreen in (False, True):
            if fullscreen:
                window.toggle_fullscreen()
            for view in window.views:
                view.rotation = 0
                view.crop = QRectF(.1, .2, .5, .6)
            window.activate_view(window.views[0])
            target = window.views[0] if fullscreen else window.speed
            target.setFocus()
            QTest.qWait(10)
            for expected in (90, 180, 270, 0):
                QTest.keyClick(target, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
                self.assertEqual(window.views[0].rotation, expected)
                self.assertEqual(window.views[1].rotation, 0)
                self.assertEqual(window.views[0].crop, QRectF(.1, .2, .5, .6))
            QTest.mouseClick(window.views[1], Qt.MouseButton.LeftButton, pos=window.views[1].rect().center())
            QTest.keyClick(window.views[1], Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual([v.rotation for v in window.views], [0, 90])
            QTest.keyClick(window.views[1], Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(window.views[1].rotation, 90)
            self.assertEqual(window.views[1].crop, QRectF(0, 0, 1, 1))
            self.assertIs(window.views[0].frame, window.views[1].frame)

    def test_selection_zoom_maps_back_from_every_rotation(self):
        view = self.window.views[0]
        expected = {0: (.1, .2, .3, .4), 90: (.2, .6, .4, .3),
                    180: (.6, .4, .3, .4), 270: (.4, .1, .4, .3)}
        for rotation, (x, y, width, height) in expected.items():
            for previous in (QRectF(0, 0, 1, 1), QRectF(.2, .3, .5, .6)):
                view.rotation = rotation
                view.crop = QRectF(previous)
                target = view.video_rect()
                rectangle = QRectF(target.x() + .1 * target.width(), target.y() + .2 * target.height(),
                                   .3 * target.width(), .4 * target.height())
                self.assertTrue(view.apply_selection(rectangle))
                result = view.crop
                wanted = (previous.x() + x * previous.width(), previous.y() + y * previous.height(),
                          width * previous.width(), height * previous.height())
                for actual, value in zip((result.x(), result.y(), result.width(), result.height()), wanted):
                    self.assertAlmostEqual(actual, value)
                self.assertEqual(view.rotation, rotation)

    def test_clockwise_pixels_and_recording_composition_match_independent_views(self):
        from PySide6.QtGui import QColor, QPainter
        from duplo.recording import compose_video
        window = self.window
        window.toggle_split()
        image = QImage(320, 180, QImage.Format.Format_RGB32)
        colors = [QColor('red'), QColor('lime'), QColor('blue'), QColor('yellow')]
        painter = QPainter(image)
        for color, (x, y) in zip(colors, ((0, 0), (160, 0), (0, 90), (160, 90))):
            painter.fillRect(x, y, 160, 90, color)
        painter.end()
        for view in window.views:
            view.set_frame(image)
            view.set_presentation(True)
        corners = ((.25, .25), (.75, .25), (.25, .75), (.75, .75))
        expected = {0: [0, 1, 2, 3], 90: [2, 0, 3, 1],
                    180: [3, 2, 1, 0], 270: [1, 3, 0, 2]}
        window.views[1].rotation = 270
        for rotation in (0, 90, 180, 270):
            window.views[0].rotation = rotation
            composed = compose_video(window.views, True, window.video_splitter.size(), window.video_splitter.size())
            for view in window.views:
                target = view.video_rect()
                rendered = view.grab().toImage()
                ratio = 180 / 320 if view.rotation % 180 else 320 / 180
                self.assertAlmostEqual(target.width() / target.height(), ratio)
                for (u, v), index in zip(corners, expected[view.rotation]):
                    x, y = int(target.x() + u * target.width()), int(target.y() + v * target.height())
                    self.assertEqual(rendered.pixelColor(x, y), colors[index])
                    self.assertEqual(composed.pixelColor(x + view.x(), y + view.y()), colors[index])

    def test_noise_slider_and_shortcut_in_fullscreen(self):
        window = self.window
        self.assertEqual(window.engine.audio.noise_level, 0)
        window.noise_button.click()
        self.assertEqual(window.engine.audio.noise_level, 65)
        for percent in (0, 1, 37, 100, 65):
            window.noise_strength.setValue(percent)
            self.assertEqual(window.engine.audio.noise_level, percent)
            self.assertEqual(window.noise_percent_label.text(), f'{percent}%')
        window.noise_button.click()
        self.assertEqual(window.engine.audio.noise_level, 0)
        window.toggle_fullscreen()
        window.views[0].setFocus()
        QTest.qWait(20)
        QTest.keyClick(window.views[0], Qt.Key.Key_H, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(window.engine.audio.noise_level, 65)
        QTest.keyClick(window.views[0], Qt.Key.Key_H, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(window.engine.audio.noise_level, 0)
        self.assertTrue(window.isFullScreen())
        self.assertFalse(window.controls.isVisible())

    def test_noise_preferences_are_restored(self):
        values = {'noise_enabled': True, 'noise_percent': 47, 'volume': 6}
        with patch('duplo.window.QSettings') as settings:
            settings.return_value.value.side_effect = lambda key, default=None: values.get(key, default)
            restored = PlayerWindow(silent=True)
            try:
                self.assertFalse(restored.noise_button.isChecked())
                self.assertEqual(restored.noise_strength.value(), 47)
                self.assertEqual(restored.engine.audio.noise_level, 0)
            finally:
                restored.close()
            settings.return_value.setValue.assert_any_call('noise_enabled', False)
            settings.return_value.setValue.assert_any_call('noise_percent', 47)

    def test_former_noise_levels_are_migrated(self):
        for old, percent in ((1, 35), (2, 65), (3, 100)):
            values = {'noise_enabled': True, 'noise_strength': old}
            with patch('duplo.window.QSettings') as settings:
                settings.return_value.value.side_effect = lambda key, default=None: values.get(key, default)
                restored = PlayerWindow(silent=True)
                try:
                    self.assertEqual(restored.noise_strength.value(), percent)
                    self.assertEqual(restored.engine.audio.noise_level, 0)
                finally:
                    restored.close()

    def test_playback_preferences_round_trip_and_noise_starts_off(self):
        for order in PlaybackOrder:
            for repeat in Repeat:
                values = {}
                with patch('duplo.window.QSettings') as settings:
                    settings.return_value.value.side_effect = lambda key, default=None: values.get(key, default)
                    settings.return_value.setValue.side_effect = lambda key, value: values.update({key: value})
                    original = PlayerWindow(silent=True)
                    original.set_order(order)
                    original.repeat.setCurrentIndex(original.repeat.findData(repeat))
                    original.toggle_split()
                    original.volume.setValue(7)
                    original.toggle_mute()
                    original.noise_strength.setValue(43)
                    original.noise_button.click()
                    self.assertEqual(original.engine.audio.noise_level, 43)
                    original.close()
                    restored = PlayerWindow(silent=True)
                    try:
                        self.assertEqual(restored.playlist.order, order)
                        self.assertIn(order.label, restored.shuffle_button.toolTip())
                        self.assertEqual(restored.playlist.repeat, repeat)
                        self.assertEqual(restored.repeat.currentData(), repeat)
                        self.assertEqual(restored.repeat_button.accessibleName(), repeat.label)
                        self.assertTrue(restored.split)
                        self.assertTrue(restored.split_button.isChecked())
                        self.assertFalse(restored.views[1].isHidden())
                        self.assertEqual(restored.volume.value(), 7)
                        self.assertEqual(restored.engine.volume, 7)
                        self.assertTrue(restored.engine.muted)
                        self.assertFalse(restored.noise_button.isChecked())
                        self.assertEqual(restored.engine.audio.noise_level, 0)
                        self.assertEqual(restored.noise_strength.value(), 43)
                    finally:
                        restored.close()

    def test_invalid_saved_modes_use_defaults(self):
        values = {'playback_order': 'invalid', 'repeat_mode': 'invalid', 'split': 'false'}
        with patch('duplo.window.QSettings') as settings:
            settings.return_value.value.side_effect = lambda key, default=None: values.get(key, default)
            restored = PlayerWindow(silent=True)
            try:
                self.assertEqual(restored.playlist.order, PlaybackOrder.SEQUENTIAL)
                self.assertEqual(restored.playlist.repeat, Repeat.OFF)
                self.assertFalse(restored.split)
            finally:
                restored.close()

    def test_drop_plays_requested_file_even_if_loaded_or_already_listed(self):
        window = self.window
        window.timer.stop()
        with tempfile.TemporaryDirectory() as folder:
            files = [Path(folder) / name for name in ('a.mp4', 'b.mp4', 'ignore.txt', 'c.mp4')]
            for path in files:
                path.touch()
            with patch.object(window.engine, 'load') as load:
                window.add_paths([files[0]])
                self.assertEqual(window._displayed_path, files[0])
                for dropped in ((files[1], files[3]), (files[0],), (files[0],)):
                    mime = QMimeData()
                    mime.setUrls([QUrl.fromLocalFile(str(files[2]))] + [QUrl.fromLocalFile(str(p)) for p in dropped])
                    event = QDropEvent(QPointF(100,100), Qt.DropAction.CopyAction, mime,
                                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                    load.reset_mock()
                    window.dropEvent(event)
                    self.assertTrue(event.isAccepted())
                    load.assert_called_once_with(dropped[0])
                    self.assertEqual(window.playlist.current, dropped[0])
                    self.assertEqual(window._displayed_path, dropped[0])
                self.assertEqual(window.playlist.items, [files[0], files[1], files[3]])
                load.reset_mock()
                window.add_paths([files[2]], play_immediately=True)
                load.assert_not_called()

    def test_fullscreen_timeline_floats_only_while_mouse_is_near_bottom(self):
        window = self.window
        window.timer.stop()
        window.update_timeline(QPoint(100, window.centralWidget().height() - 5))
        self.assertFalse(window.timeline.isVisible())
        window.toggle_fullscreen()
        QTest.qWait(50)
        area = window.centralWidget().rect()
        window.update_timeline(QPoint(area.width() // 2, area.height() // 2))
        self.assertFalse(window.timeline.isVisible())
        window.update_timeline(QPoint(area.width() // 2, area.height() - 10))
        self.assertTrue(window.timeline.isVisible())
        geometry = window.timeline.geometry()
        self.assertTrue(area.contains(geometry))
        self.assertGreater(geometry.top(), area.height() // 2)
        # Over the bar itself it stays; leaving the zone hides it again.
        window.update_timeline(geometry.center())
        self.assertTrue(window.timeline.isVisible())
        window.update_timeline(QPoint(area.width() // 2, 10))
        self.assertFalse(window.timeline.isVisible())
        # Video only stays video only for recording: the bar is not in the views.
        self.assertFalse(any(window.timeline.parentWidget() is view for view in window.views))
        window.update_timeline(QPoint(area.width() // 2, area.height() - 10))
        window.toggle_fullscreen()
        QTest.qWait(20)
        self.assertFalse(window.timeline.isVisible())

    def test_fullscreen_timeline_click_seeks(self):
        window = self.window
        window.timer.stop()
        window.toggle_fullscreen()
        QTest.qWait(50)
        area = window.centralWidget().rect()
        window.update_timeline(QPoint(area.width() // 2, area.height() - 10))
        slider = window.timeline.slider
        with patch.object(window, 'seek_fraction') as seek:
            slider.seek_requested.disconnect()
            slider.seek_requested.connect(window.seek_fraction)
            QTest.mouseClick(slider, Qt.MouseButton.LeftButton, pos=QPoint(slider.width() // 4, slider.height() // 2))
            seek.assert_called()
            self.assertAlmostEqual(seek.call_args_list[0].args[0], 2500, delta=150)

    def test_join_needs_two_segments_and_offers_menu_entry(self):
        window = self.window
        self.assertFalse(window.join_button.isEnabled())
        window.join_recordings()
        self.assertEqual(window.statusBar().currentMessage(), tr('rec.join_need'))
        window.recorder.segments = [Path('one.mp4')]
        window._segments_changed(1)
        self.assertTrue(window.join_button.isEnabled())
        with patch.object(window.recorder, 'join') as join:
            window.join_recordings()
            join.assert_not_called()
            window.recorder.segments.append(Path('two.mp4'))
            join.return_value = True
            window.join_recordings()
            join.assert_called_once()
        self.assertEqual(window.record_info.text(), tr('rec.joining', n=2))

if __name__ == '__main__':
    unittest.main()
