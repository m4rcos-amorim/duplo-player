from pathlib import Path
import time

from PySide6.QtCore import QRect, QSize, QEvent, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel, QListWidget,
                              QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                              QPushButton, QSlider, QSplitter, QVBoxLayout, QWidget, QWidgetAction)

from .engine import Engine, vlc
from .explorer import reveal_in_explorer
from .model import ABLoop, EXTENSIONS, Playlist, Repeat, PlaybackOrder, timestamp
from .style import STYLE
from .view import VideoView
from .icons import icon
from .recording import ViewRecorder, RECORDINGS
from .i18n import LANGUAGES, language, pair, tr


class SeekSlider(QSlider):
    seek_requested = Signal(int)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Clicking anywhere on the timeline seeks directly, not by page step.
            value = int(self.maximum() * max(0, min(1, event.position().x() / max(1, self.width()))))
            self.setValue(value)
            self.seek_requested.emit(value)
        super().mousePressEvent(event)


class FloatingTimeline(QWidget):
    """Timeline shown over the video in full screen while the mouse is near it."""
    ZONE = 90  # pixels from the bottom edge that reveal the bar
    MARGIN = 24
    HEIGHT = 46

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('floating_timeline')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(12)
        self.slider = SeekSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 10000)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.slider, 1)
        self.clock = QLabel('00:00:00 / 00:00:00')
        self.clock.setObjectName('floating_clock')
        layout.addWidget(self.clock)
        self.hide()

    def place(self):
        area = self.parentWidget().rect()
        geometry = QRect(self.MARGIN, area.height() - self.HEIGHT - 16,
                         max(1, area.width() - 2 * self.MARGIN), self.HEIGHT)
        if self.geometry() != geometry:
            self.setGeometry(geometry)

    def wanted(self, cursor):
        """Visible while the cursor is in the bottom zone, or dragging the slider."""
        area = self.parentWidget().rect()
        return self.slider.isSliderDown() or (area.contains(cursor)
                                              and cursor.y() >= area.height() - self.ZONE)


