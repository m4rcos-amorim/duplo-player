from pathlib import Path
import struct
import sys

from PySide6.QtCore import QBuffer, QIODevice, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
root = Path(__file__).resolve().parent.parent
image = QIcon(str(root / 'assets' / 'duplo.svg')).pixmap(QSize(256, 256)).toImage()
buffer = QBuffer()
buffer.open(QIODevice.OpenModeFlag.WriteOnly)
image.save(buffer, 'PNG')
data = bytes(buffer.data())
# Modern Windows ICO supports a PNG entry at 256×256.
header = struct.pack('<HHH', 0, 1, 1)
entry = struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(data), 22)
(root / 'assets' / 'duplo.ico').write_bytes(header + entry + data)
