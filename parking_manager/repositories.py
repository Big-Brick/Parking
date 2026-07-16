from __future__ import annotations

from datetime import date, datetime

from parking_manager.database import DatabaseManager
from parking_manager.models import (
    ISO_DATE,
    Car,
    DailyCarEntry,
    EventType,
    IndividualPermit,
    ParkingEvent,
    to_iso_datetime,
)


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
