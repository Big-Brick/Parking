from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QObject, Signal

from parking_manager.database import DatabaseManager
from parking_manager.models import CarDisplayRow, EventType
from parking_manager.repositories import CarRepository, DailyListRepository, ParkingEventRepository, PermitRepository


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