class RecordingBadge(QLabel):
    """Blinking '● REC' with the recorded time, over the video's top-right corner.

    Like the timeline it is a child of the window, not of the views, so the
    recording (composed from the views only) never contains it.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('recording_badge')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def show_time(self, seconds, area):
        dot = '●' if int(time.monotonic() * 2) % 2 == 0 else '○'
        self.setText(f"{dot} {tr('rec.badge')} {timestamp(int(seconds * 1000))}")
        self.adjustSize()
        self.move(area.right() - self.width() - 14, area.top() + 12)
        if not self.isVisible():
            self.show()
        self.raise_()


class PlayerWindow(QMainWindow):
    def __init__(self, silent=False, settings=True):
        super().__init__()
        self.setWindowTitle('Duplo Player')
        self.resize(1280, 800)
        self.setMinimumSize(920, 600)
        self.setStyleSheet(STYLE)
        self.setAcceptDrops(True)
        self.playlist = Playlist()
        self.loop = ABLoop()
        self.engine = Engine(silent=silent)
        self.settings = QSettings('DuploPlayer', 'DuploPlayer') if settings else None
        self.split = False
        self._loaded = False
        self._displayed_path = None
        self._ended_handled = False
        self._last_state = None
        self._loop_seek_time = 0.0
        self._last_position = 0
        self._load_started = 0.0
        self._shortcuts = []
        self._build_ui()
        self.recorder = ViewRecorder(self)
        self.recorder.changed.connect(self._record_changed)
        self.recorder.saved.connect(self._record_saved)
        self.recorder.failed.connect(self._record_failed)
        self.recorder.segments_changed.connect(self._segments_changed)
        self.recorder.joined.connect(self._segments_joined)
        self._closing_after_record = False
        self._bind_shortcuts()
        QApplication.instance().installEventFilter(self)
        if self.settings:
            self.volume.setValue(int(self.settings.value('volume', 80)))
            # Migrate the former three levels without changing saved intensity.
            old_level = max(1, min(3, int(self.settings.value('noise_strength', 2))))
            self.noise_strength.setValue(int(self.settings.value('noise_percent', (35, 65, 100)[old_level - 1])))
            order = PlaybackOrder.__members__.get(str(self.settings.value('playback_order', 'SEQUENTIAL')),
                                                  PlaybackOrder.SEQUENTIAL)
            self.set_order(order)
            repeat = Repeat.__members__.get(str(self.settings.value('repeat_mode', 'OFF')), Repeat.OFF)
            self.repeat.setCurrentIndex(self.repeat.findData(repeat))
            if str(self.settings.value('split', False)).lower() in ('true', '1'):
                self.toggle_split()
            if str(self.settings.value('muted', False)).lower() in ('true', '1'):
                self.toggle_mute()
            geometry = self.settings.value('geometry')
            if geometry:
                self.restoreGeometry(geometry)
        # Each launch starts with the original audio, even if filtering was on.
        self.noise_button.setChecked(False)
        self.apply_noise()
        self.change_volume(self.volume.value())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def button(self, text, callback, shortcut=None, checkable=False, name=None, glyph=None):
        button = QPushButton('' if glyph else text)
        button.setCheckable(checkable)
        button.setAccessibleName(text)
        button.setToolTip(f'{text} ({shortcut})' if shortcut else text)
        if glyph:
            button.setIcon(icon(glyph, dark=name == 'play'))
            button.setIconSize(QSize(22, 22))
            button.setFixedSize(36, 34)
        if name:
            button.setObjectName(name)
        button.clicked.connect(callback)
        return button

    def _build_ui(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(6, 6, 6, 2)
        outer.setSpacing(4)
        self.outer_layout = outer
        self._chrome_widgets = []
        self._sidebar_before_fullscreen = False
        self._was_maximized_before_fullscreen = False
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.video_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.views = [VideoView(tr('view.a')), VideoView(tr('view.b'))]
        for view in self.views:
            self.video_splitter.addWidget(view)
            view.activated.connect(self.activate_view)
            view.zoomed.connect(self.update_zoom_info)
            view.context_requested.connect(self.context_menu)
            view.fullscreen_requested.connect(self.toggle_fullscreen)
        self.views[1].hide()
        self.active_view = self.views[0]
        self.active_view.active = True
        self.video_splitter.setChildrenCollapsible(False)
        self.video_splitter.setHandleWidth(4)
        self.main_splitter.addWidget(self.video_splitter)
        self.sidebar = QWidget()
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(8, 0, 0, 0)
        self.list_count = QLabel(tr('list.count', n=0))
        side.addWidget(self.list_count)
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        side.addWidget(self.list_widget)
        self.sidebar.setMinimumWidth(215)
        self.main_splitter.addWidget(self.sidebar)
        self.sidebar.hide()
        self.main_splitter.setStretchFactor(0, 4)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([970, 260])
        self.main_splitter.setChildrenCollapsible(False)
        outer.addWidget(self.main_splitter, 1)

        self.controls = QWidget()
        self.controls.setObjectName('controls')
        dock = QVBoxLayout(self.controls)
        dock.setContentsMargins(8, 4, 8, 4)
        dock.setSpacing(4)
        self._chrome_widgets.append(self.controls)
        info = QHBoxLayout()
        self.filename = QLabel(tr('file.none'))
        self.filename.setObjectName('filename')
        info.addWidget(self.filename, 1)
        self.clock = QLabel('00:00:00 / 00:00:00')
        info.addWidget(self.clock)
        dock.addLayout(info)
        self.seek_slider = SeekSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 10000)
        self.seek_slider.seek_requested.connect(self.seek_fraction)
        self.seek_slider.sliderMoved.connect(self.seek_fraction)
        self.seek_slider.setEnabled(False)
        dock.addWidget(self.seek_slider)

        playback = QHBoxLayout()
        playback.setSpacing(5)
        playback.addWidget(self.button(tr('btn.open_files'), self.open_files, 'Ctrl+O', glyph='open'))
        playback.addWidget(self.button(tr('btn.open_folder'), self.open_folder, 'Ctrl+Shift+O', glyph='folder'))
        playback.addSpacing(8)
        playback.addWidget(self.button(tr('btn.previous'), self.previous, '1 / P', glyph='previous'))
        self.play_button = self.button(tr('btn.play_pause'), self.play_pause, tr('key.space'), name='play', glyph='play')
        playback.addWidget(self.play_button)
        playback.addWidget(self.button(tr('btn.next'), self.next, '2 / N', glyph='next'))
        playback.addWidget(self.button(tr('btn.stop'), self.stop, 'S', glyph='stop'))
        playback.addWidget(self.button(tr('btn.frame'), self.frame_step, 'E', glyph='frame'))
        self.shuffle_button = self.button(tr('btn.order', mode=PlaybackOrder.SEQUENTIAL.label), self.cycle_order, glyph='sequential')
        playback.addWidget(self.shuffle_button)
        self.repeat_button = self.button(Repeat.OFF.label, self.cycle_repeat, glyph='repeat-off')
        playback.addWidget(self.repeat_button)
        # Keep a single state adapter for existing navigation and integrations.
        self.repeat = QComboBox(self.controls)
        for mode in Repeat:
            self.repeat.addItem(mode.label, mode)
        self.repeat.currentIndexChanged.connect(self.change_repeat)
        self.repeat.hide()
        self.record_button = self.button(tr('btn.record'), self.toggle_recording, 'Ctrl+G', glyph='record')
        playback.addWidget(self.record_button)
        self.join_button = self.button(tr('btn.join'), self.join_recordings, 'Ctrl+Shift+G', glyph='join')
        self.join_button.setEnabled(False)
        playback.addWidget(self.join_button)
        self.noise_button = self.button(tr('btn.noise'), self.toggle_noise,
                                        'Ctrl+H', True, glyph='noise')
        playback.addWidget(self.noise_button)
        self.noise_strength = QSlider(Qt.Orientation.Horizontal)
        self.noise_strength.setRange(0, 100)
        self.noise_strength.setValue(65)
        self.noise_strength.setFixedWidth(100)
        self.noise_strength.setAccessibleName(tr('noise.accessible'))
        self.noise_percent_label = QLabel('65%')
        self.noise_percent_label.setFixedWidth(38)
        self.noise_strength.valueChanged.connect(self.apply_noise)
        playback.addWidget(self.noise_strength)
        playback.addWidget(self.noise_percent_label)
        playback.addStretch()
        playback.addWidget(QLabel(tr('label.speed')))
        self.speed = QComboBox()
        self.speed.setToolTip(tr('speed.tip'))
        for rate in [0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            self.speed.addItem(f'{rate:g}×', rate)
        self.speed.setCurrentIndex(4)
        self.speed.currentIndexChanged.connect(self.change_speed)
        playback.addWidget(self.speed)
        self.mute_button = self.button(tr('btn.mute'), self.toggle_mute, 'M', True, glyph='volume')
        playback.addWidget(self.mute_button)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(80)
        self.volume.setMaximumWidth(100)
        self.volume.valueChanged.connect(self.change_volume)
        playback.addWidget(self.volume)
        dock.addLayout(playback)

        tools = QHBoxLayout()
        tools.setSpacing(5)
        self.split_button = self.button(tr('btn.split'), self.toggle_split, 'Ctrl+D / D', True, glyph='split')
        self.zoom_button = self.button(tr('btn.zoom'), self.toggle_zoom, 'Ctrl+S / Z', True, glyph='zoom')
        tools.addWidget(self.split_button)
        tools.addWidget(self.zoom_button)
        tools.addWidget(self.button(tr('btn.reset_zoom'), self.reset_zoom, 'Ctrl+Z / R', glyph='reset'))
        tools.addWidget(self.button(tr('btn.rotate'), self.rotate_view, 'Ctrl+R', glyph='rotate'))
        tools.addWidget(self.button(tr('btn.mark_a'), self.mark_a, '3 / A', glyph='a'))
        tools.addWidget(self.button(tr('btn.mark_b'), self.mark_b, '3 / B', glyph='b'))
        tools.addWidget(self.button(tr('btn.clear_ab'), self.clear_ab, 'C', glyph='clear'))
        tools.addWidget(self.button(tr('btn.fullscreen'), self.toggle_fullscreen, 'F11', glyph='fullscreen'))
        tools.addWidget(self.button(tr('btn.reveal'), self.reveal_file, glyph='folder'))
        tools.addWidget(self.button(tr('btn.trash'), self.trash_current, glyph='trash'))
        tools.addWidget(self.button(tr('btn.sidebar'), self.toggle_sidebar, 'Ctrl+L', glyph='list'))
        tools.addWidget(self.button(tr('btn.remove'), self.remove_selected, glyph='remove'))
        tools.addWidget(self.button(tr('btn.help'), self.show_help, 'F1', glyph='help'))
        tools.addStretch()
        self.ab_label = QLabel(tr('ab.off'))
        self.ab_label.setObjectName('counter')
        tools.addWidget(self.ab_label)
        self.zoom_info = QLabel(f"{self.views[0].name.title()} • {tr('zoom.full')}")
        self.zoom_info.setObjectName('counter')
        tools.addWidget(self.zoom_info)
        dock.addLayout(tools)
        self.record_info = QLabel(tr('record.idle'))
        self.record_info.setObjectName('counter')
        dock.addWidget(self.record_info)
        outer.addWidget(self.controls)
        self.setCentralWidget(root)
        # Not in a layout: it floats over the video and never enters a recording.
        self.timeline = FloatingTimeline(root)
        self.timeline.slider.seek_requested.connect(self.seek_fraction)
        self.timeline.slider.sliderMoved.connect(self.seek_fraction)
        self.recording_badge = RecordingBadge(root)
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().showMessage(tr('status.start'))

    def eventFilter(self, watched, event):
        # Sliders and combo boxes normally consume arrow keys. Keep playback
        # navigation available while those controls have focus; menus/dialogs
        # retain their own keyboard navigation.
        if (event.type() == QEvent.Type.ShortcutOverride
                and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down)
                and isinstance(watched, QWidget)
                and (watched is self.list_widget or self.list_widget.isAncestorOf(watched))):
            # The list keeps Up/Down for moving between videos.
            event.accept()
            return True
        if (event.type() == QEvent.Type.ShortcutOverride
                and isinstance(watched, QWidget) and watched.window() is self
                and (event.modifiers() in (Qt.KeyboardModifier.NoModifier,
                                           Qt.KeyboardModifier.KeypadModifier)
                     or (event.key() == Qt.Key.Key_Plus
                         and event.modifiers() == Qt.KeyboardModifier.ShiftModifier))
                and (event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right,
                                     Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_Minus, Qt.Key.Key_Plus)
                     # Up/Down set the volume, except while browsing the list.
                     or (event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down)
                         and watched is not self.list_widget
                         and not self.list_widget.isAncestorOf(watched)))):
            event.ignore()
            return True
        return super().eventFilter(watched, event)

    def _bind_shortcuts(self):
        shortcuts = {'Ctrl+O': self.open_files, 'Ctrl+Shift+O': self.open_folder,
                     'Space': self.play_pause, 'D': self.toggle_split, 'Z': self.toggle_zoom,
                     'Ctrl+S': self.toggle_zoom, 'Ctrl+D': self.toggle_split, '3': self.mark_ab,
                     'Ctrl+H': self.toggle_noise, 'Ctrl+R': self.rotate_view, 'Ctrl+Z': self.reset_zoom, 'Ctrl+G': self.toggle_recording,
                     'Ctrl+Shift+G': self.join_recordings, 'R': self.reset_zoom, 'Shift+R': self.reset_all_zoom,
                     'F11': self.toggle_fullscreen, 'Escape': self.escape, 'F1': self.show_help,
                     'A': self.mark_a, 'B': self.mark_b, 'C': self.clear_ab,
                     'N': self.next, 'P': self.previous, '1': self.previous, '2': self.next,
                     'S': self.stop, 'E': self.frame_step,
                     'M': self.toggle_mute, 'Left': lambda: self.seek_relative(-5000),
                     'Right': lambda: self.seek_relative(5000),
                     'Up': lambda: self.volume_step(5), 'Down': lambda: self.volume_step(-5),
                     '[': lambda: self.rate_step(-1),
                     ']': lambda: self.rate_step(1), '-': self.slow_down, 'Num+-': self.slow_down,
                     '+': lambda: self.rate_step(1), 'Shift++': lambda: self.rate_step(1),
                     'Num++': lambda: self.rate_step(1),
                     'Ctrl+L': self.toggle_sidebar}
        for key, callback in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            if key in ('1', '2', '3', 'Ctrl+S', 'Ctrl+D', 'D', 'Ctrl+Z', 'Ctrl+G', 'Ctrl+Shift+G', 'Ctrl+R', 'Ctrl+H', '-', 'Num+-', '+', 'Shift++', 'Num++'):
                shortcut.setAutoRepeat(False)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def open_files(self):
        patterns = ' '.join('*' + ext for ext in sorted(EXTENSIONS))
        start = str(self.playlist.current.parent) if self.playlist.current else ''
        paths, _ = QFileDialog.getOpenFileNames(self, tr('dlg.open_videos'), start,
                                                tr('dlg.videos_filter', patterns=patterns))
        self.add_paths(paths)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr('dlg.open_folder'))
        if folder:
            self.add_paths([folder])

    def add_paths(self, paths, play_immediately=False):
        expanded = []
        for value in paths:
            path = Path(value)
            if path.is_dir():
                # Deliberately only the chosen folder, sorted predictably.
                expanded.extend(sorted(path.iterdir(), key=lambda p: p.name.casefold()))
            else:
                expanded.append(path)
        added = self.playlist.add(expanded)
        self.refresh_list()
        target = next((path.resolve() for path in expanded
                       if path.is_file() and path.suffix.lower() in EXTENSIONS), None) if play_immediately else None
        if target is not None or (added and not self._loaded):
            target = target if target is not None else added[0]
            self.playlist.reset_order()
            self.playlist.select(self.playlist.items.index(target))
            self.load_current(preserve_view=target == self._displayed_path)
        elif added:
            self.statusBar().showMessage(tr('status.added', n=len(added)), 5000)
        elif paths:
            self.statusBar().showMessage(tr('status.none_new'), 6000)

    def refresh_list(self):
        self.list_widget.clear()
        for index, path in enumerate(self.playlist.items):
            item = QListWidgetItem(f'{index + 1:02d}   {path.name}')
            item.setToolTip(str(path))
            self.list_widget.addItem(item)
        if self.playlist.current:
            self.list_widget.setCurrentRow(self.playlist.index)
        self.list_count.setText(tr('list.count', n=len(self.playlist.items)))

    def play_selected(self, item=None):
        if self.playlist.select(self.list_widget.currentRow()):
            self.playlist.reset_order()
            self.load_current()

    def load_current(self, preserve_view=False):
        path = self.playlist.current
        if not path:
            return
        if not path.is_file():
            QMessageBox.warning(self, tr('dlg.unavailable_title'), tr('dlg.unavailable_body', path=path))
            return
        self.clear_ab()
        self._last_position = 0
        self._loaded = True
        self._ended_handled = False
        self._last_state = None
        self._load_started = time.monotonic()
        if not preserve_view:
            for view in self.views:
                view.rotation = 0
            self.reset_all_zoom()
        self._displayed_path = path
        for view in self.views:
            view.set_frame(None)
        self.filename.setText(path.name)
        self.filename.setToolTip(str(path))
        self.setWindowTitle(f'{path.name} — Duplo Player')
        self.seek_slider.setValue(0)
        self.engine.load(path)
        self.refresh_list()
        self.statusBar().showMessage(tr('status.loading'))

    def play_pause(self):
        if not self.playlist.current:
            self.open_files()
            return
        state = self.engine.player.get_state()
        if not self._loaded or state in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error):
            self.load_current(preserve_view=self.playlist.current == self._displayed_path)
        else:
            self.engine.player.set_pause(0 if state == vlc.State.Paused else 1)

    def stop(self):
        self.engine.stop()
        self._loaded = False
        self.clear_ab()
        self.seek_slider.setValue(0)
        self.seek_slider.setEnabled(False)
        self.timeline.slider.setValue(0)
        self.timeline.slider.setEnabled(False)
        self.clock.setText('00:00:00 / 00:00:00')
        self.timeline.clock.setText(self.clock.text())
        self.play_button.setIcon(icon('play', dark=True))
        for view in self.views:
            view.set_frame(None)
        self.statusBar().showMessage(tr('status.stopped'))

    def next(self, automatic=False):
        previous = self._displayed_path
        if self.playlist.next(automatic=automatic):
            self.load_current(preserve_view=self.playlist.current == previous)
        else:
            self.statusBar().showMessage(tr('status.end_of_list'), 6000)

    def previous(self):
        if self.playlist.previous():
            self.load_current()

    def cycle_order(self):
        modes = list(PlaybackOrder)
        self.set_order(modes[(modes.index(self.playlist.order) + 1) % len(modes)])

    def set_order(self, mode):
        self.playlist.set_order(mode)
        glyph = {PlaybackOrder.SEQUENTIAL: 'sequential', PlaybackOrder.RANDOM_VIDEO: 'random',
                 PlaybackOrder.SHUFFLE_LIST: 'shuffle'}[mode]
        self.shuffle_button.setIcon(icon(glyph))
        self.shuffle_button.setToolTip(tr('btn.order_tip', mode=mode.label))
        self.shuffle_button.setAccessibleName(tr('btn.order', mode=mode.label))
        self.statusBar().showMessage(tr('status.order', mode=mode.label, repeat=self.playlist.repeat.label), 6000)

    def toggle_shuffle(self):
        self.set_order(PlaybackOrder.SEQUENTIAL if self.playlist.shuffle else PlaybackOrder.SHUFFLE_LIST)

    def cycle_repeat(self):
        self.repeat.setCurrentIndex((self.repeat.currentIndex() + 1) % self.repeat.count())

    def change_repeat(self):
        self.playlist.repeat = self.repeat.currentData()
        mode = self.playlist.repeat
        glyph = {Repeat.OFF: 'repeat-off', Repeat.ONE: 'repeat-one', Repeat.ALL: 'repeat'}[mode]
        self.repeat_button.setIcon(icon(glyph))
        self.repeat_button.setToolTip(tr('btn.repeat_tip', mode=mode.label))
        self.repeat_button.setAccessibleName(mode.label)
        self.statusBar().showMessage(tr('status.repeat', mode=mode.label), 5000)

    def toggle_recording(self):
        if self.recorder.active:
            self.recorder.stop()
        elif self.recorder.finishing:
            self.statusBar().showMessage(tr('status.finishing_recording'), 5000)
        else:
            try:
                self.recorder.start()
            except Exception as exc:
                QMessageBox.warning(self, tr('rec.cannot_title'), str(exc))

    def _record_changed(self, active):
        self.record_button.setIcon(icon('stop' if active else 'record'))
        self.record_button.setToolTip(tr('rec.stop_tip') if active else tr('rec.start_tip'))
        self.record_info.setText(tr('rec.active', n=len(self.recorder.segments) + 1, path=self.recorder.path)
                                 if active else tr('rec.finishing'))
        self.join_button.setEnabled(bool(self.recorder.segments) or active)

    def join_recordings(self):
        recorder = self.recorder
        count = len(recorder.segments) + (1 if recorder.active else 0)
        if recorder.joining:
            self.statusBar().showMessage(tr('rec.joining', n=len(recorder.segments)), 5000)
        elif count < 2 and not recorder.finishing:
            self.statusBar().showMessage(tr('rec.join_need'), 8000)
        elif recorder.join():
            self.record_info.setText(tr('rec.joining', n=count))
            self.statusBar().showMessage(tr('rec.joining', n=count), 5000)

    def _segments_changed(self, count):
        self.join_button.setEnabled(count > 0 or self.recorder.active)
        if count:
            self.record_info.setText(tr('rec.segments', n=count, path=self.recorder.segments[-1]))

    def _segments_joined(self, path, error, count):
        if not path:
            self.record_info.setText(tr('rec.failed_info', message=error))
            QMessageBox.warning(self, tr('rec.join_failed_title'), tr('rec.join_kept', error=error))
            return
        message = tr('rec.joined', n=count, path=path)
        self.record_info.setText(message)
        self.statusBar().showMessage(message, 10000)

    def _record_saved(self, path):
        self.record_info.setText(tr('rec.saved', path=path))
        self.statusBar().showMessage(tr('rec.saved', path=path), 10000)
        if self._closing_after_record:
            QTimer.singleShot(0, self.close)

    def _record_failed(self, message):
        self.record_info.setText(tr('rec.failed_info', message=message))
        if self._closing_after_record:
            QTimer.singleShot(0, self.close)
        else:
            QMessageBox.warning(self, tr('rec.failed_title'), message)

    def seek_fraction(self, value):
        if not self._loaded or not self.engine.player.is_seekable():
            return
        target = int(self.engine.player.get_length() * value / 10000)
        self.seek_to(target)

    def seek_to(self, target):
        if self.loop.enabled:
            target = max(self.loop.a, min(target, self.loop.b - 1))
        self.engine.seek(target)
        self._last_position = target

    def seek_relative(self, delta):
        if self._loaded:
            self.seek_to(max(0, self.engine.player.get_time()) + delta)

    def frame_step(self):
        if self._loaded:
            self.engine.player.set_pause(1)
            self.engine.player.next_frame()

    def mark_ab(self):
        # First press starts A; second sets B. Once a range is complete,
        # another press starts a new range. Invalid B leaves A ready to retry.
        if not self._loaded or not self.engine.player.is_seekable():
            self.statusBar().showMessage(tr('status.ab_needs_seek'), 5000)
            return
        if self.loop.a is None or self.loop.enabled:
            self.mark_a()
        else:
            self.mark_b()

    def mark_a(self):
        if self._loaded and self.engine.player.is_seekable():
            self.loop.mark_a(max(0, self.engine.player.get_time()))
            self.update_ab_label()

    def mark_b(self):
        if not self._loaded:
            return
        if not self.loop.mark_b(max(0, self.engine.player.get_time())):
            self.statusBar().showMessage(tr('status.ab_order'), 6000)
        else:
            self.engine.seek(self.loop.a)
            self._loop_seek_time = time.monotonic()
            self.update_ab_label()

    def clear_ab(self):
        self.loop.clear()
        self.update_ab_label()

    def update_ab_label(self):
        if self.loop.enabled:
            self.ab_label.setText(tr('ab.range', a=timestamp(self.loop.a), b=timestamp(self.loop.b)))
        elif self.loop.a is not None:
            self.ab_label.setText(tr('ab.wait', a=timestamp(self.loop.a)))
        else:
            self.ab_label.setText(tr('ab.off'))

    def change_speed(self):
        if not self.engine.set_rate(self.speed.currentData()):
            self.statusBar().showMessage(tr('status.rate_refused'), 5000)

    def rate_step(self, delta):
        self.speed.setCurrentIndex(max(0, min(self.speed.count() - 1, self.speed.currentIndex() + delta)))

    def slow_down(self):
        current = self.speed.currentData()
        for rate in (.75, .5, .25):
            if rate < current:
                self.speed.setCurrentIndex(self.speed.findData(rate))
                return

    def toggle_noise(self):
        # Button clicks have already toggled its checked state; shortcuts have not.
        if self.sender() is not self.noise_button:
            self.noise_button.setChecked(not self.noise_button.isChecked())
        self.apply_noise()

    def apply_noise(self):
        percent = self.noise_strength.value()
        level = percent if self.noise_button.isChecked() else 0
        self.engine.audio.set_noise(level)
        self.noise_percent_label.setText(f'{percent}%')
        self.noise_strength.setToolTip(tr('noise.strength_tip', percent=percent))
        state = f'{percent}%' if self.noise_button.isChecked() else tr('noise.off')
        self.noise_button.setToolTip(tr('noise.tip', state=state))
        self.noise_button.setAccessibleName(tr('noise.tip', state=state).replace(' (Ctrl+H)', ''))

    def change_volume(self, value):
        self.engine.set_volume(value)
        self.volume.setToolTip(tr('volume.tip', percent=value))

    def volume_step(self, delta):
        # Turning the volume up also unmutes, as in most players.
        if delta > 0 and self.engine.muted:
            self.toggle_mute()
        self.volume.setValue(max(0, min(100, self.volume.value() + delta)))
        self.statusBar().showMessage(tr('status.volume', percent=self.volume.value()), 3000)

    def toggle_mute(self):
        muted = not self.engine.muted
        self.engine.set_muted(muted)
        self.mute_button.setChecked(muted)
        self.mute_button.setIcon(icon('mute' if muted else 'volume'))

    def activate_view(self, view):
        self.active_view = view
        for candidate in self.views:
            candidate.active = candidate is view
            candidate.update()
        self.update_zoom_info()

    def update_zoom_info(self, view=None):
        selected = self.active_view
        factor = 1 / max(selected.crop.width(), selected.crop.height())
        detail = tr('zoom.factor', factor=factor) if factor > 1.01 else tr('zoom.full')
        if selected.rotation:
            detail += f' • {selected.rotation}°'
        self.zoom_info.setText(f'{selected.name.title()} • {detail}')

    def toggle_zoom(self):
        enabled = not self.views[0].selecting
        self.zoom_button.setChecked(enabled)
        for view in self.views:
            view.set_selection(enabled)
        self.statusBar().showMessage(tr('status.zoom_on') if enabled else tr('status.zoom_off'), 6000)

    def rotate_view(self):
        self.active_view.rotate_clockwise()

    def reset_zoom(self):
        self.active_view.reset_zoom()

    def reset_all_zoom(self):
        for view in self.views:
            view.reset_zoom()

    def toggle_split(self):
        self.split = not self.split
        self.views[1].setVisible(self.split)
        self.split_button.setChecked(self.split)
        if self.split:
            self.video_splitter.setSizes([1, 1])
        else:
            self.activate_view(self.views[0])
        self.statusBar().showMessage(tr('status.shared'), 6000)

    def toggle_sidebar(self):
        if not self.isFullScreen():
            self.sidebar.setVisible(not self.sidebar.isVisible())

    def _set_video_only(self, enabled):
        for widget in self._chrome_widgets:
            widget.setVisible(not enabled)
        self.statusBar().setVisible(not enabled)
        self.sidebar.setVisible(False if enabled else self._sidebar_before_fullscreen)
        if enabled:
            self.outer_layout.setContentsMargins(0, 0, 0, 0)
        else:
            self.outer_layout.setContentsMargins(6, 6, 6, 2)
        self.outer_layout.setSpacing(0 if enabled else 4)
        self.video_splitter.setHandleWidth(0 if enabled else 4)
        self.video_splitter.setStyleSheet('QSplitter::handle { background: #000; width: 0px; }' if enabled else '')
        for view in self.views:
            view.set_presentation(enabled)
        if not enabled:
            self.timeline.hide()

    def update_recording_badge(self):
        if self.recorder.active:
            area = self.video_splitter.geometry()
            self.recording_badge.show_time(self.recorder.video_number / 30, area)
        else:
            self.recording_badge.hide()

    def update_timeline(self, cursor=None):
        """Show the floating timeline in full screen only while the mouse is over its zone."""
        if not self.isFullScreen():
            self.timeline.hide()
            return
        if cursor is None:
            cursor = self.centralWidget().mapFromGlobal(QCursor.pos())
        if self.timeline.wanted(cursor):
            self.timeline.place()
            if not self.timeline.isVisible():
                self.timeline.show()
                self.timeline.raise_()
        else:
            self.timeline.hide()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self._set_video_only(False)
            if self._was_maximized_before_fullscreen:
                self.showMaximized()
            else:
                self.showNormal()
        else:
            self._sidebar_before_fullscreen = self.sidebar.isVisible()
            self._was_maximized_before_fullscreen = self.isMaximized()
            self._set_video_only(True)
            self.showFullScreen()
        self.active_view.setFocus()

    def escape(self):
        if self.isFullScreen():
            self.toggle_fullscreen()
        elif self.views[0].selecting:
            self.toggle_zoom()

    def context_menu(self, view, position):
        menu = QMenu(self)
        menu.addAction(tr('menu.play_pause'), self.play_pause)
        menu.addSeparator()
        reveal = menu.addAction(tr('menu.reveal'), self.reveal_file)
        trash = menu.addAction(tr('menu.trash'), self.trash_current)
        enabled = self.playlist.current is not None
        reveal.setEnabled(enabled)
        trash.setEnabled(enabled)
        menu.addSeparator()
        zoom = menu.addAction(tr('menu.zoom'), self.toggle_zoom)
        zoom.setCheckable(True)
        zoom.setChecked(view.selecting)
        noise_action = menu.addAction(tr('menu.noise'), self.toggle_noise)
        noise_action.setCheckable(True)
        noise_action.setChecked(self.noise_button.isChecked())
        noise_menu = menu.addMenu(tr('menu.noise_strength'))
        intensity = QWidget()
        intensity_layout = QHBoxLayout(intensity)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(self.noise_strength.value())
        slider.setMinimumWidth(180)
        slider.setAccessibleName(tr('noise.accessible'))
        percent = QLabel(f'{slider.value()}%')
        percent.setFixedWidth(38)
        intensity_layout.addWidget(slider)
        intensity_layout.addWidget(percent)
        slider.valueChanged.connect(self.noise_strength.setValue)
        slider.valueChanged.connect(lambda value: percent.setText(f'{value}%'))
        slider_action = QWidgetAction(noise_menu)
        slider_action.setDefaultWidget(intensity)
        noise_menu.addAction(slider_action)
        menu.addAction(tr('menu.reset_zoom'), self.reset_zoom)
        menu.addAction(tr('menu.rotate'), self.rotate_view)
        split = menu.addAction(tr('menu.split'), self.toggle_split)
        split.setCheckable(True)
        split.setChecked(self.split)
        menu.addSeparator()
        speed_menu = menu.addMenu(tr('menu.speed'))
        for index in range(self.speed.count()):
            action = speed_menu.addAction(self.speed.itemText(index))
            action.setCheckable(True)
            action.setChecked(index == self.speed.currentIndex())
            action.triggered.connect(lambda checked=False, i=index: self.speed.setCurrentIndex(i))
        menu.addAction(tr('menu.fullscreen'), self.toggle_fullscreen)
        menu.addAction(tr('menu.rec_stop') if self.recorder.active else tr('menu.rec_start'), self.toggle_recording)
        join = menu.addAction(tr('menu.rec_join', n=len(self.recorder.segments)), self.join_recordings)
        join.setEnabled(self.join_button.isEnabled())
        menu.addSeparator()
        language_menu = menu.addMenu(tr('menu.language'))
        for code, name in LANGUAGES.items():
            action = language_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(code == language())
            action.triggered.connect(lambda checked=False, c=code: self.choose_language(c))
        menu.exec(position)

    def reveal_file(self):
        path = self._displayed_path if self._loaded and self._displayed_path else self.playlist.current
        if path is None:
            return
        try:
            reveal_in_explorer(path)
        except FileNotFoundError as exc:
            QMessageBox.warning(self, tr('dlg.unavailable_title'), str(exc))
        except OSError as exc:
            QMessageBox.warning(self, tr('dlg.cannot_open_folder'), f'{path}\n\n{exc}')
        else:
            self.statusBar().showMessage(tr('status.revealed', folder=path.parent), 6000)

    def trash_current(self):
        path = self.playlist.current
        if path is None:
            return
        was_playing = self.engine.player.get_state() == vlc.State.Playing
        position = max(0, self.engine.player.get_time())
        if was_playing:
            self.engine.player.set_pause(1)
        confirm = QMessageBox(self)
        confirm.setWindowTitle(tr('trash.title'))
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setText(tr('trash.text', name=path.name))
        confirm.setInformativeText(tr('trash.info', path=path))
        yes = confirm.addButton(tr('trash.confirm'), QMessageBox.ButtonRole.AcceptRole)
        cancel = confirm.addButton(tr('trash.cancel'), QMessageBox.ButtonRole.RejectRole)
        confirm.setDefaultButton(cancel)
        confirm.setEscapeButton(cancel)
        confirm.exec()
        if confirm.clickedButton() is not yes:
            if was_playing:
                self.engine.player.set_pause(0)
            return
        # Release VLC file handles before recycling. There is no unlink fallback.
        self.engine.stop()
        self._loaded = False
        try:
            from .recycle import recycle
            recycle(path)
        except Exception as exc:
            QMessageBox.warning(self, tr('trash.failed_title'), tr('trash.failed_body', error=exc))
            self.load_current()
            self._restore_position(position, paused=not was_playing)
            return
        idx = self.playlist.remove(path)
        self.refresh_list()
        if idx >= 0:
            self.playlist.select(idx)
            self.load_current()
        else:
            self.stop()
            self.filename.setText(tr('file.none'))
            self.setWindowTitle('Duplo Player')
        self.statusBar().showMessage(tr('status.trashed', name=path.name), 8000)

    def _restore_position(self, position, paused, attempts=30):
        # After a reload VLC reports seekable before it accepts a seek; one sent while the
        # media is still opening is ignored and playback starts from 0. Wait for Playing.
        player = self.engine.player
        if player.get_state() == vlc.State.Playing and player.is_seekable():
            self.engine.seek(position)
            if paused:
                self.engine.player.set_pause(1)
        elif attempts:
            QTimer.singleShot(100, lambda: self._restore_position(position, paused, attempts - 1))

    def remove_selected(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return
        path = self.playlist.items[row]
        current = path == self.playlist.current
        if current:
            self.stop()
        idx = self.playlist.remove(path)
        if current and idx >= 0:
            self.playlist.select(idx)
            self.load_current()
        elif current:
            self.filename.setText(tr('file.none'))
            self.setWindowTitle('Duplo Player')
        self.refresh_list()

    def tick(self):
        self.engine.audio.pump()
        frame = self.engine.take_frame()
        if frame is not None:
            for view in self.views:
                view.set_frame(frame)
        self.update_timeline()
        self.update_recording_badge()
        if not self._loaded:
            return
        player = self.engine.player
        state = player.get_state()
        position = max(0, player.get_time())
        duration = max(0, player.get_length())
        if state == vlc.State.Playing:
            self._last_position = position
        self.play_button.setIcon(icon('pause' if state == vlc.State.Playing else 'play', dark=True))
        seekable = bool(player.is_seekable()) and duration > 0
        self.clock.setText(f'{timestamp(position)} / {timestamp(duration)}')
        self.timeline.clock.setText(self.clock.text())
        for slider in (self.seek_slider, self.timeline.slider):
            slider.setEnabled(seekable)
            if not slider.isSliderDown() and duration:
                slider.setValue(int(position / duration * 10000))
        if self.loop.enabled and state == vlc.State.Playing and position >= self.loop.b:
            if time.monotonic() - self._loop_seek_time > 0.12:
                self.engine.seek(self.loop.a)
                self._loop_seek_time = time.monotonic()
        if state != self._last_state:
            self._last_state = state
            if state == vlc.State.Playing:
                self.statusBar().showMessage(tr('status.playing'))
            elif state == vlc.State.Paused:
                self.statusBar().showMessage(tr('status.paused'))
        if state == vlc.State.Ended and not self._ended_handled:
            self._ended_handled = True
            # A–B takes precedence even if B is at the very end of the file.
            if self.loop.enabled:
                saved_loop = ABLoop(self.loop.a, self.loop.b)
                self.load_current(preserve_view=True)
                self.loop = saved_loop
                self.update_ab_label()
                self._restore_position(self.loop.a, paused=False)
            else:
                self.next(automatic=True)
        if (state == vlc.State.Error or self.engine.callback_error) and not self._ended_handled:
            self._ended_handled = True
            self.statusBar().showMessage(tr('status.play_failed'))
            QMessageBox.warning(self, tr('dlg.play_failed_title'), tr('dlg.play_failed_body'))

    def show_help(self):
        QMessageBox.information(self, tr('help.title'), tr('help.body'))

    def choose_language(self, code):
        """Save the interface language; it applies the next time the app starts."""
        if code == language():
            return
        if self.settings:
            self.settings.setValue('language', code)
        pt, en = pair('language.changed_body')
        QMessageBox.information(self, 'Idioma alterado / Language changed', f'{pt}\n\n{en}')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self.add_paths(paths, play_immediately=True)
        event.acceptProposedAction()

    def closeEvent(self, event):
        if self.recorder.active or self.recorder.finishing:
            self._closing_after_record = True
            self.recorder.stop()
            event.ignore()
            return
        if self.recorder.joining:
            # Let the stream copy finish; segments are only recycled after it succeeds.
            self._closing_after_record = True
            self.recorder.joined.connect(lambda *args: QTimer.singleShot(0, self.close))
            event.ignore()
            return
        self.timer.stop()
        if self.settings:
            self.settings.setValue('volume', self.volume.value())
            self.settings.setValue('playback_order', self.playlist.order.name)
            self.settings.setValue('repeat_mode', self.playlist.repeat.name)
            self.settings.setValue('split', self.split)
            self.settings.setValue('muted', self.engine.muted)
            self.settings.setValue('noise_enabled', False)
            self.settings.setValue('noise_percent', self.noise_strength.value())
            if not self.isFullScreen():
                self.settings.setValue('geometry', self.saveGeometry())
        self.engine.close()
        event.accept()
