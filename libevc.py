#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
import serial
import time
#import sys


class EvapParams():
    '''EVCstate contains the state of all EVC / evaporator parameters like
    emission (emis), temperature (temp), highvoltage (hv), fil (filament),
    emiscon (emission control: 1 = off, 0 = on) and flux.'''
    def __init__(self):
        '''Initialize parameters. Start with None to show that they
        are not set.'''
        self.emis = None
        self.temp = None
        self.hv = None
        self.flux = None
        self.fil = None
        self.emiscon = 1
        self.controller = None

    def estab_cont(self, EVC_controller):
        '''estab_cont establishes the communication with the EVC300 and reads
        the parameters the first time.'''
        self.controller = EVC_controller
        self.controller.status()

    def status(self):
        '''Returns all evaporator parameters.'''
        self.fil = EVC.get_fil()
        self.emis = EVC.get_emis()
        self.flux = self.get_flux()
        self.volt = self.get_hv()
        self.temp = self.get_temp()

    def print_status(self):
        print('FIL  {0:3.2f} A     EMIS  {1:2.1f} mA'.format(self.fil, self.emis))
        print('FLUX  {0} nA   VOLT  {1:3.0f} V'.format(self.flux, self.volt))
        print('TMP  {0:2.1f} C'.format(self.temp))

    def drive_emis(self, endemis, duration):
        '''drive_emis raises or loweres emission current time depending.
        Necessary parameters are the final emission current endemis and the
        time (duration) in which the final emission current should be reached
        (in sec).'''
        drive_emis = DriveVal(duration, self.emis, endemis, 0.1)
        dt, values = drive_emis.calc_lintimestep()
        for val in values:
            self.controller.set_emis(val)
            time.sleep(dt)

    def change_hv(self, endhv, duration):
        '''drive_hv raises or loweres the high voltage time depending.
        Necessary parameters are the final voltage endhv and the
        time (duration) in which the final voltage should be reached
        (in sec).'''
        drive_hv = DriveVal(duration, self.hv, endhv, 1)
        dt, values = drive_hv.calc_lintimestep()
        for val in values:
            self.controller.set_hv(val)
            time.sleep(dt)


class EVC():
    '''Class to communicate EVC300 controller.'''
    ## TODO Check minimal time duration possible between two commads to EVC
    ## TODO The "get methods should return real numbers not strings
    def __init__(self):
        '''Initializes the communication with the EVC300.'''
        # settings for EVC300
        # give permission to user to access port ttyUSB0 -> links.txt
        # TODO Write error when no serial port open
        self.ser = serial.Serial(
            baudrate=57600,
            port='/dev/ttyUSB0',
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=True,
            bytesize=serial.EIGHTBITS,
            timeout=1)
        print('Serial port to EVC open')

    def __del__(self):
        '''Destroys EVC object.'''
        print('EVC object deleted')

    def _get_value(self, str_val):
        '''Reads value of parameter given by str_val. Returns float number.'''
        self.ser.write('GET ' + str_val + '\r\n')
        num = ''
        time.sleep(0.01)
        num = float(self.ser.read(self.ser.inWaiting()))
        return num

    def _set_val(self, str_val, new_val, maxdiff):
        '''Writes new value EVC. Check that the new value is really reached.
        maxdiff gives the maximal allowed difference.'''
        old_val = self.get_value(str_val)
        dval = new_val - old_val
        nn = 0
        while dval > maxdiff:
            nn += 1
            if dval > 0:
                sign = '+'
            elif dval < 0:
                sign = '-'
            self.ser.write('SET {0} {1} +{2:3.1f}'.format(str_val, sign, dval))
            time.sleep(0.1)
            old_val = self.get_value(str_val)
            dval = new_val - old_val
            if nn > 10:
                print('Error _set_val timeout:\
                        Stopped setting {0}\n'.format(str_val))
                break

    def get_fil(self):
        '''Reads fil'''
        return self._get_value('Fil')

    def get_emis(self):
        '''Reads emis'''
        return self._get_value('Emis')

    def get_flux(self):
        '''Reads flux'''
        return self._get_value('Flux')

    def get_hv(self):
        '''Reads volt'''
        return self._get_value('HV')

    def get_temp(self):
        '''Reads temp'''
        return self._get_value('Temp')

    def set_hv(self, new_voltage):
        '''Sets volt'''
        maxdiffhv = 1.5
        self._set_val('HV', new_voltage, maxdiffhv)

    def get_emiscon(self):
        '''get_emiscon reads the emission control status out
        (0: Emission control, 1: Filament control).'''
        return self._get_value('Emiscon')

    def set_emis(self, new_emis):
        '''Sets emission current. Checks before whether the evaporator is in
        emission control.'''
        # Checking every time if emissioncontrol is on might be a bit
        # overloading?
        maxdiffemis = 0.15
        if self.get_emiscon == 0:
            self._set_val('EMIS', new_emis, maxdiffemis)
        else:
            print('Err set_emis: No emission control.')


class Data():
    '''Class to save parameters in list.'''
    def __init__(self, data_type):
        '''Initialize data attributes name and list.'''
        self.name = data_type
        self.lst = []

    def save(self, fname):
        '''Saves data array to hard disk.'''
        self.fname = fname
        fl = file(fname, 'w')
        for val in self.lst:
            fl.write('{0}'.format(val))

    def add_val(self, value):
        '''Adds values to data list.'''
        self.value = value
        self.lst.append(value)


class DriveVal():
    '''Change Val raises or lowers a value within a given duration by a
    function.'''
    def __init__(self, duration, startval, endval, valrate):
        self.duration = duration
        self.dt_min = 0.1  # sec
        self.valrate = valrate
        self.startval = startval
        self.dval = startval - endval

    def calc_lintimestep(self):
        n = self.dval/self.valrate
        self.dt = self.duration/n
        if self.dt < self.dat_min:
            # TODO: Better raise exception here
            print('Err calc_lintimestep: Time step too small (dt < {0}'
                  .format(self.dt_min))
            vals = self.startval
        else:
            vals = [self.startval+ii*self.dt*self.valrate for ii in range(0, n)]
        return self.dt, vals
