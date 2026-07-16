#!/usr/bin/env python3
"""Parking lot manager GUI backed by embedded SQLite.

Run with:
    python parking_manager.py

SQLite is embedded through Python's sqlite3 module; no separate database server
or external SQLite program is required. By default, data is stored in
``parking.db`` next to this script.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from PySide6.QtCore import (
    QAbstractTableModel,
    QDate,
    QDateTime,
    QEvent,
    QModelIndex,
    QObject,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

ISO_DATETIME = "%Y-%m-%dT%H:%M:%S"
ISO_DATE = "%Y-%m-%d"
ALL_LOCATIONS = "All locations"
EventType = Literal["entering", "leaving"]


@dataclass(slots=True)
class Car:
    id: int | None
    license_plate: str
    model: str
    location: str


@dataclass(slots=True)
class IndividualPermit:
    id: int | None
    car_id: int
    start_date: datetime
    end_date: datetime


@dataclass(slots=True)
class DailyCarEntry:
    id: int | None
    car_id: int
    permit_id: int | None
    list_date: date


@dataclass(slots=True)
class ParkingEvent:
    id: int | None
    car_id: int
    event_type: EventType
    timestamp: datetime


@dataclass(slots=True)
class CarDisplayRow:
    car_id: int
    license_plate: str
    model: str
    location: str
    has_valid_individual_permit: bool
    is_on_daily_list: bool


def to_iso_datetime(value: datetime) -> str:
    return value.replace(microsecond=0).strftime(ISO_DATETIME)


def car_label(car: Car) -> str:
    return f"{car.license_plate} — {car.model} ({car.location})"


class DatabaseManager:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.initialize_schema()

    def initialize_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_plate TEXT NOT NULL UNIQUE,
                model TEXT NOT NULL,
                location TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS individual_permits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS daily_car_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_id INTEGER NOT NULL,
                permit_id INTEGER NULL,
                list_date TEXT NOT NULL,
                FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE,
                FOREIGN KEY (permit_id) REFERENCES individual_permits(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS parking_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_id INTEGER NOT NULL,
                event_type TEXT NOT NULL CHECK(event_type IN ('entering', 'leaving')),
                timestamp TEXT NOT NULL,
                FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
            );
            """
        )
        self.connection.commit()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(sql, params)
        self.connection.commit()
        return cursor

    def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return list(self.connection.execute(sql, params))

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        return self.connection.execute(sql, params).fetchone()

    def close(self) -> None:
        self.connection.close()


class CarRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def add_car(self, car: Car) -> int:
        cursor = self.db.execute(
            "INSERT INTO cars (license_plate, model, location) VALUES (?, ?, ?)",
            (car.license_plate, car.model, car.location),
        )
        return int(cursor.lastrowid)

    def update_car(self, car: Car) -> None:
        self.db.execute(
            "UPDATE cars SET license_plate = ?, model = ?, location = ? WHERE id = ?",
            (car.license_plate, car.model, car.location, car.id),
        )

    def delete_car(self, car_id: int) -> None:
        self.db.execute("DELETE FROM cars WHERE id = ?", (car_id,))

    def get_car(self, car_id: int) -> Car | None:
        row = self.db.fetch_one("SELECT * FROM cars WHERE id = ?", (car_id,))
        if row is None:
            return None
        return Car(row["id"], row["license_plate"], row["model"], row["location"])

    def list_cars(self) -> list[Car]:
        rows = self.db.fetch_all("SELECT * FROM cars ORDER BY license_plate COLLATE NOCASE")
        return [Car(row["id"], row["license_plate"], row["model"], row["location"]) for row in rows]

    def list_locations(self) -> list[str]:
        rows = self.db.fetch_all("SELECT DISTINCT location FROM cars ORDER BY location COLLATE NOCASE")
        return [row["location"] for row in rows]


class PermitRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def add_permit(self, permit: IndividualPermit) -> int:
        cursor = self.db.execute(
            "INSERT INTO individual_permits (car_id, start_date, end_date) VALUES (?, ?, ?)",
            (permit.car_id, to_iso_datetime(permit.start_date), to_iso_datetime(permit.end_date)),
        )
        return int(cursor.lastrowid)

    def update_permit(self, permit: IndividualPermit) -> None:
        self.db.execute(
            "UPDATE individual_permits SET car_id = ?, start_date = ?, end_date = ? WHERE id = ?",
            (permit.car_id, to_iso_datetime(permit.start_date), to_iso_datetime(permit.end_date), permit.id),
        )

    def delete_permit(self, permit_id: int) -> None:
        self.db.execute("DELETE FROM individual_permits WHERE id = ?", (permit_id,))

    def list_permits(self) -> list[IndividualPermit]:
        rows = self.db.fetch_all("SELECT * FROM individual_permits ORDER BY start_date DESC")
        return [
            IndividualPermit(
                row["id"],
                row["car_id"],
                datetime.fromisoformat(row["start_date"]),
                datetime.fromisoformat(row["end_date"]),
            )
            for row in rows
        ]

    def has_valid_permit(self, car_id: int, moment: datetime) -> bool:
        iso_moment = to_iso_datetime(moment)
        return (
            self.db.fetch_one(
                """
                SELECT 1
                FROM individual_permits
                WHERE car_id = ?
                  AND start_date <= ?
                  AND end_date >= ?
                LIMIT 1
                """,
                (car_id, iso_moment, iso_moment),
            )
            is not None
        )


class DailyListRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def add_entry(self, entry: DailyCarEntry) -> int:
        cursor = self.db.execute(
            "INSERT INTO daily_car_list (car_id, permit_id, list_date) VALUES (?, ?, ?)",
            (entry.car_id, entry.permit_id, entry.list_date.strftime(ISO_DATE)),
        )
        return int(cursor.lastrowid)

    def update_entry(self, entry: DailyCarEntry) -> None:
        self.db.execute(
            "UPDATE daily_car_list SET car_id = ?, permit_id = ?, list_date = ? WHERE id = ?",
            (entry.car_id, entry.permit_id, entry.list_date.strftime(ISO_DATE), entry.id),
        )

    def delete_entry(self, entry_id: int) -> None:
        self.db.execute("DELETE FROM daily_car_list WHERE id = ?", (entry_id,))

    def list_entries(self) -> list[DailyCarEntry]:
        rows = self.db.fetch_all("SELECT * FROM daily_car_list ORDER BY list_date DESC")
        return [
            DailyCarEntry(row["id"], row["car_id"], row["permit_id"], date.fromisoformat(row["list_date"]))
            for row in rows
        ]

    def is_car_on_daily_list(self, car_id: int, list_date: date) -> bool:
        return (
            self.db.fetch_one(
                "SELECT 1 FROM daily_car_list WHERE car_id = ? AND list_date = ? LIMIT 1",
                (car_id, list_date.strftime(ISO_DATE)),
            )
            is not None
        )


class ParkingEventRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def add_event(self, event: ParkingEvent) -> int:
        cursor = self.db.execute(
            "INSERT INTO parking_events (car_id, event_type, timestamp) VALUES (?, ?, ?)",
            (event.car_id, event.event_type, to_iso_datetime(event.timestamp)),
        )
        return int(cursor.lastrowid)

    def update_event(self, event: ParkingEvent) -> None:
        self.db.execute(
            "UPDATE parking_events SET car_id = ?, event_type = ?, timestamp = ? WHERE id = ?",
            (event.car_id, event.event_type, to_iso_datetime(event.timestamp), event.id),
        )

    def delete_event(self, event_id: int) -> None:
        self.db.execute("DELETE FROM parking_events WHERE id = ?", (event_id,))

    def list_events(self) -> list[ParkingEvent]:
        rows = self.db.fetch_all("SELECT * FROM parking_events ORDER BY timestamp DESC")
        return [
            ParkingEvent(row["id"], row["car_id"], row["event_type"], datetime.fromisoformat(row["timestamp"]))
            for row in rows
        ]

    def log(self, car_id: int, event_type: EventType) -> int:
        return self.add_event(ParkingEvent(None, car_id, event_type, datetime.now()))


class ParkingService(QObject):
    data_changed = Signal()

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self.cars = CarRepository(db)
        self.permits = PermitRepository(db)
        self.daily = DailyListRepository(db)
        self.events = ParkingEventRepository(db)

    def car_rows(self, location_filter: str | None, plate_query: str) -> list[CarDisplayRow]:
        now = datetime.now()
        today = date.today()
        normalized_query = plate_query.strip().lower()
        rows: list[CarDisplayRow] = []
        for car in self.cars.list_cars():
            if location_filter and car.location != location_filter:
                continue
            if normalized_query and normalized_query not in car.license_plate.lower():
                continue
            if car.id is None:
                continue
            rows.append(
                CarDisplayRow(
                    car.id,
                    car.license_plate,
                    car.model,
                    car.location,
                    self.permits.has_valid_permit(car.id, now),
                    self.daily.is_car_on_daily_list(car.id, today),
                )
            )
        return rows

    def log_event(self, car_id: int, event_type: EventType) -> None:
        self.events.log(car_id, event_type)
        self.data_changed.emit()


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
        if event.type() == QEvent.Type.MouseButtonRelease and option.rect.contains(event.pos()):
            self.clicked.emit(int(index.data(Qt.ItemDataRole.UserRole)), self.action)
            return True
        return False


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


