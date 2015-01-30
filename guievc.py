#!/usr/bin/python
# -*- coding:utf-8 -*-

import os
import pprint
import sys
import wx
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
import numpy as np
import pylab
import serial
import libevc
import time

evap = libevc.EvapParams()
evc = libevc.EVC()
data = libevc.Data()

class EnterSelectElement(wx.Panel):
    """ A static box with a enter-text-field"""
    def __init__(self, parent, ID, label, initval):
        wx.Panel.__init__(self, parent, ID)
        
        self.value = initval
        
        box = wx.StaticBox(self, -1, label)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        self.manual_text = wx.TextCtrl(self, -1, 
            size=(35,-1),
            value=str(initval),
            style=wx.TE_PROCESS_ENTER)

        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.manual_text)

        parameters = ['EMIS', 'VOLT', 'None']


        self.select_value = wx.ComboBox(self, -1, choices=parameters, style=wx.CB_READONLY)
        self.select_value.SetValue(parameters[2])
        self.on_combo(self.select_value)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo, self.select_value)
        
        manual_box = wx.BoxSizer(wx.HORIZONTAL)
        manual_box.Add(self.manual_text, flag=wx.ALIGN_CENTER_VERTICAL)
        manual_box.Add(self.select_value, flag=wx.ALIGN_RIGHT)

        sizer.Add(manual_box, 0, wx.ALL, 10)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    def on_update_manual_text(self, event):
        self.manual_text.Enable(self.radio_manual.GetValue())
    
    def on_text_enter(self, event):
        self.value = self.manual_text.GetValue()
        self.setting_value(self.value)
        time.sleep(1)

    def is_auto(self):
        return self.radio_auto.GetValue()
        
    def manual_value(self):
        return self.value

    def setting_value(self, input):
        if self.paramSelection == 'VOLT':
            evc.set_hv(int(input))
        elif self.paramSelection == 'EMIS':
            evc.set_emis(int(input))
        elif self.paramSelection == 'None':
            print 'No Selection'
    def on_combo(self, event):
        self.paramSelection = self.select_value.GetValue()

