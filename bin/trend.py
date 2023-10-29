#!/usr/bin/env python3
"""Create trendbargraphs for various periods of data."""

import argparse
import os
import sqlite3 as s3
import warnings
from datetime import datetime as dt

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import constants

warnings.simplefilter(action="ignore", category=FutureWarning)

# fmt: off
parser = argparse.ArgumentParser(description="Create a trendgraph")
parser.add_argument("-hr", "--hours", type=int, help="create an hour-trend of <HOURS>")
parser.add_argument("-d", "--days", type=int, help="create a day-trend of <DAYS>")
parser.add_argument("-m", "--months", type=int,
                    help="number of months of data to use for the graph")
parser_group = parser.add_mutually_exclusive_group(required=False)
parser_group.add_argument("--debug", action="store_true", help="start in debugging mode")
OPTION = parser.parse_args()
# fmt: on

# constants
DEBUG = False  # sort of
# app_name :
HERE = os.path.realpath(__file__).split("/")
# runlist id for daemon :
MYID = HERE[-1]
# MYAPP = HERE[-3]
MYROOT = "/".join(HERE[0:-3])
NODE = os.uname()[1]

# example values:
# HERE: ['', 'home', 'pi', 'upsdiagd', 'bin', 'ups.py']

DATABASE = constants.TREND["database"]
TABLE = constants.TREND["sql_table"]


def fetch_data(hours_to_fetch=48, aggregation="5min"):
    """Query the database to fetch the requested data

    Args:
        hours_to_fetch (int): number of hours of data to fetch
        aggregation (str): number of minutes to aggregate per datapoint

    Returns:
        dictionary of dataframes
    """
    df_v = None
    df_chg = None
    df_run = None
    if DEBUG:
        print("*** fetching UPS data ***")
    where_condition = f" (sample_time >= datetime('now', '-{hours_to_fetch + 1} hours'))"
    s3_query = f"SELECT * FROM {TABLE} WHERE {where_condition}"
    if DEBUG:
        print(s3_query)
    with s3.connect(DATABASE) as con:
        df = pd.read_sql_query(s3_query, con, parse_dates="sample_time", index_col="sample_epoch")
    for c in df.columns:
        if c not in ["sample_time"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df.index = (
        pd.to_datetime(df.index, unit="s").tz_localize("UTC").tz_convert("Europe/Amsterdam")
    )
    # resample to monotonic timeline
    df = df.resample(f"{aggregation}").mean()
    df = df.interpolate()
    if DEBUG:
        print(df)
    df_v = collate(
        None, df, columns_to_drop=["charge_bat", "load_ups", "runtime_bat", "volt_bat"]
    )
    df_chg = collate(None, df, columns_to_drop=["volt_in", "volt_bat", "load_ups", "runtime_bat"])
    df_run = collate(None, df, columns_to_drop=["volt_in", "volt_bat", "charge_bat", "load_ups"])

    data_dict = {"V": df_v, "CHG": df_chg, "RUN": df_run}
    return data_dict


def collate(prev_df, data_frame, columns_to_drop=None):
    if columns_to_drop is None:
        columns_to_drop = []
    # drop the 'columns_to_drop'
    for col in columns_to_drop:
        data_frame = data_frame.drop(col, axis=1, errors="ignore")
    # if DEBUG:
    #     print()
    #     print(new_name)
    #     print(data_frame)
    # collate both dataframes
    if prev_df is not None:
        data_frame = pd.merge(prev_df, data_frame, left_index=True, right_index=True, how="outer")
    if DEBUG:
        print(data_frame)
    return data_frame


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


def plot_graph(output_file, data_dict, plot_title):
    """Plot the data into a graph

    Args:
        output_file (str): (str) name of the trendgraph file
        data_dict (dict): contains the data for the lines. Each key-value pair
                          is a separate pandas Dataframe: {'df': Dataframe}
        plot_title (str): title to be displayed above the plot
    Returns:
        None
    """
    if DEBUG:
        print("*** plotting ***")
    fig_x = 10
    fig_y = 2.5
    fig_fontsize = 6.5
    ahpla = 0.6
    for parameter in data_dict:
        if DEBUG:
            print(parameter)
        data_frame = data_dict[parameter]
        fig_x = 20
        fig_y = 7.5
        fig_fontsize = 13
        ahpla = 0.7

        # ###############################
        # Create a line plot of temperatures
        # ###############################
        plt.rc("font", size=fig_fontsize)
        ax1 = data_frame.plot(kind="line", figsize=(fig_x, fig_y))
        # linewidth and alpha need to be set separately
        for i, l in enumerate(ax1.lines):  # pylint: disable=W0612
            plt.setp(l, alpha=ahpla, linewidth=2, linestyle="-")
        ax1.set_ylabel(parameter)
        if parameter == "temperature_ac":
            ax1.set_ylim([12, 28])
        ax1.legend(loc="lower left", ncol=8, framealpha=0.2)
        ax1.set_xlabel("Datetime")
        ax1.grid(which="major", axis="y", color="k", linestyle="--", linewidth=0.5)
        plt.title(f"{parameter} {plot_title}")
        plt.tight_layout()
        plt.savefig(fname=f"{output_file}_{parameter}.png", format="png")


def main():
    """
    This is the main loop
    """
    if OPTION.hours:
        # plot_graph(
        #     f'/tmp/{MYAPP}/site/img/pastday_', fetch_last_day(OPTION.hours),
        #     f"Trend afgelopen uren ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})"
        # )
        plot_graph(
            constants.TREND["day_graph"],
            fetch_data(hours_to_fetch=OPTION.hours, aggregation="5min"),
            f" trend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
        )
    if OPTION.days:
        # plot_graph(
        #     f'/tmp/{MYAPP}/site/img/pastmonth_',
        #     fetch_last_day(OPTION.days * 24),
        #     f"Trend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})"
        # )
        plot_graph(
            constants.TREND["month_graph"],
            fetch_data(hours_to_fetch=OPTION.days * 24, aggregation="H"),
            f" trend per uur afgelopen maand ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
        )
    if OPTION.months:
        # plot_graph(
        #     f'/tmp/{MYAPP}/site/img/pastmonth_',
        #     fetch_last_day(OPTION.days * 24),
        #     f"Trend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})"
        # )
        plot_graph(
            constants.TREND["year_graph"],
            fetch_data(hours_to_fetch=OPTION.months * 31 * 24, aggregation="D"),
            f" trend per dag afgelopen maanden ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
        )


if __name__ == "__main__":
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
