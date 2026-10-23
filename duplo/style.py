STYLE = '''
QWidget { background: #101720; color: #dee8f1; font-family: "Segoe UI"; font-size: 13px; }
QMainWindow { background: #101720; }
QLabel#brand { color: #51ddc3; font-size: 25px; font-weight: 700; }
QLabel#subtitle { color: #8b9bab; }
QLabel#filename { font-size: 12px; font-weight: 600; }
QWidget#controls { background: #141e29; border-radius: 6px; }
QLabel#counter { color: #8b9bab; }
QWidget#floating_timeline { background: rgba(16, 23, 32, 215); border: 1px solid #2b3b4d; border-radius: 10px; }
QWidget#floating_timeline QSlider, QLabel#floating_clock { background: transparent; }
QLabel#floating_clock { color: #dee8f1; font-weight: 600; }
QLabel#recording_badge { background: rgba(16, 23, 32, 200); color: #fa707b; border: 1px solid #fa707b;
                         border-radius: 8px; padding: 4px 10px; font-weight: 700; }
QPushButton, QToolButton { background: #1c2835; border: 1px solid #2b3b4d; border-radius: 6px;
                          padding: 4px; min-height: 18px; }
QPushButton:hover, QToolButton:hover { border-color: #51ddc3; background: #243649; }
QPushButton:checked, QToolButton:checked { background: #24453f; color: #77f2da; border-color: #51ddc3; }
QPushButton:disabled { color: #5c6a79; }
QPushButton#primary { background: #51ddc3; color: #091613; font-weight: 700; border: none; }
QPushButton#play { background: #51ddc3; color: #091613; font-size: 17px; min-width: 26px; font-weight: 600; }
QComboBox { background: #1c2835; border: 1px solid #2b3b4d; border-radius: 6px; padding: 4px; }
QComboBox QAbstractItemView { background: #1c2835; selection-background-color: #24453f; }
QListWidget { background: #141e29; border: 1px solid #253344; border-radius: 8px; padding: 5px; }
QListWidget::item { padding: 10px 6px; border-radius: 4px; }
QListWidget::item:selected { background: #24453f; color: #77f2da; }
QListWidget::item:hover { background: #1c2b3b; }
QSlider::groove:horizontal { background: #2b3b4d; height: 5px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #51ddc3; border-radius: 2px; }
QSlider::handle:horizontal { background: #bcfff0; width: 13px; margin: -5px 0; border-radius: 6px; }
QMenu { background: #182431; border: 1px solid #36475b; padding: 6px; }
QMenu::item { padding: 8px 26px; border-radius: 4px; }
QMenu::item:selected { background: #24453f; }
QMenu::item:disabled { color: #5c6a79; }
QMenu::separator { height: 1px; background: #36475b; margin: 4px 6px; }
QStatusBar { color: #8b9bab; border-top: 1px solid #253344; }
QSplitter::handle { background: #101720; width: 10px; }
QMessageBox { background: #182431; }
QScrollBar:vertical { background: #141e29; width: 9px; }
QScrollBar::handle:vertical { background: #36475b; border-radius: 4px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
'''
