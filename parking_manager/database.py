from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


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
