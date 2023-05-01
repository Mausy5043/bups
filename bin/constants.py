#!/usr/bin/env python3

"""Project constants for use in Python3 scripts."""

import os
import sys

_MYHOME = os.environ["HOME"]
_DATABASE_FILENAME = "upsdata.sqlite3"
_DATABASE = f"/srv/rmt/_databases/bups/{_DATABASE_FILENAME}"
_WEBSITE = "/tmp/bups/site"

if not os.path.isfile(_DATABASE):
    _DATABASE = f"/srv/databases/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f"/srv/data/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f"/mnt/data/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f".local/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    _DATABASE = f"{_MYHOME}/.sqlite3/{_DATABASE_FILENAME}"
if not os.path.isfile(_DATABASE):
    print("Database is missing.")
    sys.exit(1)

DT_FORMAT = "%Y-%m-%d %H:%M:%S"

# The paths defined here must match the paths defined in constants.sh
# $website_dir  and  $website_image_dir
TREND = {
    "database": _DATABASE,
    "sql_table": "ups",
    "website": _WEBSITE,
    "day_graph": f"{_WEBSITE}/img/bups_hours",
    "month_graph": f"{_WEBSITE}/img/bups_days",
    "year_graph": f"{_WEBSITE}/img/bups_months",
}


UPS = {
    "database": _DATABASE,
    "sql_table": "ups",
    "sql_command": "INSERT INTO ups ("
    "sample_time, sample_epoch, "
    "volt_in, volt_bat, charge_bat, "
    "load_ups, runtime_bat"
    ")"
    "VALUES (?, ?, ?, ?, ?, ?, ?)",
    "report_interval": 180,
    "delay": 0,
    "samplespercycle": 1,
}


if __name__ == "__main__":
    print(f"home              = {_MYHOME}")
    print(f"database location = {_DATABASE}")
