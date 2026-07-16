# Parking Manager

A local desktop parking-lot manager implemented with Python, PySide6, and embedded SQLite.

## Features

- No database server is required; the app opens a local SQLite file itself.
- Four editable data sets:
  - cars: license plate, model, and location;
  - individual permits: car reference, start datetime, and end datetime;
  - daily car list: car reference, optional permit reference, and list date;
  - parking events: car reference, entering/leaving type, and timestamp.
- Cars tab includes:
  - location filtering;
  - automatic license-plate search with whitespace-trimmed partial matching;
  - custom status-dot delegates for valid individual permits and daily-list presence;
  - custom button delegates inside the `QTableView` for entering/leaving event logging.

## Requirements

- Python 3.10 or newer
- PySide6

Install the GUI dependency with:

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python parking_manager.py
```

By default, data is stored in `parking.db` next to `parking_manager.py`. To choose another database file:

```bash
python parking_manager.py --database /path/to/parking.db
```
