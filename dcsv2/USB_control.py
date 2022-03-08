# -*- coding: utf-8 -*-
"""
Created on Wed Aug 05 16:11:31 2015

@author: lcs/ihk/hnb3

Modified by Hugo Bergeron on August 5, 2015.

This is the main GUI code. I changed the code so it treats control loops in a
more symetrical way. This will prevent mistakes in the future.

The GUI takes a configuration dictionnary as an input. This dictionnary comes
from an XML file that was loaded in comb_box_temperature_control.pyw. This
dictionnary contains all the values needed and also subdictionnaries for the
control loops.
"""


from __future__ import unicode_literals
import sys, os, time, errno
from PyQt4 import QtGui, QtCore, uic #change PySide to PyQT4 if necessary

import numpy
import matplotlibwidget
import AsyncSocketComms
from control_loop import *
from NIUSB_DAQ import *

from combcontrol import DualCombControlWidget

progname = os.path.basename(sys.argv[0])
progversion = "0.2"

MAXSTRIKES = 3

tempcontGUI=uic.loadUiType('tempcont.ui')[0] # This converts the Ui file to python -- easier than cmd line prompt!
class ApplicationWindow(QtGui.QMainWindow, tempcontGUI):
    def __init__(self, configuration):
        super(ApplicationWindow, self).__init__()

        arduino_port = configuration['arduino_port']
        if arduino_port is None:
            self.laser_control_widget = None
        else:
            self.laser_control_widget = DualCombControlWidget(arduino_port, self)

        ################
        # Program settings

        # Copy configuration
        self.configuration = configuration

        # Get device names
        self.ni6009_devname = self.configuration['ni6009_devname']
        self.ni9264_devname = self.configuration['ni9264_devname']

        # Create dictionnary to map names to control loop indices
        self.ctrl_i = {}
        self.ctrl_i['Oscillator']  = 0
        self.ctrl_i['Transceiver'] = 1

        ################
        # Control loops

        # Create the control loops using a for loop
        self.control_loop_count = len(self.ctrl_i)
        self.control_loops = [None]*self.control_loop_count
        self.panic_strikes = [0]*self.control_loop_count
        for key in self.configuration['control_loops']:
            ctrl_loop_name = self.configuration['control_loops'][key]['name']
            try:
                i = self.ctrl_i[ctrl_loop_name]
            except KeyError:
                continue
            self.control_loops[i] = control_loop(self.configuration['control_loops'][key])

        # Set the initial setpoints and enables
        self.firstStep = True
        self.requested_enables = [0]*self.control_loop_count
        self.requested_setpoints = [0.0]*self.control_loop_count
        self.requested_adjusts = [0.0]*self.control_loop_count
        for i in range(self.control_loop_count):
            self.requested_enables[i] = self.control_loops[i].enabled_default
            self.requested_setpoints[i] = self.control_loops[i].temperature_default

        ################
        # Setup the socket server
        self.setpoint_adjust_Oscillator = 0.
        oscillator_port = self.control_loops[self.ctrl_i['Oscillator']].port
        self.IPC_serv = AsyncSocketComms.AsyncSocketServer(oscillator_port)

        self.setpoint_adjust_Transceiver = 0.
        trans_port = self.control_loops[self.ctrl_i['Transceiver']].port
        self.IPC_servt = AsyncSocketComms.AsyncSocketServer(trans_port)

        ################
        # Setup DAQ tasks
        #
        # 1) Analog in (start first, read values in the timer loop, stop)
        # 2) Analog out (start first, write values in the timer loop, stop)
        # 3) Digital (only initialized here, the task is created and destroyed everytime)

        # Analog in
        analog_in_devname  = self.ni6009_devname
        # Create list of channels
        analog_in_channels = list()
        for i in range(self.control_loop_count):
            analog_in_channels.append(self.control_loops[i].ni6009_actual_ch)
            analog_in_channels.append(self.control_loops[i].ni6009_setpoint_ch)
        # Create object
        self.usb_analog_in = NI_USB_Analog_In(analog_in_devname, analog_in_channels)
        # Start task
        self.usb_analog_in.start()

        # Analog out
        analog_out_devname  = self.ni9264_devname
        # Create list of channels
        analog_out_channels = list()
        for i in range(self.control_loop_count):
            analog_out_channels.append(self.control_loops[i].ni9264_output_ch)
        # Create object
        self.usb_analog_out = NI_USB_Analog_Out(analog_out_devname, analog_out_channels)
        # Start task
        self.usb_analog_out.start()

        # Digital out
        digital_out_devname = self.ni6009_devname
        # Create list of port/lines
        digital_out_ports = list()
        digital_out_lines = list()
        for i in range(self.control_loop_count):
            digital_out_ports.append(self.control_loops[i].ni6009_enable_port)
            digital_out_lines.append(self.control_loops[i].ni6009_enable_line)
        # Create object
        self.usb_digital_out = NI_USB_Digital_Out(digital_out_devname, digital_out_ports, digital_out_lines)

        ################
        # Misc
        self.logics_out_last = [None]*self.control_loop_count

        self.enable_plot = False
        self.timer_period = 0.250 # in seconds
        self.use_adjust_valuesOsc = False
        self.use_adjust_valuesTrans = False

        ################
        # Setup file operation
        self.write_to_file = 0
        self.path_name = 'temp_control_output'
        self.filename = time.strftime('temp_control_output\%Y%m%dT%H%M%S.txt')
        self.make_sure_path_exists('temp_control_output')

        ################
        # Setup GUI
        self.setStyleSheet(self.configuration['stylesheet'])
        self.setupUi(self)

        self.layout_laser.addWidget(self.laser_control_widget)

        self.connectToGUI()
        self.setupGraphs()
        self.plot_enable()
        self.statusBar().showMessage("Temperature Monitor")

        ################
        # Start timer
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.timerHandler)
        self.timer.start(round(1000*self.timer_period))

        self.t0 = time.time()

        ################
        # Show GUI
        self.show()

    ################################################################
    ## Cleanup function
    ################################################################
    def cleanup(self):
        if self.laser_control_widget is not None:
            self.laser_control_widget.close()
        self.timer.stop() # Stop timer
        self.usb_analog_in.stop() # Stop task
        self.usb_analog_out.stop() # Stop task
        self.IPC_serv.stopListening() # Stop socket
        self.IPC_servt.stopListening() # Stop socket

    def timerHandler(self):
        ########################## IPC for Oscillator setpoint #################################
        self.setpoint_max_adjust = 5.
        line = self.IPC_serv.run()
        if line:
            if line == 'COMMITADJUST':
                # Add adjust value to set point and then set adjust value to 0
                newSetPoint = self.requested_setpoints[self.ctrl_i['Oscillator']] + self.setpoint_adjust_Oscillator
                self.setpoint_adjust_Oscillator = 0
                # Validate input
                if self.control_loops[self.ctrl_i['Oscillator']].is_acceptable_setpoint(newSetPoint):
                    # Change setpoint
                    self.edits_userSetpoint[self.ctrl_i['Oscillator']].setText('{:.2f}'.format(newSetPoint))
                    self.requested_setpoints[self.ctrl_i['Oscillator']] = newSetPoint
            else:
                try:
                    self.setpoint_adjust_Oscillator += float(line)
                except:
                    self.setpoint_adjust_Oscillator = 0.

            # Implement limits:
            if self.setpoint_adjust_Oscillator > self.setpoint_max_adjust:
                self.setpoint_adjust_Oscillator = self.setpoint_max_adjust
                print('Clamped setpoint adjust osc to %f deg.' % self.setpoint_adjust_Oscillator)
            elif self.setpoint_adjust_Oscillator < -self.setpoint_max_adjust:
                self.setpoint_adjust_Oscillator = -self.setpoint_max_adjust
                print('Clamped setpoint adjust osc to %f deg.' % self.setpoint_adjust_Oscillator)

            print('Setpoint adjust osc by %f degrees C' % self.setpoint_adjust_Oscillator)
            # self.setTempSetpoint('Oscillator') #sets temperature setpoint for box

        # ...and now for transceiver
        line = self.IPC_servt.run()
        if line:
            if line == 'COMMITADJUST':
                # Add adjust value to set point and then set adjust value to 0
                newSetPoint = self.requested_setpoints[self.ctrl_i['Transceiver']] + self.setpoint_adjust_Transceiver
                self.setpoint_adjust_Transceiver = 0
                # Validate input
                if self.control_loops[self.ctrl_i['Transceiver']].is_acceptable_setpoint(newSetPoint):
                    # Change setpoint
                    self.edits_userSetpoint[self.ctrl_i['Transceiver']].setText('{:.2f}'.format(newSetPoint))
                    self.requested_setpoints[self.ctrl_i['Transceiver']] = newSetPoint
            else:
                try:
                    self.setpoint_adjust_Transceiver += float(line)
                except:
                    self.setpoint_adjust_Transceiver = 0.

            # Implement limits:
            if self.setpoint_adjust_Transceiver > self.setpoint_max_adjust:
                self.setpoint_adjust_Transceiver = self.setpoint_max_adjust
                print('Clamped setpoint adjust trans to %f deg.' % self.setpoint_adjust_Transceiver)
            elif self.setpoint_adjust_Transceiver < -self.setpoint_max_adjust:
                self.setpoint_adjust_Transceiver = -self.setpoint_max_adjust
                print('Clamped setpoint adjust trans to %f deg.' % self.setpoint_adjust_Transceiver)

            print('Setpoint adjust trans by %f degrees C' % self.setpoint_adjust_Transceiver)
            # self.setTempSetpoint('Transceiver') #sets temperature setpoint for box
        ##################################################################################

        # Handle the adjust values for the Oscillator control loop
        if self.use_adjust_valuesOsc == True:
            self.requested_adjusts[self.ctrl_i['Oscillator']] = self.setpoint_adjust_Oscillator
        else:
            self.requested_adjusts[self.ctrl_i['Oscillator']] = 0.0

        # Handle the adjust values for the Transceiver control loop
        if self.use_adjust_valuesTrans == True:
            self.requested_adjusts[self.ctrl_i['Transceiver']] = self.setpoint_adjust_Transceiver
        else:
            self.requested_adjusts[self.ctrl_i['Transceiver']] = 0.0

        ################################
        ## Read values from ADC
        ################################
        try:
            voltages_in  = self.usb_analog_in.read_values()
        except:
            for i in xrange(self.control_loop_count):
                self.setEnable(i, False)
            raise

        ################################
        ## Main computation
        ################################
        voltages_out = [0.0]*self.control_loop_count
        logics_out   = [0]*self.control_loop_count
        panics_out   = [False]*self.control_loop_count
        # For each control loop
        for i in range(self.control_loop_count):
            loop = self.control_loops[i]
            # Get the voltages
            voltage_in0 = voltages_in[i*2+0]
            voltage_in1 = voltages_in[i*2+1]
            # Get the validated user input
            loop.requested_enable   = self.requested_enables[i]
            loop.requested_setpoint = self.requested_setpoints[i]
            loop.requested_adjust   = self.requested_adjusts[i]
            # Do a computation step
            (voltage_out0, logic_out0, panic0) = loop.do_step(voltage_in0, voltage_in1)
            # Copy output of computation
            voltages_out[i] = voltage_out0 # voltage
            logics_out[i] = logic_out0     # enable (active high or low, depending on control loop)
            panics_out[i] = panic0         # panic signal. True when actual temperature is beyond limits

            if panic0 and loop.requested_enable:
                comb_number = i + 1
                self.panic_strikes[i] += 1
                print('WARNING: comb %i temp %0.2f outside limits (%0.1f, %0.1f); stike %i/%i' % \
                 (comb_number, loop.read_actual, loop.temperature_minimum,
                  loop.temperature_maximum, self.panic_strikes[i], MAXSTRIKES))
                if self.panic_strikes[i] >= MAXSTRIKES:
                    self.setEnable(i, False)
                    self.btns_enable[i].setChecked(False)
                    self.btns_disable[i].setChecked(True)
                    self.panic_strikes[i] = 0
            else:
                self.panic_strikes[i] = 0

        ################################
        ## Write values to DAC
        ################################
        self.usb_analog_out.write_values(voltages_out)

        ################################
        ## Write digital values
        ################################
        for i in range(self.control_loop_count):
            if self.firstStep == True or \
               self.logics_out_last[i] != logics_out[i]:
                self.usb_digital_out.write_value(i, logics_out[i])
        self.logics_out_last = logics_out

        ################################
        ## Update labels
        ################################
        for i in range(self.control_loop_count):
            self.lbls_userSetpoint[i].setText('%.3f' % self.control_loops[i].read_actual)
        self.lbl_oscAdjust.setText('Adjust: %.3f deg' % self.setpoint_adjust_Oscillator)
        self.lbl_transAdjust.setText('Adjust: %.3f deg' % self.setpoint_adjust_Transceiver)

        ################################
        ## Copy to y variable for legacy code
        ################################
        self.y = [self.control_loops[self.ctrl_i['Oscillator']].read_setpoint,
                  self.control_loops[self.ctrl_i['Oscillator']].read_actual,
                  self.control_loops[self.ctrl_i['Transceiver']].read_setpoint,
                  self.control_loops[self.ctrl_i['Transceiver']].read_actual,]

        ################################
        ## Legacy code starts here
        ################################
        if self.y:
            x = time.time() - self.t0
            self.oscgraphArray1=self.UpdateArray(self.oscgraphArray1,self.limitx,self.y[0])
            self.oscgraphArray2=self.UpdateArray(self.oscgraphArray2,self.limitx,self.y[1])
            self.receivergraphArray1=self.UpdateArray(self.receivergraphArray1,self.limitx,self.y[2])
            self.receivergraphArray2=self.UpdateArray(self.receivergraphArray2,self.limitx,self.y[3])
            self.timeArray=self.UpdateArray(self.timeArray,self.limitx,x)
            #except:
            #    pass

        if self.enable_plot:
            self.oscLine1.set_data(self.timeArray, self.oscgraphArray1)
            self.oscLine2.set_data(self.timeArray, self.oscgraphArray2)
            self.oscGraph.xlimleft = x - self.limitx*self.timer_period #limits xrange on plot to last 100 seconds
            self.oscGraph.xlimright = x + 1.0
            self.oscGraph.update_figure()

            self.receiverLine1.set_data(self.timeArray, self.receivergraphArray1)
            self.receiverLine2.set_data(self.timeArray, self.receivergraphArray2)
            self.receiverGraph.xlimleft = x - self.limitx*self.timer_period #limits xrange on plot to last 100 seconds
            self.receiverGraph.xlimright = x + 1.0
            self.receiverGraph.update_figure()

        if self.write_to_file:
            DAT = numpy.array([[x],[self.y[0]],[self.y[1]],[self.y[2]],[self.y[3]],[self.y[4]],[self.y[5]]])
            self.f_handle = file(self.filename,'a')
            numpy.savetxt(self.f_handle,numpy.column_stack(DAT))
            self.f_handle.close()

        self.firstStep = False

    def connectToGUI(self):
    #Connect temperture setpoint text
        # Set initial text
        self.edit_userSetpoint_Oscillator.setText( '%.3f' % self.requested_setpoints[self.ctrl_i['Oscillator']] )
        self.edit_userSetpoint_Transceiver.setText( '%.3f' % self.requested_setpoints[self.ctrl_i['Transceiver']] )
        # Press one the buttons depending on the enable state
        self.btn_enable_Oscillator.setChecked(self.requested_enables[self.ctrl_i['Oscillator']])
        self.btn_disable_Oscillator.setChecked(not self.requested_enables[self.ctrl_i['Oscillator']])
        self.btn_enable_Transceiver.setChecked(self.requested_enables[self.ctrl_i['Transceiver']])
        self.btn_disable_Transceiver.setChecked(not self.requested_enables[self.ctrl_i['Transceiver']])

        # Store the enable buttons in lists so we can use "for loops"
        self.btns_enable = [self.btn_enable_Oscillator,
                            self.btn_enable_Transceiver,]
        self.btns_disable = [self.btn_disable_Oscillator,
                             self.btn_disable_Transceiver,]
        # Connect temperature setpoint text boxes
        self.edit_userSetpoint_Oscillator.returnPressed.connect(lambda: self.setTempSetpoint(self.ctrl_i['Oscillator']))
        self.edit_userSetpoint_Transceiver.returnPressed.connect(lambda: self.setTempSetpoint(self.ctrl_i['Transceiver']))
        self.edits_userSetpoint = [self.edit_userSetpoint_Oscillator,
                                   self.edit_userSetpoint_Transceiver,]

        # Store the setpoint text boxes in lists so we can use "for loops"
        self.lbls_userSetpoint = [self.lbl_current_Oscillator,
                                  self.lbl_current_Transceiver,]

    #enable/disable outputs
        #Osc
        self.btn_enable_Oscillator.clicked.connect(lambda: self.setEnable(self.ctrl_i['Oscillator'], True))
        self.btn_disable_Oscillator.clicked.connect(lambda: self.setEnable(self.ctrl_i['Oscillator'], False))
        #XCVR
        self.btn_enable_Transceiver.clicked.connect(lambda: self.setEnable(self.ctrl_i['Transceiver'], True))
        self.btn_disable_Transceiver.clicked.connect(lambda: self.setEnable(self.ctrl_i['Transceiver'], False))

    #text input for setting y limits for graphs
        #osc
        self.oscGraphMin.returnPressed.connect(lambda: self.updateGraphAxes('Oscillator','lower_bound'))
        self.oscGraphMax.returnPressed.connect(lambda: self.updateGraphAxes('Oscillator','upper_bound'))
        #xcvr
        self.receiverGraphMin.returnPressed.connect(lambda: self.updateGraphAxes('Transceiver','lower_bound'))
        self.receiverGraphMax.returnPressed.connect(lambda: self.updateGraphAxes('Transceiver','upper_bound'))

    #adjust value
        self.oscAdjustString = ''
    #x-axis
        self.limitx = round(100/self.timer_period)
        self.edit_timeScale.returnPressed.connect(self.updateX)

        # Set initial values for the misc controls
        self.edit_timeScale.setText('100')
        self.oscGraphMin.setText('20')
        self.oscGraphMax.setText('30')
        self.receiverGraphMin.setText('20')
        self.receiverGraphMax.setText('30')

    #enable plotting of temperature data
        self.chk_enableGraph.clicked.connect(self.plot_enable)
    #enable logging of temperature data
        self.chk_enableDataLog.clicked.connect(self.log_data)
    #Use adjust values received from the socket or not:
        self.chk_useAdjustValues_Oscillator.clicked.connect(self.adjust_enableOsc)
        self.chk_useAdjustValues_Transceiver.clicked.connect(self.adjust_enableTrans)
        self.adjust_enableOsc()
        self.adjust_enableTrans()

    def setTempSetpoint(self, index):
        userInputText = self.edits_userSetpoint[index].text()
        try:
            # Convert to float
            userInputValue = float(userInputText)
            # Validate input
            if self.control_loops[index].is_acceptable_setpoint(userInputValue):
                # Change setpoint
                self.requested_setpoints[index] = userInputValue
        except:
            # We should specify which exception is catched...
            pass

    def setEnable(self, index, enable):
        print('Set temperature control %i to %s' % (index+1, enable))
        if self.laser_control_widget is not None:
            self.laser_control_widget.temp_set_enable(index, enable)
        self.requested_enables[index] = enable

    def setupGraphs(self):
    #Plot instantiation (from matplotlbwidget class)
        self.oscGraph= matplotlibwidget.MatplotlibWidget()
        self.oscGraph.title = "Comb 1\n(green= setpoint)"
        self.receiverGraph= matplotlibwidget.MatplotlibWidget()
        self.receiverGraph.title = "Comb 2\n(green = setpoint)"

        self.updateGraphAxes('Oscillator','lower_bound')
        self.updateGraphAxes('Oscillator','upper_bound')
        self.updateGraphAxes('Transceiver','lower_bound')
        self.updateGraphAxes('Transceiver','upper_bound')

    #Make arrays and plot objects to hold graph data
        self.timeArray = numpy.zeros(self.limitx)

        self.oscgraphArray1 = numpy.zeros(self.limitx)
        self.oscgraphArray2 = numpy.zeros(self.limitx)
        self.oscLine1, self.oscLine2, = self.oscGraph.axes.plot(numpy.zeros(self.limitx),numpy.zeros(self.limitx),'g',numpy.zeros(self.limitx),numpy.zeros(self.limitx),'b')

        self.receivergraphArray1 = numpy.zeros(self.limitx)
        self.receivergraphArray2 = numpy.zeros(self.limitx)
        self.receiverLine1, self.receiverLine2, = self.receiverGraph.axes.plot(numpy.zeros(self.limitx),numpy.zeros(self.limitx),'g',numpy.zeros(self.limitx),numpy.zeros(self.limitx),'b')

    def updateGraphAxes(self, box, bound):
         try:
            if box == 'Oscillator':
                if bound == 'lower_bound':
                    self.oscGraph.ylim_lower = float(self.oscGraphMin.text())
                elif bound == 'upper_bound':
                    self.oscGraph.ylim_upper = float(self.oscGraphMax.text())

            elif box == 'Transceiver':
                if bound == 'lower_bound':
                    self.receiverGraph.ylim_lower = float(self.receiverGraphMin.text())
                elif bound == 'upper_bound':
                    self.receiverGraph.ylim_upper = float(self.receiverGraphMax.text())
         except:
            pass

    def closeEvent(self, event):
        reply = QtGui.QMessageBox.question(self, 'Message',
            "Do you really want to quit?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            # Perform cleanup
            self.cleanup()
            event.accept()
        else:
            event.ignore()

    def make_sure_path_exists(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    def textInputHandler(self, event):
        print(event)

    def updateX(self):
        try:
            self.limitx = round(float(self.edit_timeScale.text())/self.timer_period)
        except:
            self.limitx = round(100./self.timer_period)

    def adjust_enableOsc(self):
        self.use_adjust_valuesOsc = self.chk_useAdjustValues_Oscillator.isChecked()

    def adjust_enableTrans(self):
        self.use_adjust_valuesTrans = self.chk_useAdjustValues_Transceiver.isChecked()

    #enable plotting
    def plot_enable(self):
        self.enable_plot = False
        if self.chk_enableGraph.isChecked():
            self.enable_plot = True
            self.oscGraph.setVisible(True)
            self.receiverGraph.setVisible(True)

            self.graphBox.addWidget(self.oscGraph)
            self.graphBox.addWidget(self.receiverGraph)
            print('enabled graph')
        else:
            self.oscGraph.setVisible(False)
            self.receiverGraph.setVisible(False)
            self.graphBox.removeWidget(self.oscGraph)
            self.graphBox.removeWidget(self.receiverGraph)
            print('disabled graph')

        #enable writing of temperature log to file
    def log_data(self):
        self.write_to_file = 0
        if self.chk_enableDataLog.isChecked():
            self.write_to_file = 1
            print('writing data to log file')
        else:
            print('data logging ended')

    def UpdateArray(self, array, limitx, new_value):
        if len(array) != int(limitx): #if limitx value gets changed, change size of array
            array = numpy.zeros(limitx)
            #print('array size adjusted for plotting')
        else:
            pass
        array[:int(limitx-1)]=array[1:]
        array[int(limitx-1)]=new_value
        return array
