#!/usr/bin/env python3
"""
Communicate with the UPS.

Store data from a supported UPS in an sqlite3 database.
"""

import argparse
import datetime as dt
import os
import shutil
import syslog
import time
import traceback

from typing import Any

import mausy5043_common.funfile as mf
import mausy5043_common.libsignals as ml
import mausy5043_common.libsqlite3 as m3
from pynut3 import nut3

import constants

# fmt: off
parser = argparse.ArgumentParser(description="Execute the bups daemon.")
parser.add_argument("--host", type=str, required=True,
                    help="IP-address or hostname of the UPS-server")
parser_group = parser.add_mutually_exclusive_group(required=True)
parser_group.add_argument("--start", action="store_true",
                          help="start the daemon as a service")
parser_group.add_argument("--debug", action="store_true",
                          help="start the daemon in debugging mode")
OPTION = parser.parse_args()
# fmt: on


# constants
DEBUG = False
HERE = os.path.realpath(__file__).split("/")
# runlist id :
MYID = HERE[-1]
# app_name :
MYAPP = HERE[-3]
MYROOT = "/".join(HERE[0:-3])
APPROOT = "/".join(HERE[0:-2])
# host_name :
NODE = os.uname()[1]


# example values:
# HERE: ['', 'home', 'pi', 'bups', 'bin', 'ups.py']
# MYID: 'ups.py
# MYAPP: bups
# MYROOT: /home/pi
# NODE: rbups


def main() -> None:
    """Execute main loop."""
    set_led("ups-state", "orange")
    killer = ml.GracefulKiller()

    nut3_api = nut3.PyNUT3Client(
        host=OPTION.host, persistent=False, descriptors=False, debug=DEBUG
    )
    mf.syslog_trace(f"Connected to UPS-server: {OPTION.host}", True, DEBUG)
    ups_id = list(nut3_api.devices.keys())[0]

    sql_db = m3.SqlDatabase(
        database=constants.UPS["database"],
        table=constants.UPS["sql_table"],
        insert=constants.UPS["sql_command"],
        debug=DEBUG,
    )

    report_interval = float(constants.UPS["report_interval"])
    sample_interval: float = report_interval / int(constants.UPS["samplespercycle"])
    next_time = 0.0
    if not DEBUG:
        next_time = time.time() + (sample_interval - (time.time() % sample_interval))
    rprt_time = time.time() + (report_interval - (time.time() % report_interval))

    while not killer.kill_now:
        if time.time() > next_time:
            start_time = time.time()
            try:
                data = convert_telegram(nut3_api.devices[ups_id]["vars"])
                mf.syslog_trace(f"Data retrieved: {data}", False, DEBUG)
                set_led("ups-state", "green")
            except Exception:  # noqa
                set_led("ups-state", "red")
                mf.syslog_trace(
                    "Unexpected error while trying to do some work!",
                    syslog.LOG_CRIT,
                    DEBUG,
                )
                mf.syslog_trace(traceback.format_exc(), syslog.LOG_CRIT, DEBUG)
                raise

            # check if we already need to report the result data
            if time.time() > rprt_time:
                mf.syslog_trace("Reporting", False, DEBUG)
                try:
                    sql_db.queue(data)
                except Exception:  # noqa
                    set_led("ups-state", "red")
                    mf.syslog_trace(
                        "Unexpected error while trying to queue the data",
                        syslog.LOG_ALERT,
                        DEBUG,
                    )
                    mf.syslog_trace(traceback.format_exc(), syslog.LOG_ALERT, DEBUG)
                    raise  # may be changed to pass if errors can be corrected.
                try:
                    sql_db.insert(method="replace")
                except Exception:  # noqa
                    set_led("ups-state", "red")
                    mf.syslog_trace(
                        "Unexpected error while trying to commit the data to the database",
                        syslog.LOG_ALERT,
                        DEBUG,
                    )
                    mf.syslog_trace(traceback.format_exc(), syslog.LOG_ALERT, DEBUG)
                    raise  # may be changed to pass if errors can be corrected.

            pause_interval = (
                sample_interval - (time.time() - start_time) - (start_time % sample_interval)
            )
            next_time = (
                pause_interval + time.time()
            )  # gives the actual time when the next loop should start
            # determine moment of next report
            rprt_time = time.time() + (report_interval - (time.time() % report_interval))
            mf.syslog_trace(f"Spent {time.time() - start_time:.1f}s getting data", False, DEBUG)
            mf.syslog_trace(f"Report in {rprt_time - time.time():.0f}s", False, DEBUG)
            mf.syslog_trace("................................", False, DEBUG)
        else:
            time.sleep(1.0)  # 1s resolution is enough


def set_led(dev: str, colour: str) -> None:
    """Activate te requested LED on the website"""
    mf.syslog_trace(f"{dev} is {colour}", False, DEBUG)

    in_dirfile = f"{APPROOT}/www/{colour}.png"
    out_dirfile = f'{constants.TREND["website"]}/{dev}.png'
    shutil.copy(f"{in_dirfile}", out_dirfile)


def convert_telegram(data_dict: dict[str, str]) -> dict[str, Any]:
    """Prune the data.

    Extract only what we need.
    """
    idx_dt = dt.datetime.now()
    epoch = int(idx_dt.timestamp())
    return {
        "sample_time": idx_dt.strftime(constants.DT_FORMAT),
        "sample_epoch": epoch,
        "volt_in": data_dict["output.voltage"][0],
        "volt_bat": -1,  # ##Not on Eaton Protection Station## data_dict['battery.voltage'],
        "charge_bat": data_dict["battery.charge"][0],
        "load_ups": data_dict["ups.load"][0],
        "runtime_bat": data_dict["battery.runtime"][0],
    }


if __name__ == "__main__":
    # initialise logging
    syslog.openlog(ident=f'{MYAPP}.{MYID.split(".")[0]}', facility=syslog.LOG_LOCAL0)

    if OPTION.debug:
        DEBUG = True
        mf.syslog_trace("Debug-mode started.", syslog.LOG_DEBUG, DEBUG)
        print("Use <Ctrl>+C to stop.")

    # OPTION.start only executes this next line, we don't need to test for it.
    main()

    print("And it's goodnight from him")
