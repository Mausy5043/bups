#!/usr/bin/env python3

import os
import sys

_MYHOME = os.environ["HOME"]
_DATABASE = '/srv/databases/upsdata.sqlite3'
_WEBSITE = '/tmp/bups/site'

if not os.path.isfile(_DATABASE):
    _DATABASE = '/srv/data/upsdata.sqlite3'
if not os.path.isfile(_DATABASE):
    _DATABASE = '/mnt/data/upsdata.sqlite3'
if not os.path.isfile(_DATABASE):
    _DATABASE = f'.local/upsdata.sqlite3'
if not os.path.isfile(_DATABASE):
    _DATABASE = f'{_MYHOME}/.sqlite3/upsdata.sqlite3'
if not os.path.isfile(_DATABASE):
    print("Database is missing.")
    sys.exit(1)

DT_FORMAT = "%Y-%m-%d %H:%M:%S"

# The paths defined here must match the paths defined in constants.sh
# $website_dir  and  $website_image_dir
TREND = {'database': _DATABASE,
         'sql_table': "ups",
         'website': _WEBSITE,
         'day_graph': f'{_WEBSITE}/img/bups_hours',
         'month_graph': f'{_WEBSITE}/img/bups_days',
         'year_graph': f'{_WEBSITE}/img/bups_months'
         }


UPS = {'database': _DATABASE,
       'sql_command': "INSERT INTO ups ("
                      "sample_time, sample_epoch, "
                      "volt_in, volt_bat, charge_bat, "
                      "load_ups, runtime_bat"
                      ")"
                      "VALUES (?, ?, ?, ?, ?, ?, ?)",
       'sql_table': "ups",
       'report_time': 60,
       'cycles': 3,
       'samplespercycle': 5
       }
