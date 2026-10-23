"""Small consistent vector icons, rendered locally without external assets."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PATHS = {
 'open': '<rect x="4" y="3" width="13" height="18" rx="2"/><path d="M9 3v6h8M18 14h5m-2-2 2 2-2 2"/>',
 'folder': '<path d="M3 7h7l2 3h9v10H3zM3 7V4h7l2 3h8v3"/>',
 'previous': '<path d="M5 5v14M19 5 8 12l11 7z"/>',
 'next': '<path d="M19 5v14M5 5l11 7-11 7z"/>',
 'play': '<path d="m7 4 13 8-13 8z"/>',
 'pause': '<path d="M8 5v14M16 5v14"/>',
 'stop': '<rect x="5" y="5" width="14" height="14" rx="1"/>',
 'frame': '<path d="m4 5 11 7-11 7zM18 5v14M20 12h4m-2-2v4"/>',
 'sequential': '<path d="M4 6h16M4 12h16M4 18h16m-3-3 3 3-3 3"/>',
 'random': '<path d="M3 6h3c5 0 7 12 12 12h3m-3-3 3 3-3 3M3 18h3c5 0 7-12 12-12h3m-3-3 3 3-3 3"/>',
 'shuffle': '<path d="M2 5h4c5 0 6 10 11 10h4m-3-3 3 3-3 3M2 15h4c5 0 6-10 11-10h4m-3-3 3 3-3 3M4 21h12"/>',
 'repeat': '<path d="M5 7h13l3 3m-3-6 3 6h-6M19 17H6l-3-3m3 6-3-6h6"/>',
 'repeat-off': '<path d="M5 7h13l3 3m-3-6 3 6h-6M19 17H6l-3-3m3 6-3-6h6M3 2l18 20"/>',
 'repeat-one': '<path d="M5 7h13l3 3m-3-6 3 6h-6M19 17H6l-3-3m3 6-3-6h6M11 10h2v5"/>',
 'record': '<circle cx="12" cy="12" r="8" fill="#fa707b" stroke="#fa707b"/>',
 'join': '<path d="M3 5v14M21 5v14M6 12h5m-3-3 3 3-3 3M18 12h-5m3-3-3 3 3 3"/>',
 'split': '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M12 4v16"/>',
 'zoom': '<path d="M3 9V3h6M15 3h6v6M21 15v6h-6M9 21H3v-6M8 12h8M12 8v8"/>',
 'rotate': '<path d="M20 8a8 8 0 1 0 0 8M20 3v5h-5"/><path d="M9 9h6v6H9z"/>',
 'reset': '<path d="M4 9a8 8 0 1 1 0 6M4 3v6h6"/>',
 'a': '<path d="m5 20 7-16 7 16M8 14h8"/>',
 'b': '<path d="M6 4v16h7a4 4 0 0 0 0-8H6h6a4 4 0 0 0 0-8z"/>',
 'clear': '<path d="m6 6 12 12M18 6 6 18"/>',
 'fullscreen': '<path d="M3 9V3h6M15 3h6v6M21 15v6h-6M9 21H3v-6"/>',
 'volume': '<path d="M3 9h4l5-5v16l-5-5H3zM16 8a6 6 0 0 1 0 8M19 5a10 10 0 0 1 0 14"/>',
 'noise': '<path d="M3 10v4M7 7v10M11 3v18M15 7v10M19 10v4M2 3l20 18"/>',
 'mute': '<path d="M3 9h4l5-5v16l-5-5H3zM16 9l6 6M22 9l-6 6"/>',
 'list': '<path d="M8 5h13M8 12h13M8 19h13M3 5h1M3 12h1M3 19h1"/>',
 'trash': '<path d="M3 6h18M8 6V3h8v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
 'remove': '<path d="M5 12h14"/>',
 'help': '<circle cx="12" cy="12" r="10"/><path d="M8 8a4 4 0 0 1 8 0c0 3-4 3-4 6M12 18v1"/>',
}
_CACHE = {}


def icon(name, dark=False):
    key = (name, dark)
    if key not in _CACHE:
        color = '#091613' if dark else '#dee8f1'
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
               f'<g fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
               + PATHS[name] + '</g></svg>')
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        QSvgRenderer(QByteArray(svg.encode())).render(painter)
        painter.end()
        _CACHE[key] = QIcon(pixmap)
    return _CACHE[key]
