from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget

from parking_manager.service import ParkingService
from parking_manager.tabs import CarsTab, CrudTab


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
