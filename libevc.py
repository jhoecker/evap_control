#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
import serial
import time


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
        self.controller = EVC()

    def estab_cont(self, EVC_controller):
        '''estab_cont establishes the communication with the EVC300 and reads
        the parameters the first time.'''
        self.controller = EVC_controller
        self.status()

    def status(self):
        '''Returns all evaporator parameters.'''
        self.fil = self.controller.get_fil()
        self.emis = self.controller.get_emis()
        self.flux = self.controller.get_flux()
        self.temp = self.controller.get_temp()
        self.hv = self.controller.get_hv()
        self.emiscon = self.controller.get_emiscon()

    def print_status(self):
        self.status()
        print('FIL  {0:3.2f} A     EMIS  {1:2.1f} mA'.format(self.fil, self.emis))
        print('FLUX  {0} nA   VOLT  {1:3.0f} V'.format(self.flux, self.hv))
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
        #### DEBUG ####
        print(dt, values)
        ###############
        for val in values:
            self.controller.set_hv(val)
            time.sleep(1.5)


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

#    def __del__(self):
#        '''Destroys EVC object.'''
#        print('EVC object deleted')

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
        old_val = self._get_value(str_val)
        dval = new_val - old_val
        #### DEBUG #####
        print('old_val = {0} \ndval = {1}'.format(old_val, dval))
        ################
        nn = 0
        vsign = '+'
        if dval < 0:
            vsign = '-'
        #### DEBUG ####
        print('SET {0} {1}{2:3.1f}\r\n'.format(str_val, vsign, abs(dval)))
        ###############
        ## TODO: Raise exception if command unknown, value invalid, etc.
        self.ser.write('SET {0} {1}{2:3.1f}\r\n'.format(str_val, vsign, abs(dval)))
        time.sleep(0.1)        
        if self.ser.inWaiting() > 0:
            print(self.ser.read(self.ser.inWaiting()))

    def set_emiscon(self, emiscon):
        self.ser.write('SET Emiscon {0} \r\n'.format(emiscon))
        
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
        #### DEBUG ####
        print('EMISCON = {}'.format(self._get_value('Emiscon')))
        ###############
        return self._get_value('Emiscon')

    def set_emis(self, new_emis):
        '''Sets emission current. Checks before whether the evaporator is in
        emission control.'''
        # Checking every time if emissioncontrol is on might be a bit
        # overloading?
        maxdiffemis = 1.5
        #if self.get_emiscon() == 0:
        self._set_val('EMIS', new_emis, maxdiffemis)
        #else:
        #    print('Err set_emis: No emission control.')


class Data():
    '''Class to save parameters in list.'''
    def __init__(self):
        '''Initialize data attributes name and list.'''
        self.tstart = time.time()
        self.time = []
        self.ylst1 = []
        self.ylst2 = []

    def save(self, fname):
        '''Saves data array to hard disk.'''
        fl = file(fname, 'w')
        for ii in range(0,len(self.time)):
            fl.write('{0}    {1}    {2}\n'.format(self.time[ii], self.ylst1[ii], self.ylst2[ii]))

    def add_val(self, yvalue1, yvalue2):
        '''Adds values to data lists.'''
        self.yvalue1 = yvalue1
        self.yvalue2 = yvalue2
        self.time.append(round(time.time()-self.tstart, 0))
        self.ylst1.append(yvalue1)
        self.ylst2.append(yvalue2)

class DriveVal():
    '''Change Val raises or lowers a value within a given duration by a
    function.'''
    def __init__(self, duration, startval, endval, valrate):
        self.duration = duration
        self.dt_min = 1.5  # sec
        self.valrate = valrate
        self.startval = startval
        self.dval = endval - startval 

    def calc_lintimestep(self):
        n = int(self.dval/self.valrate)
        self.dt = self.duration/n
        #### DEBUG ####
        print('n = {}, dt = {}'.format(n, self.dt))
        ###############
        if self.dt < self.dt_min:
            # TODO: Better raise exception here
            print('Err calc_lintimestep: Time step too small (dt < {0})'
                  .format(self.dt_min))
            vals = [self.startval]
        else:
            vals = [self.startval+ii*self.valrate for ii in range(1, n+1)]
        return self.dt, vals

