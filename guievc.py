#!/usr/bin/python
# -*- coding:utf-8 -*-
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

import os
import wx
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas
import numpy as np
import pylab
import libevc
import time

## TODO
# - Remove EVC instance

evap = libevc.EvapParams('EVC')
evc = libevc.EVC()
data = libevc.Data()


class EnterSelectElement(wx.Panel):
    ''' A static box with a enter-text-field and combobox.
    Processes value on enter.'''
    def __init__(self, parent, ID, label, initval):
        '''Inits EnterSelectElement.'''
        wx.Panel.__init__(self, parent, ID)

        self.value = initval
        box = wx.StaticBox(self, -1, label)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        self.manual_text = wx.TextCtrl(self, -1,
                                       size=(35, -1),
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
        '''Gets value when text is entered.'''
        self.manual_text.Enable(self.radio_manual.GetValue())

    def on_text_enter(self, event):
        '''Calls setting_value function on Enter.'''
        self.value = self.manual_text.GetValue()
        self.setting_value(self.value)
        time.sleep(1)

    def manual_value(self):
        '''Gets entered value.'''
        return self.value

    def setting_value(self, input):
        '''Selects value from combo box.'''
        if self.paramSelection == 'VOLT':
            evc.set_hv(int(input))
        elif self.paramSelection == 'EMIS':
            evc.set_emis(int(input))
        elif self.paramSelection == 'None':
            print 'No Selection'

    def on_combo(self, event):
        '''Gets selection from combo box.'''
        self.paramSelection = self.select_value.GetValue()


class EvapGUI(wx.Frame):
    '''The main frame of the application'''
    title = 'EVAP - The EVC Data Graph'

    def __init__(self):
        '''Inits the main frame.'''
        wx.Frame.__init__(self, None, -1, self.title)
        self.redrawtime = 2  # in sec
        self.paused = True
        self.create_main_panel()
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
        self.redraw_timer.Start(self.redraw_timer*1000)

    def create_main_panel(self):
        '''Creates main panel with all the GUI elements. A lot of box sizers
        are used.'''
        self.panel = wx.Panel(self)

        self.init_plot_flux()
        self.init_plot_emis()

        self.canvas_flux = FigCanvas(self.panel, -1, self.fig_flux)
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

        self.font = wx.Font(11, wx.NORMAL, wx.DEFAULT, wx.NORMAL)

        self.line1 = wx.StaticLine(self.panel, -1, style=wx.LI_VERTICAL)
        self.line2 = wx.StaticLine(self.panel, -1, style=wx.LI_VERTICAL)
        self.line3 = wx.StaticLine(self.panel, -1, style=wx.LI_HORIZONTAL)
        self.line4 = wx.StaticLine(self.panel, -1, style=wx.LI_HORIZONTAL)

        self.fil = wx.StaticText(self.panel, label=str(evap.fil))
        self.emis = wx.StaticText(self.panel, label=str(evap.emis))
        self.flux = wx.StaticText(self.panel, label=str(evap.flux))
        self.hv = wx.StaticText(self.panel, label=str(evap.hv))
        self.temp = wx.StaticText(self.panel, label=str(evap.temp))
        self.caption = wx.StaticText(self.panel, label='Parameters')
        self.caption.SetFont(self.font)

        self.hbox1 = wx.BoxSizer(wx.VERTICAL)
        self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL)
        self.hbox1.Add(self.save_button, border=5, flag=wx.ALL)
        self.hbox1.Add(self.cb_grid, border=2, flag=wx.ALL)
        self.hbox1.Add(self.fix_axes, border=2, flag=wx.ALL)

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
        self.hbox5.Add(self.canvas_flux, 1, flag=wx.ALL | wx.EXPAND | wx.ALIGN_TOP, border=4)
        self.hbox5.Add(self.canvas_emis, 1, flag=wx.ALL | wx.EXPAND | wx.ALIGN_BOTTOM, border=4)

        self.hbox6 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox6.Add(self.hbox3, 0, flag=wx.RIGHT | wx.GROW | wx.ALIGN_LEFT, border=40)
        self.hbox6.Add(self.hbox2, 0, flag=wx.RIGHT | wx.GROW, border=15)
        self.hbox6.Add(self.hbox4, 0, flag=wx.RIGHT | wx.GROW | wx.ALIGN_TOP, border=10)

        self.hbox7 = wx.BoxSizer(wx.VERTICAL)
        self.hbox7.Add(self.caption, 0, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, border=5)
        self.hbox7.Add(self.line3, 0, flag=wx.BOTTOM | wx.GROW, border=10)
        self.hbox7.Add(self.hbox6, 0, flag=wx.ALL | wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.SHAPED)
        self.hbox7.Add(self.line4, 0, flag=wx.TOP | wx.BOTTOM | wx.GROW, border=10)
        self.hbox7.Add(self.set_value, 0, flag=wx.RIGHT | wx.ALIGN_LEFT)

        self.vbox = wx.BoxSizer(wx.HORIZONTAL)
        self.vbox.Add(self.hbox7, 0, flag=wx.ALL | wx.ALIGN_LEFT, border=15)
        self.vbox.Add(self.line1, 0, flag=wx.ALL | wx.GROW, border=5)
        self.vbox.Add(self.hbox5, 1, flag=wx.ALL | wx.GROW | wx.ALIGN_CENTER, border=5)
        self.vbox.Add(self.line2, 0, flag=wx.ALL | wx.GROW, border=5)
        self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_TOP | wx.ALIGN_RIGHT | wx.GROW | wx.ALL)

        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

    def set_textboxlabels(self, fil, emis, flux, hv, temp):
        '''Updates the text labels in status text field.'''
        self.fil.SetLabel(fil)
        self.emis.SetLabel(emis)
        self.flux.SetLabel(flux)
        self.hv.SetLabel(hv)
        self.temp.SetLabel(temp)

    def init_plot_flux(self):
        '''Inits the flux graph.'''
        self.dpi = 100
        self.fig_flux = Figure((3.0, 2.3), dpi=self.dpi)

        self.axes_flux = self.fig_flux.add_subplot(111)
        self.axes_flux.set_axis_bgcolor('black')
        self.axes_flux.set_title('Flux', size=10)
        self.axes_flux.set_aspect('auto')

        pylab.setp(self.axes_flux.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes_flux.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference
        # to the plotted line series
        self.plot_data_flux = self.axes_flux.plot(
            data.flux,
            linewidth=1,
            color=(1, 1, 0),
            )[0]

    def init_plot_emis(self):
        '''Inits the emis graph.'''
        self.dpi = 100
        self.fig_emis = Figure(figsize=(3.0, 2.3), dpi=self.dpi)

        self.axes_emis = self.fig_emis.add_subplot(111)
        self.axes_emis.set_axis_bgcolor('black')
        self.axes_emis.set_title('Emission current', size=10)
        self.axes_emis.set_aspect('auto')

        pylab.setp(self.axes_emis.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes_emis.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference
        # to the plotted line series
        self.plot_data_emis = self.axes_emis.plot(
            data.emis,
            linewidth=1,
            color=(0, 1, 1),
            )[0]

    def draw_plot_flux(self):
        '''Redraws the plot of FLUX'''
        twindow = 300
        #### DEBUG ####
        # print('data.flux = {}'.format(data.flux))
        # print('EVAP EMIS = {}'.format(evap.flux))
        try:
            xmax = len(data.flux)*self.redrawtime if len(data.flux)*self.redrawtime > twindow else twindow
            xmin = xmax - twindow
            ymax = round(max(data.flux), 0) + 1
            ymin = round(min(data.flux), 0) - 0.4
        except ValueError:
            xmax = twindow
            xmin = 0
            ymax = 1
            ymin = 0

        if self.cb_grid.IsChecked():
            self.axes_flux.grid(True, color='gray')
        else:
            self.axes_flux.grid(False)

        if self.fix_axes.IsChecked():
            xmin = 0
            ymin = 0

        self.axes_flux.set_xbound(lower=xmin, upper=xmax)
        self.axes_flux.set_ybound(lower=ymin, upper=ymax)
        self.plot_data_flux.set_xdata(np.arange(len(data.flux))*self.redrawtime)
        self.plot_data_flux.set_ydata(np.array(data.flux))

        self.canvas_flux.draw()

    def draw_plot_emis(self):
        '''Redraws the plot of EMIS'''
        twindow = 300
        try:
            xmax = len(data.emis)*self.redrawtime if len(data.emis)**self.redrawtime > twindow else twindow
            xmin = xmax - twindow
            ymax = round(max(data.emis), 0) + 1
            ymin = round(min(data.emis), 0) - 0.4
        except ValueError:
            xmax = twindow
            xmin = 0
            ymax = 1
            ymin = 0

        if self.cb_grid.IsChecked():
            self.axes_emis.grid(True, color='gray')
        else:
            self.axes_emis.grid(False)

        if self.fix_axes.IsChecked():
            xmin = 0
            ymin = 0

        self.axes_emis.set_xbound(lower=xmin, upper=xmax)
        self.axes_emis.set_ybound(lower=ymin, upper=ymax)
        self.plot_data_emis.set_xdata(np.arange(len(data.emis))*self.redrawtime)
        self.plot_data_emis.set_ydata(np.array(data.emis))

        self.canvas_emis.draw()

    def on_pause_button(self, event):
        '''Sets paused to false/true.'''
        self.paused = not self.paused

    def on_update_pause_button(self, event):
        '''Updates the label on the pause button.'''
        label = 'Resume' if self.paused else 'Pause'
        self.pause_button.SetLabel(label)

    def on_save_button(self, event):
        '''Creates save dialog on press button event.'''
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
        '''Continues drawing the graph when grid checkbox is checked.'''
        self.draw_plot_flux()
        self.draw_plot_emis()

    def on_fix_axes(self, event):
        '''Continues drawing the graph when grid checkbox is checked.'''
        self.draw_plot_flux()
        self.draw_plot_emis()

    def on_redraw_timer(self, event):
        '''Redraw timer updates all values of the graph and status text field.'''
        # if paused do not add data, but still redraw the plot
        # (to respond to scale modifications, grid change, etc.)
        if not self.paused:
            evap.update_params()
            data.add_val(evap.flux, evap.emis)
            self.draw_plot_flux()
            self.draw_plot_emis()
            self.set_textboxlabels(str(evap.fil), str(evap.emis), str(evap.flux),
                    str(evap.hv), str(evap.temp))

    def on_exit(self, event):
        '''Destroys the application when you close it.'''
        self.Destroy()

if __name__ == '__main__':
    app = wx.PySimpleApp()
    app.frame = EvapGUI()
    app.frame.Show()
    app.MainLoop()
