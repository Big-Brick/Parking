from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QTableView, QVBoxLayout, QWidget

from parking_manager.delegates import ButtonDelegate, StatusDotDelegate
from parking_manager.dialogs import CarDialog, DailyListEntryDialog, ParkingEventDialog, PermitDialog
from parking_manager.models import ALL_LOCATIONS, car_label
from parking_manager.service import ParkingService
from parking_manager.table_models import CarsModel, SimpleTableModel


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
