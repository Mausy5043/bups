#!/usr/bin/env python3

"""Common functions for use with the KAMSTRUP electricity meter"""

import subprocess
import syslog
import time

import mausy5043_common.funfile as mf

import constants


class Ups:
    """Class to interact with the UPS
    """

    def __init__(self, debug=False):

        self.dt_format = constants.DT_FORMAT  # "%Y-%m-%d %H:%M:%S"
        # starting values
        self.list_data = list()

        self.debug = debug
        if self.debug:
            self.telegram = list()

    def get_telegram(self):
        """Do the thing.
        Example:
        *2*  battery.charge: 100
            battery.charge.low: 20
        *4*  battery.runtime: 1875
            battery.type: PbAc
            device.mfr: EATON
            device.model: Protection Station 650
            device.serial: AN2E49008
            device.type: ups
            driver.name: usbhid-ups
            driver.parameter.pollfreq: 30
            driver.parameter.pollinterval: 2
            driver.parameter.port: auto
            driver.parameter.synchronous: no
            driver.version: 2.7.4
            driver.version.data: MGE HID 1.39
            driver.version.internal: 0.41
            input.transfer.high: 264
            input.transfer.low: 184
            outlet.1.desc: PowerShare Outlet 1
            outlet.1.id: 2
            outlet.1.status: on
            outlet.1.switchable: no
            outlet.2.desc: PowerShare Outlet 2
            outlet.2.id: 3
            outlet.2.status: on
            outlet.2.switchable: no
            outlet.desc: Main Outlet
            outlet.id: 1
            outlet.power: 25
            outlet.switchable: no
            output.frequency.nominal: 50
        *0*  output.voltage: 230.0
            output.voltage.nominal: 230
            ups.beeper.status: enabled
            ups.delay.shutdown: 20
            ups.delay.start: 30
            ups.firmware: 1.13
        *3*  ups.load: 2
            ups.mfr: EATON
            ups.model: Protection Station 650
            ups.power.nominal: 650
            ups.productid: ffff
            ups.serial: AN2E49008
            ups.status: OL
            ups.timer.shutdown: -1
            ups.timer.start: -1
            ups.vendorid: 0463
        """
        try:
            upsc = str(subprocess.check_output(['upsc', 'ups@localhost'], stderr=subprocess.STDOUT),
                       'utf-8').splitlines()
        except subprocess.CalledProcessError:
            mf.syslog_trace("Waiting 10s ...", syslog.LOG_ALERT, self.debug)

            time.sleep(10)  # wait to let the driver crash properly
            mf.syslog_trace("*** RESTARTING nut-server.service ***",
                            syslog.LOG_ALERT, self.debug)
            redo = str(subprocess.check_output(['sudo',
                                                'systemctl',
                                                'restart',
                                                'nut-server.service']
                                               ),
                       'utf-8').splitlines()
            mf.syslog_trace("Returned : {0}".format(redo), False, self.debug)

            time.sleep(15)
            mf.syslog_trace("!!! Retrying communication with UPS !!!",
                            syslog.LOG_ALERT,
                            self.debug)
            upsc = str(subprocess.check_output(['upsc',
                                                'ups@localhost'
                                                ],
                                               stderr=subprocess.STDOUT),
                       'utf-8').splitlines()

        ups_data = [-1.0, -1.0, -1.0, -1.0, -1.0]
        for element in upsc:
            var = element.split(': ')
            # if var[0] == 'input.voltage':
            if var[0] == 'output.voltage':
                ups_data[0] = float(var[1])
            # not available on Eaton Protection Station:
            if var[0] == 'battery.voltage':
                ups_data[1] = float(var[1])
            if var[0] == 'battery.charge':
                ups_data[2] = float(var[1])
            if var[0] == 'ups.load':
                ups_data[3] = float(var[1])
            if var[0] == 'battery.runtime':
                ups_data[4] = float(var[1])

        return ups_data
