from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

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
