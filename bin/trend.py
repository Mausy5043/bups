#!/usr/bin/env python3
"""Create trendbargraphs for various periods of data."""

import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

import argparse
from datetime import datetime as dt
import os
import sqlite3 as s3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

import constants

# app_name :
HERE = os.path.realpath(__file__).split('/')
# runlist id for daemon :
MYID = HERE[-1]
MYAPP = HERE[-3]
MYROOT = "/".join(HERE[0:-3])
NODE = os.uname()[1]

# example values:
# HERE: ['', 'home', 'pi', 'upsdiagd', 'bin', 'ups.py']

DATABASE = constants.TREND['database']
TABLE = constants.TREND['sql_table']
OPTION = ""
DEBUG = False


def fetch_data(hours_to_fetch=48, aggregation='2min'):
    """
    Query the database to fetch the requested data
    :param hours_to_fetch:      (int) number of hours of data to fetch
    :param aggregation:         (int) number of minutes to aggregate per datapoint
    :return:
    """
    df_cmp = None
    df_t = None
    if DEBUG:
        print("*** fetching UPS data ***")
    where_condition = f" (sample_time >= datetime(\'now\', \'-{hours_to_fetch + 1} hours\'))"
    s3_query = f"SELECT * FROM {TABLE} WHERE {where_condition}"
    if DEBUG:
        print(s3_query)
    with s3.connect(DATABASE) as con:
        df = pd.read_sql_query(s3_query,
                               con,
                               parse_dates='sample_time',
                               index_col='sample_epoch'
                               )
    for c in df.columns:
        if c not in ['sample_time']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df.index = pd.to_datetime(df.index, unit='s').tz_localize("UTC").tz_convert("Europe/Amsterdam")
    # resample to monotonic timeline
    df = df.resample(f'{aggregation}').mean()
    df = df.interpolate(method='slinear')
    df = df.reset_index(level=['sample_epoch'])
    data_dict = dict()
    data_dict['ups'] = df
    return data_dict


def y_ax_limits(data_set, accuracy):
    """Determine proper y-axis scaling

    Args:
        data_set (a single dataframe row): containing the data
        accuracy (int): round the y-limit up or down to the closest
                        multiple of this parameter

    Returns:
        list: [lower limit, upper limit] as calculated
    """
    hi_limit = np.ceil(np.nanmax(data_set) / accuracy) * accuracy + (accuracy * 0.1)
    lo_limit = np.floor(np.nanmin(data_set) / accuracy) * accuracy - (accuracy * 0.1)
    if np.isnan(lo_limit):
        lo_limit = 0
    if np.isnan(hi_limit):
        hi_limit = lo_limit + accuracy
    return [lo_limit, hi_limit]


