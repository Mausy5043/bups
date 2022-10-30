#!/usr/bin/env python3
"""
Communicate with the UPS.

Store data from a supported UPS in an sqlite3 database.
"""

import argparse
import configparser
import datetime as dt
import os
import sqlite3
import subprocess
import sys
import syslog
import time
import traceback

import mausy5043_common.funfile as mf
import mausy5043_common.libsignals as ml
import mausy5043_common.libsqlite3 as m3

import constants
import libbups as bl

parser = argparse.ArgumentParser(description="Execute the bups daemon.")
parser_group = parser.add_mutually_exclusive_group(required=True)
parser_group.add_argument("--start",
                          action="store_true",
                          help="start the daemon as a service"
                          )
parser_group.add_argument("--debug",
                          action="store_true",
                          help="start the daemon in debugging mode"
                          )
OPTION = parser.parse_args()

# constants
DEBUG = False
HERE = os.path.realpath(__file__).split('/')
# runlist id :
MYID = HERE[-1]
# app_name :
MYAPP = HERE[-3]
MYROOT = "/".join(HERE[0:-3])
# host_name :
NODE = os.uname()[1]

# example values:
# HERE: ['', 'home', 'pi', 'bups', 'bin', 'ups.py']
# MYID: 'ups.py
# MYAPP: bups
# MYROOT: /home/pi
# NODE: rbups

API_BL = None

def main():
    """Execute main loop."""
    global API_BL
    set_led('ups', 'orange')
    killer = ml.GracefulKiller()
    API_BL = bl.Ups(DEBUG)

    sql_db = m3.SqlDatabase(database=constants.UPS['database'],
                            table='mains', insert=constants.UPS['sql_command'],
                            debug=DEBUG
                            )

    report_interval = int(constants.UPS['report_interval'])
    sample_interval = report_interval / int(constants.UPS['samplespercycle'])

    next_time = time.time() + (sample_interval - (time.time() % sample_interval))
    rprt_time = time.time() + (report_interval - (time.time() % report_interval))

    # report_time = constants.UPS['report_time']
    # # fdatabase = f"{MYROOT}/{iniconf.get('DEFAULT', 'databasefile')}"
    # fdatabase = constants.UPS['database']
    # # sqlcmd = iniconf.get(MYID, 'sqlcmd')
    # sqlcmd = constants.UPS['sql_command']
    # # samples_averaged = iniconf.getint(MYID, 'samplespercycle') \
    # #                   * iniconf.getint(MYID, 'cycles')
    # # sample_time = report_time / iniconf.getint(MYID, 'samplespercycle')
    # samples_averaged = int(constants.UPS['samplespercycle']) \
    #                    * int(constants.UPS['cycles'])
    # sample_time = report_time / int(constants.UPS['samplespercycle'])
    while not killer.kill_now:
        if time.time() > next_time:
            start_time = time.time()
            try:
                succes = API_BL.get_telegram()
                set_led('ups', 'green')
            except Exception:  # noqa
                set_led('ups', 'red')
                mf.syslog_trace("Unexpected error while trying to do some work!", syslog.LOG_CRIT, DEBUG)
                mf.syslog_trace(traceback.format_exc(), syslog.LOG_CRIT, DEBUG)
                raise


        if time.time() > pause_time:
            start_time = time.time()
            result = do_work()
            mf.syslog_trace(f"Result   : {result}", False, DEBUG)
            data.append([float(d) for d in result])
            if len(data) > samples_averaged:
                data.pop(0)

            # report sample average
            if start_time % report_time < sample_time:
                # somma       = list(map(sum, zip(*data)))
                somma = [sum(d) for d in zip(*data)]
                # not all entries should be float
                # ['234.000', '13.700', '100.000', '20.000', '1447.000']
                averages = [float(format(d / len(data), '.3f')) for d in somma]
                mf.syslog_trace("Averages : {0}".format(averages),
                                False,
                                DEBUG)
                do_add_to_database(averages, fdatabase, sqlcmd)

            pause_time = (sample_time - (time.time() - start_time) -
                          (start_time % sample_time) + time.time())
            if pause_time > 0:
                mf.syslog_trace(f"Waiting  : {pause_time - time.time():.1f}s", False, DEBUG)
                mf.syslog_trace("................................", False, DEBUG)
            else:
                mf.syslog_trace(f"Behind   : {pause_time - time.time():.1f}s", False, DEBUG)
                mf.syslog_trace("................................", False, DEBUG)
        else:
            time.sleep(1.0)


def do_add_to_database(result, fdatabase, sql_cmd):
    """Commit the results to the database."""
    # Get the time and date in human-readable form and UN*X-epoch...
    conn = None
    cursor = None
    dt_format = '%Y-%m-%d %H:%M:%S'
    out_date = dt.datetime.now()  # time.strftime('%Y-%m-%dT%H:%M:%S')
    out_epoch = int(out_date.timestamp())
    results = (out_date.strftime(dt_format),
               out_epoch,
               result[0],
               result[1],
               result[2],
               result[3],
               result[4]
               )
    mf.syslog_trace(f"   @: {out_date.strftime(dt_format)}", False, DEBUG)
    mf.syslog_trace(f"    : {results}", False, DEBUG)

    retries = 10
    while retries:
        retries -= 1
        try:
            conn = create_db_connection(fdatabase)
            cursor = conn.cursor()
            cursor.execute(sql_cmd, results)
            cursor.close()
            conn.commit()
            conn.close()
            retries = 0
        except sqlite3.OperationalError:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            if retries:
                raise


def create_db_connection(database_file):
    """
    Create a database connection to the SQLite3 database
    specified by database_file.
    """
    consql = None
    mf.syslog_trace(f"Connecting to: {database_file}", False, DEBUG)
    try:
        consql = sqlite3.connect(database_file, timeout=9000)
        return consql
    except sqlite3.Error:
        mf.syslog_trace("Unexpected SQLite3 error when connecting to server.",
                        syslog.LOG_CRIT,
                        DEBUG
                        )
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_CRIT, DEBUG)
        if consql:  # attempt to close connection to SQLite3 server
            consql.close()
            mf.syslog_trace(" ** Closed SQLite3 connection. **",
                            syslog.LOG_CRIT,
                            DEBUG
                            )
        raise


def test_db_connection(fdatabase):
    """
    Test & log database engine connection.
    """
    try:
        conn = create_db_connection(fdatabase)
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version();")
        versql = cursor.fetchone()
        cursor.close()
        conn.commit()
        conn.close()
        syslog.syslog(syslog.LOG_INFO, f"Attached to SQLite3 server: {versql} using {fdatabase}")
    except sqlite3.Error:
        mf.syslog_trace("Unexpected SQLite3 error during test.",
                        syslog.LOG_CRIT,
                        DEBUG
                        )
        mf.syslog_trace(traceback.format_exc(), syslog.LOG_CRIT, DEBUG)
        raise


def set_led(dev, colour):
    mf.syslog_trace(f"{dev} is {colour}", False, DEBUG)

    in_dirfile = f'{APPROOT}/www/{colour}.png'
    out_dirfile = f'{constants.TREND["website"]}/img/{dev}.png'
    shutil.copy(f'{in_dirfile}', out_dirfile)


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

