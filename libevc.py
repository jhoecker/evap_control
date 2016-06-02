#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
    (C) Copyright 2015 Paul Brehmer, Keno Harbort, Jan Höcker

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as
    published by the Free Software Foundation; either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this program. If not, see
    <http://www.gnu.org/licenses/>.
'''

from __future__ import print_function
from __future__ import division
import serial
import time


class EvapParams():
    '''EVCstate contains the state of all EVC / evaporator parameters like
    emission (emis), temperature (temp), highvoltage (hv), fil (filament),
    emiscon (emission control: 1 = off, 0 = on) and flux.'''
    def __init__(self, evap_controller):
        '''Initialize parameters. Start with None to show that they
        are not set.'''
        self.emis = None
        self.temp = None
        self.hv = None
        self.flux = None
        self.fil = None
        self.degas = False
        self.estab_cont(evap_controller)

    def estab_cont(self, evap_controller):
        '''estab_cont establishes the communication with the EVC300 and reads
        the parameters the first time.'''
        if evap_controller == 'EVC':
            self.controller = EVC()

    def update_params(self):
        '''Returns all evaporator parameters.'''
        self.fil = self.get_fil()
        self.emis = self.get_emis()
        self.flux = self.get_flux()
        self.temp = self.get_temp()
        self.hv = self.get_hv()

    def print_status(self):
        ''' Print evaporator parameters to stdout.'''
        print('FIL  {0:3.2f} A     EMIS  {1:2.1f} mA'.format(self.fil, self.emis))
        print('FLUX  {0} nA   VOLT  {1:3.0f} V'.format(self.flux, self.hv))
        print('TMP  {0:2.1f} C'.format(self.temp))

    def change_emis(self, endemis, duration):
        '''Raises or loweres emission current time depending.
        Necessary parameters are the final emission current endemis and the
        time (duration) in which the final emission current should be reached
        (in sec).'''
        drive_emis = DriveVal(duration, self.emis, endemis, 0.1)
        dt, values = drive_emis.calc_lintimestep()
        #### DUMMY values for testing #####
        #drive_emis = DriveVal(duration, 1, endemis, 0.1)
        #dt, values = drive_emis.calc_lintimestep()
        #####
        t_start = time.time()
        for val in values:
            time.sleep(dt)
            if self.degas is True:
                self.set_emis(val)
                print('t_run = {} s, Value = {}'.format(
                    round(time.time()-t_start,2), val))
            else:
                print('Auto-raise emission stopped.')
                return
        self.degas = False
        print('Auto-raising done')
        return self.degas

    def change_hv(self, endhv):
        '''Raises or lowers hv value immediately.'''
        self.set_hv(endhv)
        time.sleep(1)

    def get_fil(self):
        '''Reads fil.'''
        return self.controller.get_value('Fil')

    def get_emis(self):
        '''Reads emis.'''
        return self.controller.get_value('Emis')

    def get_flux(self):
        '''Reads flux.'''
        return self.controller.get_value('Flux')*10**9

    def get_hv(self):
        '''Reads volt.'''
        return self.controller.get_value('HV')

    def get_temp(self):
        '''Reads temp.'''
        return self.controller.get_value('Temp')

    def set_hv(self, new_voltage):
        '''Sets volt.'''
        maxdiffhv = 20
        self.controller.set_val('HV', new_voltage, self.hv, maxdiffhv)

    def set_emis(self, new_emis):
        '''Sets emission current. Checks before whether the evaporator is in
        emission control.'''
        # Checking every time if emissioncontrol is on might be a bit
        # overloading?
        maxdiffemis = 1.5
        if self.emis > 3.0:
            self.controller.set_val('EMIS', new_emis, self.emis, maxdiffemis)
        else:
            print('Err set_emis: Emission too low. Set Emission forbidden.')


class EVC():
    '''Class to communicate with EVC300 controller.'''
    def __init__(self):
        '''Initializes the communication with the EVC300.'''
        # settings for EVC300
        # give permission to user to access port ttyUSB0 -> links.txt
        # BUG in EVC300: Emission control not remote available
        try:
            self.ser = serial.Serial(
                baudrate=57600,
                port='/dev/ttyUSB0',
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=True,
                bytesize=serial.EIGHTBITS,
                timeout=1)
            print('evap: Serial port to EVC open')
        except serial.SerialException as err_msg:
            print('Not able to open serial port: {}'.format(err_msg))

    def get_value(self, str_val):
        '''Reads value of parameter given by str_val. Returns float number.'''
        self.ser.write('GET ' + str_val + '\r\n')
        num = ''
        time.sleep(0.01)
        num = float(self.ser.read(self.ser.inWaiting()))
        return num

    def set_val(self, str_val, new_val, old_val, maxdiff):
        '''Writes new value EVC. maxdiff gives the maximal allowed difference.'''
        dval = new_val - old_val
        if dval > maxdiff:
            print('set_val Err: Value change of {0} larger than allowed.\
                Maximal allowed {1}'.format(dval, maxdiff))
            return
        vsign = '+'
        if dval < 0:
            vsign = '-'
        ## TODO: Raise exception if command unknown, value invalid, etc.
        self.ser.write('SET {0} {1}{2:3.1f}\r\n'.format(str_val, vsign, abs(dval)))
        time.sleep(0.1)
        if self.ser.inWaiting() > 0:
            print(self.ser.read(self.ser.inWaiting()))




class Data():
    '''Class to save parameters in list.'''
    def __init__(self):
        '''Initialize data attributes name and list.'''
        self.tstart = time.time()
        self.time = []
        self.flux = []
        self.emis = []

    def save(self, fname):
        '''Saves data arrays to hard disk.'''
        fl = file(fname, 'w')
        for ii in range(0, len(self.time)):
            fl.write('{0}    {1}    {2}\n'.format(self.time[ii],
                     self.flux[ii], self.emis[ii]))

    def add_val(self, yvalue1, yvalue2):
        '''Adds values to data lists.'''
        self.time.append(round(time.time()-self.tstart, 0))
        self.flux.append(yvalue1)
        self.emis.append(yvalue2)


class DriveVal():
    '''DriveVal raises or lowers a value within a given duration by a
    function. Valstep is the delta which is used to raise by every time
    step.'''
    def __init__(self, duration, startval, endval, valstep):
        self.duration = duration
        self.dt_min = 1.5  # sec
        self.valstep = valstep
        self.startval = startval
        self.dval = endval - startval

    def calc_lintimestep(self):
        '''Calculates and returns the timestep dt within the value is raised
        by valstep and a list of values to which the value is raised.'''
        n = int(self.dval/self.valstep)
        self.dt = self.duration/n
        #### DEBUG ####
        print('n = {}, dt = {}'.format(n, self.dt))
        ###############
        if self.dt < self.dt_min:
            print('Err calc_lintimestep: Time step too small (dt < {0})'
                  .format(self.dt_min))
            vals = [self.startval]
        else:
            vals = [self.startval+ii*self.valstep for ii in range(1, n+1)]
        return self.dt, vals