def plot_graph(output_file, data_frame, plot_title):
    """
    Create graphs
    """

    # Set the bar width
    # bar_width = 0.75
    fig_x = 10
    fig_y = 2.5
    fig_fontsize = 6.5
    ahpla = 0.6

    # ###############################
    # Create a line plot of load and line voltage
    # ###############################
    plt.rc('font', size=fig_fontsize)
    ax1 = data_frame.plot(x='sample_epoch', y=['load_ups', 'volt_in'], kind='line', figsize=(fig_x, fig_y),
                          style=['b-', 'r-'], secondary_y=['volt_in'])
    lws = [1]
    lwsr = [1]
    alp = [ahpla]
    alpr = [ahpla]
    for i, l in enumerate(ax1.lines):
        plt.setp(l, alpha=alp[i], linewidth=lws[i])
    for i, l in enumerate(ax1.right_ax.lines):
        plt.setp(l, alpha=alpr[i], linewidth=lwsr[i])
    ax1.set_ylim(y_ax_limits(data_frame['load_ups'], 0.5))
    ax1.right_ax.set_ylim(y_ax_limits(data_frame['volt_in'], 20))
    ax1.set_ylabel("[%]")
    ax1.right_ax.set_ylabel("[V]")
    ax1.legend(loc='upper left', framealpha=0.2, labels=['load'])
    ax1.right_ax.legend(loc='upper right', framealpha=0.2, labels=['line'])
    # ax1.set_xlabel("Datetime")
    ax1.grid(which='major', axis='y', color='k', linestyle='--', linewidth=0.5)
    plt.title(f'{plot_title}')
    # plt.tight_layout()
    plt.savefig(fname=f'{output_file}_V.png', format='png')

    # ###############################
    # Create a line plot of runtime
    # ###############################
    plt.rc('font', size=fig_fontsize)
    ax1 = data_frame.plot(x='sample_epoch', y=['runtime_bat'], kind='line', figsize=(fig_x, fig_y), style=['g'])
    lws = [4]
    alp = [ahpla]
    for i, l in enumerate(ax1.lines):
        plt.setp(l, alpha=alp[i], linewidth=lws[i])
    ax1.set_ylim(y_ax_limits(data_frame['runtime_bat'], 50))
    ax1.set_ylabel("[sec]")
    ax1.legend(loc='upper left', framealpha=0.2, labels=['runtime'])
    # ax1.set_xlabel("Datetime")
    ax1.grid(which='major', axis='y', color='k', linestyle='--', linewidth=0.5)
    # plt.tight_layout()
    plt.savefig(fname=f'{output_file}_RUN.png', format='png')

    # ###############################
    # Create a line plot of charge
    # ###############################
    plt.rc('font', size=fig_fontsize)
    ax1 = data_frame.plot(x='sample_epoch', y=['charge_bat'], kind='line', figsize=(fig_x, fig_y), style=['brown'])
    lws = [4]
    alp = [ahpla]
    for i, l in enumerate(ax1.lines):
        plt.setp(l, alpha=alp[i], linewidth=lws[i])
    ax1.set_ylim(y_ax_limits(data_frame['charge_bat'], 50))
    ax1.set_ylabel("[%]")
    ax1.legend(loc='upper left', framealpha=0.2, labels=['charge'])
    # ax1.set_xlabel("Datetime")
    ax1.grid(which='major', axis='y', color='k', linestyle='--', linewidth=0.5)
    # plt.tight_layout()
    plt.savefig(fname=f'{output_file}_CHG.png', format='png')


def main():
    """
      This is the main loop
      """
    global MYAPP
    global OPTION
    if OPTION.hours:
        # plot_graph(
        #     f'/tmp/{MYAPP}/site/img/pastday_', fetch_last_day(OPTION.hours),
        #     f"Trend afgelopen uren ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})"
        # )
        plot_graph(constants.TREND['day_graph'], fetch_data(hours_to_fetch=OPTION.hours, aggregation='H'),
                   f" trend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})" )
    if OPTION.days:
        # plot_graph(
        #     f'/tmp/{MYAPP}/site/img/pastmonth_',
        #     fetch_last_day(OPTION.days * 24),
        #     f"Trend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})"
        # )
        plot_graph(constants.TREND['month_graph'], fetch_data(hours_to_fetch=OPTION.days * 24, aggregation='D'),
                   f" trend per uur afgelopen maand ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})" )
    if OPTION.months:
        # plot_graph(
        #     f'/tmp/{MYAPP}/site/img/pastmonth_',
        #     fetch_last_day(OPTION.days * 24),
        #     f"Trend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})"
        # )
        plot_graph(constants.TREND['year_graph'], fetch_data(hours_to_fetch=OPTION.months * 31 * 24, aggregation='A'),
                   f" trend per dag afgelopen maanden ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})" )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a trendgraph")
    parser.add_argument('-hr', '--hours', type=int, help='create an hour-trend of <HOURS>')
    parser.add_argument('-d', '--days', type=int, help='create a day-trend of <DAYS>')
    parser.add_argument("-m", "--months", type=int, help="number of months of data to use for the graph")
    parser_group = parser.add_mutually_exclusive_group(required=False)
    parser_group.add_argument("--debug", action="store_true", help="start in debugging mode")
    OPTION = parser.parse_args()
    if OPTION.hours == 0:
        OPTION.hours = 80
    if OPTION.days == 0:
        OPTION.days = 80
    if OPTION.months == 0:
        OPTION.months = 38

    if OPTION.debug:
        print(OPTION)
        DEBUG = True
        print("DEBUG-mode started")
    main()
