from __future__ import annotations

from PySide6.QtCore import QDate, QDateTime
from PySide6.QtWidgets import QComboBox, QDateEdit, QDateTimeEdit, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox, QWidget

from parking_manager.models import Car, DailyCarEntry, IndividualPermit, ParkingEvent, car_label


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
