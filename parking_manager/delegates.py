from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QEvent, QModelIndex, QObject, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionButton, QStyleOptionViewItem


class StatusDotDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        value = bool(index.data(Qt.ItemDataRole.UserRole))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#1f9d55") if value else QColor("#d64545")
        diameter = min(option.rect.width(), option.rect.height(), 16)
        dot_rect = QRect(0, 0, diameter, diameter)
        dot_rect.moveCenter(option.rect.center())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(dot_rect)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(48, 28)


class ButtonDelegate(QStyledItemDelegate):
    clicked = Signal(int, str)

    def __init__(self, label: str, action: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.label = label
        self.action = action

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        button = QStyleOptionButton()
        button.rect = option.rect.adjusted(4, 4, -4, -4)
        button.text = self.label
        button.state = QStyle.StateFlag.State_Enabled
        QApplication.style().drawControl(QStyle.ControlElement.CE_PushButton, button, painter)

    def editorEvent(self, event: QMouseEvent, model: QAbstractTableModel, option: QStyleOptionViewItem, index: QModelIndex) -> bool:  # type: ignore[override]
        if event.type() == QEvent.Type.MouseButtonRelease and option.rect.contains(event.position().toPoint()):
            self.clicked.emit(int(index.data(Qt.ItemDataRole.UserRole)), self.action)
            return True
        return False
