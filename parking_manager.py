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
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from parking_manager.database import DatabaseManager
from parking_manager.main_window import MainWindow
from parking_manager.service import ParkingService


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