class EvapGUI(wx.Frame):
    '''The main frame of the application'''
    title = 'EVC Data Graph'

    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)
        
        evap.status()
        self.data_fil = [evap.fil]
        self.data_emis = [evap.emis]
        self.paused = False

        self.create_main_panel()
        
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)        
        self.redraw_timer.Start(2000)

    def create_main_panel(self):
        self.panel = wx.Panel(self)

        self.init_plot_fil()
        self.init_plot_emis()

        self.canvas_fil = FigCanvas(self.panel, -1, self.fig_fil)
        self.canvas_emis = FigCanvas(self.panel, -1, self.fig_emis)

        self.set_value = EnterSelectElement(self.panel, -1, 'Set Value', 15)

        self.pause_button = wx.Button(self.panel, -1, 'Pause')
        self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)

        self.save_button = wx.Button(self.panel, -1, 'Save as...')
        self.Bind(wx.EVT_BUTTON, self.on_save_button, self.save_button)

        self.cb_grid = wx.CheckBox(self.panel, -1, 'Show Grid', style=wx.ALIGN_LEFT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.cb_grid.SetValue(True)

        self.fix_axes = wx.CheckBox(self.panel, -1, 'Fix Axes', style=wx.ALIGN_LEFT)
        self.Bind(wx.EVT_CHECKBOX, self.on_fix_axes, self.fix_axes)
        self.fix_axes.SetValue(False)

        self.hbox1 = wx.BoxSizer(wx.VERTICAL)
        self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL)
        self.hbox1.Add(self.save_button, border=5, flag=wx.ALL)
        self.hbox1.Add(self.cb_grid, border=2, flag=wx.ALL)
        self.hbox1.Add(self.fix_axes, border=2, flag=wx.ALL)

        self.fil = wx.StaticText(self.panel, label=str(evap.fil))
        self.emis = wx.StaticText(self.panel, label=str(evap.emis))
        self.flux = wx.StaticText(self.panel, label=str(evap.flux))
        self.hv = wx.StaticText(self.panel, label=str(evap.hv))
        self.temp = wx.StaticText(self.panel, label=str(evap.temp))

        self.hbox2 = wx.BoxSizer(wx.VERTICAL)
        self.hbox2.AddMany([self.fil, self.emis, self.flux, self.hv, self.temp])

        self.hbox3 = wx.BoxSizer(wx.VERTICAL)
        self.hbox3.AddMany([(wx.StaticText(self.panel, label='FIL')), 
            (wx.StaticText(self.panel, label='EMIS')), 
            (wx.StaticText(self.panel, label='FLUX')), 
            (wx.StaticText(self.panel, label='VOLT')), 
            (wx.StaticText(self.panel, label='TMP'))])

        self.hbox4 = wx.BoxSizer(wx.VERTICAL)
        self.hbox4.AddMany([(wx.StaticText(self.panel, label='A')), 
            (wx.StaticText(self.panel, label='mA')), 
            (wx.StaticText(self.panel, label='nA')), 
            (wx.StaticText(self.panel, label='V')), 
            (wx.StaticText(self.panel, label='°C'))])

        self.hbox5 = wx.BoxSizer(wx.VERTICAL)
        self.hbox5.Add(self.canvas_fil, 1, flag=wx.ALL | wx.GROW | wx.ALIGN_TOP)
        self.hbox5.Add(self.canvas_emis, 1, flag=wx.ALL | wx.GROW | wx.ALIGN_BOTTOM)

        self.hbox6 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox6.Add(self.hbox3, 0, flag=wx.LEFT | wx.RIGHT | wx.GROW | wx.ALIGN_LEFT, border=40)
        self.hbox6.Add(self.hbox2, 0, flag=wx.RIGHT | wx.GROW, border=15)
        self.hbox6.Add(self.hbox4, 0, flag=wx.RIGHT | wx.GROW | wx.ALIGN_TOP, border=10)
        
        self.hbox7 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox7.Add(self.set_value, 0, flag=wx.RIGHT | wx.GROW | wx.ALIGN_LEFT)

        self.hbox8 = wx.BoxSizer(wx.VERTICAL)
        self.hbox8.Add(self.hbox6, 1, flag=wx.ALL | wx.GROW | wx.ALIGN_TOP | wx.ALIGN_LEFT)
        self.hbox8.Add(self.hbox7, 0, flag=wx.ALL | wx.GROW | wx.ALIGN_LEFT)        

        self.vbox = wx.BoxSizer(wx.HORIZONTAL)
        self.vbox.Add(self.hbox8, 1, flag=wx.ALL | wx.GROW | wx.ALIGN_LEFT, border=15)
        self.vbox.Add(self.hbox5, 1, flag=wx.ALL | wx.GROW | wx.ALIGN_CENTER, border=5)
        self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_TOP | wx.ALIGN_RIGHT | wx.GROW | wx.ALL)
        
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

    def set_textboxlabels(self, fil, emis, flux, hv, temp):
        self.fil.SetLabel(fil)
        self.emis.SetLabel(emis)
        self.flux.SetLabel(flux)
        self.hv.SetLabel(hv)
        self.temp.SetLabel(temp)

    def init_plot_fil(self):
        self.dpi = 100
        self.fig_fil = Figure((3.0, 3.0), dpi=self.dpi)

        self.axes_fil = self.fig_fil.add_subplot(111)
        self.axes_fil.set_axis_bgcolor('black')
        self.axes_fil.set_title('FLUX', size=12)
        
        pylab.setp(self.axes_fil.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes_fil.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        #
        self.plot_data_fil = self.axes_fil.plot(
            self.data_fil, 
            linewidth=1,
            color=(1, 1, 0),
            )[0]
        self.plot_data_fil.set_xdata(np.arange(0,5))
        self.plot_data_fil.set_ydata(np.arange(0,5))

    def init_plot_emis(self):
        self.dpi = 100
        self.fig_emis = Figure(figsize=(3.0, 3.0), dpi=self.dpi)

        self.axes_emis = self.fig_emis.add_subplot(111)
        self.axes_emis.set_axis_bgcolor('black')
        self.axes_emis.set_title('EMIS', size=12)
        
        pylab.setp(self.axes_emis.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes_emis.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        #
        self.plot_data_emis = self.axes_emis.plot(
            self.data_emis, 
            linewidth=1,
            color=(0, 1, 1),
            )[0]

    def draw_plot_fil(self):
        """ Redraws the plot of FIL"""
        xmax = len(self.data_fil) if len(self.data_fil) > 300 else 300
        ymax = round(max(self.data_fil), 0) + 1

        if self.cb_grid.IsChecked():
            self.axes_fil.grid(True, color='gray')
        else:
            self.axes_fil.grid(False)

        if self.fix_axes.IsChecked():
            xmin = 0
            ymin = 0
        else:
            xmin = xmax - 300
            ymin = round(min(self.data_fil), 0) - 0.1

        self.axes_fil.set_xbound(lower=xmin, upper=xmax)
        self.axes_fil.set_ybound(lower=ymin, upper=ymax)
        self.plot_data_fil.set_xdata(np.arange(len(self.data_fil))*2)
        self.plot_data_fil.set_ydata(np.array(self.data_fil))

        self.canvas_fil.draw()

    def draw_plot_emis(self):
        """ Redraws the plot of EMIS"""
        xmax = len(self.data_emis) if len(self.data_emis) > 300 else 300
        ymax = round(max(self.data_emis), 0) + 1

        if self.cb_grid.IsChecked():
            self.axes_emis.grid(True, color='gray')
        else:
            self.axes_emis.grid(False)

        if self.fix_axes.IsChecked():
            xmin = 0
            ymin = 0
        else:
            xmin = xmax - 300
            ymin = round(min(self.data_emis), 0) - 0.1

        self.axes_emis.set_xbound(lower=xmin, upper=xmax)
        self.axes_emis.set_ybound(lower=ymin, upper=ymax)
        self.plot_data_emis.set_xdata(np.arange(len(self.data_emis))*2)
        self.plot_data_emis.set_ydata(np.array(self.data_emis))
        
        self.canvas_emis.draw()

    def on_pause_button(self, event):
        self.paused = not self.paused
    
    def on_update_pause_button(self, event):
        label = 'Resume' if self.paused else 'Pause'
        self.pause_button.SetLabel(label)

    def on_save_button(self, event):
        file_choices = "TXT (*.txt)|*.txt"

        dlg = wx.FileDialog(
            self,
            message="Save data as...",
            defaultDir=os.getcwd(),
            defaultFile="data.txt",
            wildcard=file_choices,
            style=wx.SAVE)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            data.save(path)

    def on_cb_grid(self, event):
        self.draw_plot_fil()
        self.draw_plot_emis()

    def on_fix_axes(self, event):
        self.draw_plot_fil()
        self.draw_plot_emis()

    def on_redraw_timer(self, event):
        # if paused do not add data, but still redraw the plot
        # (to respond to scale modifications, grid change, etc.)
        if not self.paused:
            evap.status()
            self.data_fil.append(evap.flux*10**10)
            self.data_emis.append(evap.emis)
            data.add_val(evap.flux, evap.emis)

        self.draw_plot_fil()
        self.draw_plot_emis()
        self.set_textboxlabels(str(evap.fil), str(evap.emis), str(evap.flux), str(evap.hv), str(evap.temp))
    
    def on_exit(self, event):
        self.Destroy()

if __name__ == '__main__':
    app = wx.PySimpleApp()
    app.frame = EvapGUI()
    app.frame.Show()
    app.MainLoop()

