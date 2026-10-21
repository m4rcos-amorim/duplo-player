"""Real Qt settings persistence and VLC playback after a native drop event."""
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QMimeData, QPoint, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication
from duplo.model import PlaybackOrder, Repeat
from duplo.window import PlayerWindow

app = QApplication.instance() or QApplication([])
output = ROOT / 'test-output' / 'preferences-drop'
output.mkdir(exist_ok=True)
ini = output / f'settings-{uuid4().hex}.ini'
def settings(*args):
    return QSettings(str(ini), QSettings.Format.IniFormat)
def wait_for(predicate):
    until = time.monotonic() + 12
    while time.monotonic() < until:
        app.processEvents()
        if predicate():
            return
        time.sleep(.01)
    raise TimeoutError('Playback did not start after dropping the video.')

with patch('duplo.window.QSettings', settings):
    first = PlayerWindow(silent=True)
    first.set_order(PlaybackOrder.SHUFFLE_LIST)
    first.repeat.setCurrentIndex(first.repeat.findData(Repeat.ALL))
    first.toggle_split()
    first.volume.setValue(9)
    first.noise_strength.setValue(41)
    first.noise_button.click()
    first.close()
    saved = settings()
    saved.sync()
    assert saved.status() == QSettings.Status.NoError
    restored = PlayerWindow(silent=True)
    try:
        restored.show()
        assert restored.split
        assert restored.playlist.order == PlaybackOrder.SHUFFLE_LIST
        assert restored.playlist.repeat == Repeat.ALL
        assert restored.volume.value() == restored.engine.volume == 9
        assert restored.engine.audio.noise_level == 0
        assert not restored.noise_button.isChecked()
        assert restored.noise_strength.value() == 41
        original = ROOT / 'test-output' / 'teste_principal.mp4'
        dropped = ROOT / 'test-output' / 'teste_hevc.mp4'
        restored.add_paths([original])
        wait_for(lambda: restored.views[0].frame is not None)
        for path in (dropped, original, dropped):
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(path))])
            enter = QDragEnterEvent(QPoint(100, 100), Qt.DropAction.CopyAction, mime,
                                    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            app.sendEvent(restored, enter)
            assert enter.isAccepted()
            event = QDropEvent(QPointF(100, 100), Qt.DropAction.CopyAction, mime,
                               Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            app.sendEvent(restored, event)
            assert event.isAccepted()
            assert restored._displayed_path == path
            wait_for(lambda: restored.views[0].frame is not None and restored.engine.player.get_time() > 100)
            assert restored.playlist.current == path
            assert restored.split and restored.engine.volume == 9
            assert restored.engine.audio.noise_level == 0
        assert len(restored.playlist.items) == 2
        report = {'result': 'PASS', 'real_qsettings_round_trip': True,
                  'saved_order_repeat_split_volume': True, 'noise_off_on_launch': True,
                  'native_drop_switches_playback': True, 'existing_items_replayed': True,
                  'duplicate_playlist_entries': False}
        (output / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
    finally:
        restored.close()