class CarDialog(QDialog):
    def __init__(self, parent: QWidget, car: Car | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Car")
        self.plate_input = QLineEdit(car.license_plate if car else "")
        self.model_input = QLineEdit(car.model if car else "")
        self.location_input = QLineEdit(car.location if car else "")
        form = QFormLayout(self)
        form.addRow("License plate", self.plate_input)
        form.addRow("Model", self.model_input)
        form.addRow("Location", self.location_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def get_car(self, car_id: int | None = None) -> Car:
        return Car(
            car_id,
            self.plate_input.text().strip(),
            self.model_input.text().strip(),
            self.location_input.text().strip(),
        )

    def accept(self) -> None:
        if not self.plate_input.text().strip():
            QMessageBox.warning(self, "Missing license plate", "License plate is required.")
            return
        if not self.model_input.text().strip():
            QMessageBox.warning(self, "Missing model", "Model is required.")
            return
        if not self.location_input.text().strip():
            QMessageBox.warning(self, "Missing location", "Location is required.")
            return
        super().accept()


class PermitDialog(QDialog):
    def __init__(self, parent: QWidget, cars: list[Car], permit: IndividualPermit | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Permit")
        self.car_combo = QComboBox()
        for car in cars:
            self.car_combo.addItem(car_label(car), car.id)
        self.start_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.start_input.setCalendarPopup(True)
        self.end_input = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.end_input.setCalendarPopup(True)
        if permit:
            self.car_combo.setCurrentIndex(max(self.car_combo.findData(permit.car_id), 0))
            self.start_input.setDateTime(QDateTime(permit.start_date))
            self.end_input.setDateTime(QDateTime(permit.end_date))
        form = QFormLayout(self)
        form.addRow("Car", self.car_combo)
        form.addRow("Start", self.start_input)
        form.addRow("End", self.end_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def get_permit(self, permit_id: int | None = None) -> IndividualPermit:
        return IndividualPermit(
            permit_id,
            int(self.car_combo.currentData()),
            self.start_input.dateTime().toPython(),
            self.end_input.dateTime().toPython(),
        )

    def accept(self) -> None:
        if self.end_input.dateTime() < self.start_input.dateTime():
            QMessageBox.warning(self, "Invalid date range", "End date must be after start date.")
            return
        super().accept()


class DailyListEntryDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        cars: list[Car],
        permits: list[IndividualPermit],
        entry: DailyCarEntry | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Daily list entry")
        self.car_combo = QComboBox()
        for car in cars:
            self.car_combo.addItem(car_label(car), car.id)
        self.permit_combo = QComboBox()
        self.permit_combo.addItem("No permit", None)
        for permit in permits:
            self.permit_combo.addItem(f"Permit #{permit.id} for car #{permit.car_id}", permit.id)
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        if entry:
            self.car_combo.setCurrentIndex(max(self.car_combo.findData(entry.car_id), 0))
            self.permit_combo.setCurrentIndex(max(self.permit_combo.findData(entry.permit_id), 0))
            self.date_input.setDate(QDate(entry.list_date.year, entry.list_date.month, entry.list_date.day))
        form = QFormLayout(self)
        form.addRow("Car", self.car_combo)
        form.addRow("Permit", self.permit_combo)
        form.addRow("Date", self.date_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def get_entry(self, entry_id: int | None = None) -> DailyCarEntry:
        return DailyCarEntry(
            entry_id,
            int(self.car_combo.currentData()),
            self.permit_combo.currentData(),
            self.date_input.date().toPython(),
        )


class ParkingEventDialog(QDialog):
    def __init__(self, parent: QWidget, cars: list[Car], event: ParkingEvent | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Parking event")
        self.car_combo = QComboBox()
        for car in cars:
            self.car_combo.addItem(car_label(car), car.id)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["entering", "leaving"])
        self.timestamp_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.timestamp_input.setCalendarPopup(True)
        if event:
            self.car_combo.setCurrentIndex(max(self.car_combo.findData(event.car_id), 0))
            self.type_combo.setCurrentText(event.event_type)
            self.timestamp_input.setDateTime(QDateTime(event.timestamp))
        form = QFormLayout(self)
        form.addRow("Car", self.car_combo)
        form.addRow("Type", self.type_combo)
        form.addRow("Timestamp", self.timestamp_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def get_event(self, event_id: int | None = None) -> ParkingEvent:
        return ParkingEvent(
            event_id,
            int(self.car_combo.currentData()),
            self.type_combo.currentText(),  # type: ignore[arg-type]
            self.timestamp_input.dateTime().toPython(),
        )


class BaseTab(QWidget):
    def __init__(self, service: ParkingService) -> None:
        super().__init__()
        self.service = service

    def selected_id(self, view: QTableView, model: SimpleTableModel) -> int | None:
        indexes = view.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        if model.row_ids:
            return model.row_ids[row]
        return int(model.rows[row][0])

    def show_error(self, exc: Exception) -> None:
        QMessageBox.critical(self, "Error", str(exc))


class CarsTab(BaseTab):
    def __init__(self, service: ParkingService) -> None:
        super().__init__(service)
        self.location_filter = QComboBox()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search license plate...")
        self.table = QTableView()
        self.model = CarsModel([])
        self.enter_delegate = ButtonDelegate("Enter", "entering", self)
        self.leave_delegate = ButtonDelegate("Leave", "leaving", self)
        self.enter_delegate.clicked.connect(self.log_car_event)
        self.leave_delegate.clicked.connect(self.log_car_event)
        self.table.setItemDelegateForColumn(4, StatusDotDelegate(self))
        self.table.setItemDelegateForColumn(5, StatusDotDelegate(self))
        self.table.setItemDelegateForColumn(6, self.enter_delegate)
        self.table.setItemDelegateForColumn(7, self.leave_delegate)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        add_button = QPushButton("Add")
        edit_button = QPushButton("Edit")
        delete_button = QPushButton("Delete")
        add_button.clicked.connect(self.add_car)
        edit_button.clicked.connect(self.edit_car)
        delete_button.clicked.connect(self.delete_car)
        self.location_filter.currentIndexChanged.connect(self.refresh)
        self.search_input.textChanged.connect(self.refresh)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Location:"))
        filters.addWidget(self.location_filter)
        filters.addWidget(self.search_input)
        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()
        layout = QVBoxLayout(self)
        layout.addLayout(filters)
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        current_location = self.location_filter.currentData()
        self.location_filter.blockSignals(True)
        self.location_filter.clear()
        self.location_filter.addItem(ALL_LOCATIONS, None)
        for location in self.service.cars.list_locations():
            self.location_filter.addItem(location, location)
        index = self.location_filter.findData(current_location)
        self.location_filter.setCurrentIndex(max(index, 0))
        self.location_filter.blockSignals(False)
        self.model = CarsModel(self.service.car_rows(self.location_filter.currentData(), self.search_input.text()))
        self.table.setModel(self.model)

    def add_car(self) -> None:
        dialog = CarDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.service.cars.add_car(dialog.get_car())
                self.service.data_changed.emit()
            except Exception as exc:
                self.show_error(exc)

    def edit_car(self) -> None:
        car_id = self.selected_id(self.table, self.model)
        if car_id is None:
            return
        car = self.service.cars.get_car(car_id)
        if car is None:
            return
        dialog = CarDialog(self, car)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.service.cars.update_car(dialog.get_car(car_id))
                self.service.data_changed.emit()
            except Exception as exc:
                self.show_error(exc)

    def delete_car(self) -> None:
        car_id = self.selected_id(self.table, self.model)
        if car_id is None:
            return
        self.service.cars.delete_car(car_id)
        self.service.data_changed.emit()

    def log_car_event(self, car_id: int, action: str) -> None:
        self.service.log_event(car_id, action)  # type: ignore[arg-type]


class CrudTab(BaseTab):
    def __init__(self, service: ParkingService, kind: str) -> None:
        super().__init__(service)
        self.kind = kind
        self.table = QTableView()
        self.model = SimpleTableModel([], [])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        add_button = QPushButton("Add")
        edit_button = QPushButton("Edit")
        delete_button = QPushButton("Delete")
        add_button.clicked.connect(self.add_item)
        edit_button.clicked.connect(self.edit_item)
        delete_button.clicked.connect(self.delete_item)
        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        cars = {car.id: car for car in self.service.cars.list_cars()}
        if self.kind == "permits":
            permits = self.service.permits.list_permits()
            self.model = SimpleTableModel(
                ["ID", "Car", "Start", "End"],
                [[permit.id, car_label(cars[permit.car_id]), permit.start_date, permit.end_date] for permit in permits],
                [permit.id or 0 for permit in permits],
            )
        elif self.kind == "daily":
            entries = self.service.daily.list_entries()
            self.model = SimpleTableModel(
                ["ID", "Date", "Car", "Permit"],
                [[entry.id, entry.list_date, car_label(cars[entry.car_id]), entry.permit_id or ""] for entry in entries],
                [entry.id or 0 for entry in entries],
            )
        else:
            events = self.service.events.list_events()
            self.model = SimpleTableModel(
                ["ID", "Timestamp", "Car", "Type"],
                [[event.id, event.timestamp, car_label(cars[event.car_id]), event.event_type] for event in events],
                [event.id or 0 for event in events],
            )
        self.table.setModel(self.model)

    def add_item(self) -> None:
        cars = self.service.cars.list_cars()
        if not cars:
            QMessageBox.information(self, "No cars", "Add a car before adding related entries.")
            return
        try:
            if self.kind == "permits":
                dialog = PermitDialog(self, cars)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.service.permits.add_permit(dialog.get_permit())
            elif self.kind == "daily":
                dialog = DailyListEntryDialog(self, cars, self.service.permits.list_permits())
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.service.daily.add_entry(dialog.get_entry())
            else:
                dialog = ParkingEventDialog(self, cars)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.service.events.add_event(dialog.get_event())
            self.service.data_changed.emit()
        except Exception as exc:
            self.show_error(exc)

    def edit_item(self) -> None:
        item_id = self.selected_id(self.table, self.model)
        if item_id is None:
            return
        cars = self.service.cars.list_cars()
        try:
            if self.kind == "permits":
                item = next(permit for permit in self.service.permits.list_permits() if permit.id == item_id)
                dialog = PermitDialog(self, cars, item)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.service.permits.update_permit(dialog.get_permit(item_id))
            elif self.kind == "daily":
                item = next(entry for entry in self.service.daily.list_entries() if entry.id == item_id)
                dialog = DailyListEntryDialog(self, cars, self.service.permits.list_permits(), item)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.service.daily.update_entry(dialog.get_entry(item_id))
            else:
                item = next(event for event in self.service.events.list_events() if event.id == item_id)
                dialog = ParkingEventDialog(self, cars, item)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.service.events.update_event(dialog.get_event(item_id))
            self.service.data_changed.emit()
        except Exception as exc:
            self.show_error(exc)

    def delete_item(self) -> None:
        item_id = self.selected_id(self.table, self.model)
        if item_id is None:
            return
        if self.kind == "permits":
            self.service.permits.delete_permit(item_id)
        elif self.kind == "daily":
            self.service.daily.delete_entry(item_id)
        else:
            self.service.events.delete_event(item_id)
        self.service.data_changed.emit()


class MainWindow(QMainWindow):
    def __init__(self, service: ParkingService) -> None:
        super().__init__()
        self.setWindowTitle("Parking Manager")
        self.resize(1100, 700)
        self.tabs: list[QWidget] = [
            CarsTab(service),
            CrudTab(service, "permits"),
            CrudTab(service, "daily"),
            CrudTab(service, "events"),
        ]
        tab_widget = QTabWidget()
        for tab, title in zip(self.tabs, ["Cars", "Permits", "Daily List", "Parking Events"]):
            tab_widget.addTab(tab, title)
        self.setCentralWidget(tab_widget)
        service.data_changed.connect(self.refresh_all)

    def refresh_all(self) -> None:
        for tab in self.tabs:
            tab.refresh()  # type: ignore[attr-defined]


def main() -> int:
    parser = argparse.ArgumentParser(description="Parking lot manager")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(__file__).with_name("parking.db"),
        help="SQLite database path; defaults to parking.db next to this script.",
    )
    args = parser.parse_args()
    app = QApplication(sys.argv)
    db = DatabaseManager(args.database)
    service = ParkingService(db)
    window = MainWindow(service)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
