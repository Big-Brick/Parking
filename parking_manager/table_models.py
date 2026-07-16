from __future__ import annotations

from datetime import date, datetime
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from parking_manager.models import ISO_DATE, CarDisplayRow


class SimpleTableModel(QAbstractTableModel):
    def __init__(self, headers: list[str], rows: list[list[Any]], row_ids: list[int] | None = None) -> None:
        super().__init__()
        self.headers = headers
        self.rows = rows
        self.row_ids = row_ids or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        value = self.rows[index.row()][index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(value, bool):
                return ""
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(value, date):
                return value.strftime(ISO_DATE)
            return value
        if role == Qt.ItemDataRole.UserRole:
            if self.row_ids and index.column() >= self.columnCount() - 2:
                return self.row_ids[index.row()]
            return value
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None


class CarsModel(SimpleTableModel):
    def __init__(self, rows: list[CarDisplayRow]) -> None:
        super().__init__(
            ["ID", "License Plate", "Model", "Location", "Permit", "Daily List", "Enter", "Leave"],
            [
                [
                    row.car_id,
                    row.license_plate,
                    row.model,
                    row.location,
                    row.has_valid_individual_permit,
                    row.is_on_daily_list,
                    "",
                    "",
                ]
                for row in rows
            ],
            [row.car_id for row in rows],
        )
