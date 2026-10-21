from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .i18n import tr


class VideoView(QWidget):
    activated = Signal(object)
    zoomed = Signal(object)
    context_requested = Signal(object, object)
    play_requested = Signal()
    fullscreen_requested = Signal()

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.frame: QImage | None = None
        self.crop = QRectF(0, 0, 1, 1)
        self.rotation = 0
        self.selecting = False
        self.active = False
        self.presentation = False
        self.start = self.end = None
        self.setMinimumSize(240, 190)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_frame(self, image):
        self.frame = image
        self.update()

    def reset_zoom(self):
        self.crop = QRectF(0, 0, 1, 1)
        self.start = self.end = None
        self.update()
        self.zoomed.emit(self)

    def rotate_clockwise(self):
        self.rotation = (self.rotation + 90) % 360
        self.start = self.end = None
        self.update()
        self.zoomed.emit(self)

    def draw_video(self, painter, target=None):
        if self.frame is None or self.frame.isNull():
            return
        target = self.video_rect() if target is None else QRectF(target)
        width, height = target.width(), target.height()
        if self.rotation % 180:
            width, height = height, width
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(target.center())
        painter.rotate(self.rotation)
        painter.drawImage(QRectF(-width / 2, -height / 2, width, height),
                          self.frame, self.source_rect())
        painter.restore()

    def set_selection(self, enabled):
        self.selecting = enabled
        self.start = self.end = None
        self._update_cursor()
        self.update()

    def set_presentation(self, enabled):
        self.presentation = enabled
        self._update_cursor()
        self.update()

    def _update_cursor(self):
        if self.selecting:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.BlankCursor if self.presentation else Qt.CursorShape.ArrowCursor)

    def source_rect(self):
        if self.frame is None:
            return QRectF()
        return QRectF(self.crop.x() * self.frame.width(), self.crop.y() * self.frame.height(),
                      self.crop.width() * self.frame.width(), self.crop.height() * self.frame.height())

    def video_rect(self):
        available = QRectF(self.rect())
        if not self.presentation:
            available = available.adjusted(2, 2, -2, -2)
        source = self.source_rect()
        if source.isEmpty():
            return available
        width, height = source.width(), source.height()
        if self.rotation % 180:
            width, height = height, width
        scale = min(available.width() / width, available.height() / height)
        size_w, size_h = width * scale, height * scale
        return QRectF(available.center().x() - size_w / 2,
                      available.center().y() - size_h / 2, size_w, size_h)

    def apply_selection(self, rectangle):
        target = self.video_rect()
        selection = QRectF(rectangle).normalized().intersected(target)
        if self.frame is None or selection.width() < 8 or selection.height() < 8:
            return False
        previous = QRectF(self.crop)
        x = (selection.x() - target.x()) / target.width()
        y = (selection.y() - target.y()) / target.height()
        width, height = selection.width() / target.width(), selection.height() / target.height()
        # Convert a rectangle on the rotated screen back to original frame
        # coordinates. Keeping crop in source coordinates preserves its content.
        if self.rotation == 90:
            x, y, width, height = y, 1 - x - width, height, width
        elif self.rotation == 180:
            x, y = 1 - x - width, 1 - y - height
        elif self.rotation == 270:
            x, y, width, height = 1 - y - height, x, height, width
        self.crop = QRectF(previous.x() + x * previous.width(),
                          previous.y() + y * previous.height(),
                          width * previous.width(), height * previous.height())
        self.crop = self.crop.intersected(QRectF(0, 0, 1, 1))
        self.update()
        self.zoomed.emit(self)
        return True

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#000000' if self.presentation else '#0b1016'))
        if not self.presentation:
            painter.setPen(QPen(QColor('#51ddc3' if self.active else '#253344'), 2 if self.active else 1))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 10, 10)
        if self.frame is not None and not self.frame.isNull():
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            self.draw_video(painter)
        elif not self.presentation:
            painter.setPen(QColor('#dae5ee'))
            font = painter.font()
            font.setPointSize(20)
            painter.setFont(font)
            painter.drawText(self.video_rect().adjusted(0, -35, 0, -35), Qt.AlignmentFlag.AlignCenter,
                             tr('view.title'))
            font.setPointSize(11)
            painter.setFont(font)
            painter.setPen(QColor('#8b9bab'))
            painter.drawText(self.video_rect().adjusted(0, 45, 0, 45), Qt.AlignmentFlag.AlignCenter,
                             tr('view.welcome'))
        if self.selecting and not self.presentation:
            painter.setPen(QColor('#51ddc3'))
            painter.drawText(QRectF(18, self.height() - 40, self.width() - 36, 26),
                             Qt.AlignmentFlag.AlignCenter, tr('view.select_hint'))
        if self.start is not None and self.end is not None:
            rect = QRectF(self.start, self.end).normalized().intersected(self.video_rect())
            painter.fillRect(rect, QColor(81, 221, 195, 35))
            painter.setPen(QPen(QColor('#51ddc3'), 2, Qt.PenStyle.DashLine))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        self.activated.emit(self)
        self.setFocus()
        if event.button() == Qt.MouseButton.LeftButton:
            if self.selecting and self.frame is not None and self.video_rect().contains(event.position()):
                self.start = QPointF(event.position())
                self.end = QPointF(event.position())
                self.update()

    def mouseMoveEvent(self, event):
        if self.start is not None:
            target = self.video_rect()
            self.end = QPointF(max(target.left(), min(event.position().x(), target.right())),
                               max(target.top(), min(event.position().y(), target.bottom())))
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.start is not None:
            if self.end is not None:
                self.apply_selection(QRectF(self.start, self.end))
            self.start = self.end = None
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.selecting:
            self.fullscreen_requested.emit()

    def contextMenuEvent(self, event):
        self.activated.emit(self)
        self.context_requested.emit(self, event.globalPos())
