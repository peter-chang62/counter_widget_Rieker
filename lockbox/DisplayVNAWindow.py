"""
XEM6010 Phase-lock box GUI, VNA (Vector Network Analyzer) controls
by JD Deschenes, October 2013

"""

import time
from PyQt4 import QtGui, Qt
import PyQt4.Qwt5 as Qwt
import numpy as np


from SuperLaserLand_JD2 import SuperLaserLand_JD2
from DisplayTransferFunctionWindow import DisplayTransferFunctionWindow


class DisplayVNAWindow(QtGui.QWidget):
    number_of_windows = 0   # Number of results windows we have opened
    response_windows = {}   # Dictionary which contains references to each results window
    
    bStop = False   # This is set when the user presses the stop button, and is checked by the wait loop
        
    def __init__(self):
        super(DisplayVNAWindow, self).__init__()
        
        self.initUI()
        

            
        
    def runSytemIdentification(self):
    
        # Check if another function is currently using the DDR2 logger:
        if self.sl.bDDR2InUse:
            print('DDR2 logger in use, cannot run identification')
            return
        # Block access to the DDR2 Logger to any other function until we are done:
        self.sl.bDDR2InUse = True
        
        # Reset the bStop flag (which is set when the user presses the stop button)
        self.bStop = False
        # The dither will be stopped by sl.setup_system_identification()
        self.qbtn_dither.setChecked(False)
        
        # Reset the progress bar
        self.qprogress_ident.setValue(0)
        
        (input_select, output_select, first_modulation_frequency_in_hz, last_modulation_frequency_in_hz, number_of_frequencies, System_settling_time, output_amplitude) = self.readSystemIdentificationSettings()
        
        self.sl.setup_system_identification(input_select, output_select, first_modulation_frequency_in_hz, last_modulation_frequency_in_hz, number_of_frequencies, System_settling_time, output_amplitude)
        total_wait_time = self.sl.get_system_identification_wait_time()
        print('Waiting for %f sec...\n' % total_wait_time)
        
        # If the wait time is to be > 1 minute, then give the chance to the user to cancel the action
        if total_wait_time > 60:
            reply = QtGui.QMessageBox.question(self, 'Long operation',
                'Warning! The requested identification will take %.1f minute(s), are you sure you want to continue?' % (total_wait_time/60), QtGui.QMessageBox.Yes | 
                QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                self.sl.bDDR2InUse = False
                return
            
        
        self.sl.trigger_system_identification()
        
        
        ## Wait until the transfer function measurement is finished, while updating the progress bar:
        start_time = time.clock()
        if total_wait_time > 0.1:
            # Split the wait time in chunks, updating the progress bar every time
            # TODO.
            # Should implement the wait not as time.sleep(). but by recording the start time, and updating the display
            # while we wait, because sleep() will freeze the GUI. Not the best solution anyway but it shouldn't be that bad
            # especially if we havea nicely updated progress bar.
#            time.sleep(total_wait_time)
            qapp = QtGui.QApplication.instance()
            
            while (time.clock()-start_time < total_wait_time) and self.bStop == False:
                self.qprogress_ident.setValue(  100 * (time.clock()-start_time)/total_wait_time )
#                self.qprogress_ident.update()
                self.qprogress_ident.repaint()
                qapp.processEvents()
#                print('Updating')
                time.sleep(20e-3)
        else:
            # Wait time is low enough to just use sleep() without giving the impression that the GUI has crashed.
            time.sleep(total_wait_time)
        
        if self.bStop == True:
            # Operation was cancelled by user
            self.sl.bDDR2InUse = False
            self.bStop = False
            self.qprogress_ident.setValue(0)
            self.sl.setVNA_mode_register(0, 1, 0)
            return
            
        ## Read out the results from the FPGA:
        try:
            (transfer_function_complex, frequency_axis) = self.sl.read_VNA_samples_from_DDR2()
        except:
            self.sl.bDDR2InUse = False
            raise
            
        # Signal to other functions that they can use the DDR2 logger
        self.sl.bDDR2InUse = False
        
        ## Scale the transfer function to physical units:
        # Current units are (VNA input counts)/(VNA output counts)
        # TODO: I am not sure that the following conversion will work with DAC2, because there is an additional 2^4 factor inside the FPGA firmware along the VNA output path
        output_volts_per_counts = self.sl.convertDACCountsToVolts(self.qcombo_transfer_output.currentIndex(), 1)
        print('output_volts_per_counts = %s' % output_volts_per_counts)
        
        
        if self.qcombo_transfer_input.currentIndex() == 0 or self.qcombo_transfer_input.currentIndex() == 1:
            # Input units to the VNA were ADC counts.
            # Transfer function units should be scaled to Volts/Volts, or no units:
            volts_per_VNA_input_counts = self.sl.convertADCCountsToVolts(self.qcombo_transfer_input.currentIndex(), 1)
            print('volts_per_VNA_input_counts = %s' % volts_per_VNA_input_counts)
            physical_input_units_per_input_counts = volts_per_VNA_input_counts
            
            physical_units_name = 'V/V'
        
        elif self.qcombo_transfer_input.currentIndex() == 2 or self.qcombo_transfer_input.currentIndex() == 3:
            # Input units to the VNA were frequency counts
            # Huge dirty hack because convertDDCCountsToHz expects a numpy array and we only have a scalar to give it
            if self.qcombo_transfer_input.currentIndex() == 2:
                ddc_freq_sign = cmp(self.sl.ddc0_frequency_in_hz, 0) # we wanted to do sign() here but python has no sign function
            else:
                ddc_freq_sign = cmp(self.sl.ddc1_frequency_in_hz, 0) # we wanted to do sign() here but python has no sign function
            
            Hz_per_VNA_input_counts = -ddc_freq_sign * np.mean(self.sl.convertDDCCountsToHz(   np.array((1,))   ))
#            Hz_per_VNA_input_counts = self.sl.convertDDCCountsToHz(1)
            print('Hz_per_VNA_input_counts = %s' % Hz_per_VNA_input_counts)
            physical_input_units_per_input_counts = Hz_per_VNA_input_counts
            
            physical_units_name = 'Hz/V'
        
        print('physical_units_name = %s' % physical_units_name)
        # Scale the actual measured transfer function:
        transfer_function_complex = transfer_function_complex * physical_input_units_per_input_counts / output_volts_per_counts        
        
        ## Create a new window to show the transfer function
        self.response_windows[self.number_of_windows] = DisplayTransferFunctionWindow(frequency_axis, transfer_function_complex, self.number_of_windows, physical_units_name)
        self.number_of_windows = self.number_of_windows + 1
        

        self.qprogress_ident.setValue(0)
        

        
    def updateTransferFunctionDisplay(self):
        if hasattr(self, 'transfer_function_dictionary') == False:
            return
        # Get which curve we should be displaying:
        (input_select, output_select, first_modulation_frequency_in_hz, last_modulation_frequency_in_hz, number_of_frequencies, System_settling_time, output_amplitude) = self.readSystemIdentificationSettings()
        

        try:
            H_measured_openloop = -self.transfer_function_dictionary[ (input_select, output_select, 0) ]
            freq_axis_openloop = self.transfer_freq_axis_dictionary[ (input_select, output_select, 0) ]
        except:
            H_measured_openloop = np.array((1, 1))
            freq_axis_openloop = np.array((1, 1))
        try:
            H_measured_fll = -self.transfer_function_dictionary[ (input_select, output_select, 1) ]
            freq_axis_fll = self.transfer_freq_axis_dictionary[ (input_select, output_select, 1) ]
        except:
            H_measured_fll = np.array((1, 1))
            freq_axis_fll = np.array((1, 1))
        
        
        # Predicted closed-loop response:
        # Add the PLL loop filter's transfer function
        ###### TODO: Have the sl object return the loop filters' transfer function instead of re-deriving it everywhere.
        P_gain = 0
        I_gain = 0
        
        N_delay_p = 5 # TODO: put the correct values here
        N_delay_i = 6 # TODO: put the correct values here
        H_cumsum = 1/(1-np.exp(-1j*2*np.pi*freq_axis_openloop/self.sl.fs))
        phase_ramp = 2*np.pi * freq_axis_openloop/self.sl.fs

        H_controller = P_gain * np.exp(-1j*N_delay_p * phase_ramp) + I_gain * H_cumsum * np.exp(-1j*N_delay_i * phase_ramp)
        
        H_measured_openloop = H_measured_openloop * np.exp(1j*2*np.pi*3*freq_axis_openloop/self.sl.fs) # we cancel 3 samples delay because these come from the VNA itself
        H_measured_fll = H_measured_fll * np.exp(1j*2*np.pi*3*freq_axis_fll/self.sl.fs) # we cancel 3 samples delay because these come from the VNA itself
        H_predicted_fll = H_measured_openloop / (1 + H_measured_openloop * H_controller)
            
            
        if len(freq_axis_openloop) > 2:
            self.curve_openloop.setData(freq_axis_openloop, 20*np.log10(np.abs(H_measured_openloop * H_controller)))
            self.curve_openloop_closed.setData(freq_axis_openloop, 20*np.log10(np.abs(1 / (1 + H_measured_openloop * H_controller))))
            
        # Handle the units
        # magnitude is currently in linear a linear scale units/units.
        # The units choices for the graph are:
        # self.qcombo_transfer_units.addItems(['dBunits/units', 'Hz/fullscale', 'Hz/V'])
        if self.qcombo_transfer_units.currentIndex() == 0:
            # dB units/units
            if len(freq_axis_openloop) > 2:
                self.curve_transfer_openloop.setData(freq_axis_openloop, 20*np.log10(np.abs(H_measured_openloop)))
                self.curve_transfer_closedloop_predicted.setData(freq_axis_openloop, 20*np.log10(np.abs(H_predicted_fll)))
            if len(freq_axis_fll) > 2:
                self.curve_transfer_closedloop.setData(freq_axis_fll, 20*np.log10(np.abs(H_measured_fll)))
            
            self.qplt_transfer.setAxisScaleEngine(Qwt.QwtPlot.yLeft, Qwt.QwtLinearScaleEngine())
            self.qplt_transfer.setAxisTitle(Qwt.QwtPlot.yLeft, 'Gain [dBunits/units]')
            
        elif self.qcombo_transfer_units.currentIndex() == 1:
            # Hz/fullscale
            # 2**10 is the number of fractional bits on the phase, while 2**16 is the fullscale output range in counts
            conversion_factor = self.sl.fs / 2**10 * 2**16
            if len(freq_axis_openloop) > 2:
                self.curve_transfer_openloop.setData(freq_axis_openloop, conversion_factor*(np.abs(H_measured_openloop)))
                self.curve_transfer_closedloop_predicted.setData(freq_axis_openloop, conversion_factor*(np.abs(H_predicted_fll)))
            if len(freq_axis_fll) > 2:
                self.curve_transfer_closedloop.setData(freq_axis_fll, conversion_factor*(np.abs(H_measured_fll)))
            
#            if len(H_closedloop) > 2:
#                self.curve_transfer_gainwithcontroller.setData(freq_axis, np.abs(H_closedloop) * conversion_factor)
#            else:
#                self.curve_transfer_gainwithcontroller.setData(freq_axis, magnitude * conversion_factor)
            self.qplt_transfer.setAxisScaleEngine(Qwt.QwtPlot.yLeft, Qwt.QwtLog10ScaleEngine())
            self.qplt_transfer.setAxisTitle(Qwt.QwtPlot.yLeft, 'Gain [Hz/fullscale]')
            
        elif self.qcombo_transfer_units.currentIndex() == 2:
            # Hz/V, assumes 1V fullscale DAC output (which might be incorrect depending on which DAC and the output PGA gain setting)
            # 2**10 is the number of fractional bits on the phase, while 2**16 is the fullscale output range in counts
            # The 1 at the end represents 1V/fullscale
            conversion_factor = self.sl.fs / 2**10 * 2**16 * 1
            if len(freq_axis_openloop) > 2:
                self.curve_transfer_openloop.setData(freq_axis_openloop, conversion_factor*(np.abs(H_measured_openloop)))
                self.curve_transfer_closedloop_predicted.setData(freq_axis_openloop, conversion_factor*(np.abs(H_predicted_fll)))
            if len(freq_axis_fll) > 2:
                self.curve_transfer_closedloop.setData(freq_axis_fll, conversion_factor*(np.abs(H_measured_fll)))
#            if len(H_closedloop) > 2:
#                self.curve_transfer_gainwithcontroller.setData(freq_axis, np.abs(H_closedloop) * conversion_factor)
#            else:
#                self.curve_transfer_gainwithcontroller.setData(freq_axis, magnitude * conversion_factor)
            self.qplt_transfer.setAxisScaleEngine(Qwt.QwtPlot.yLeft, Qwt.QwtLog10ScaleEngine())
            self.qplt_transfer.setAxisTitle(Qwt.QwtPlot.yLeft, 'Gain [Hz/V]')
        
        # The phase is unaffected by the units, it is always in radians:
        self.curve_transfer_phase.setData(freq_axis_openloop, np.angle(H_measured_openloop))

        # Refresh the display:
        self.qplt_transfer.replot()
        self.qplt_openloop.replot()
            
        return
        
    def readSystemIdentificationSettings(self):
        # Input select
        try:
            input_select = self.qcombo_transfer_input.currentIndex()
        except:
            input_select = 2
            pass
        
        try:
            output_select = self.qcombo_transfer_output.currentIndex()
        except:
            output_select = 0
            pass
        
        try:
            System_settling_time = float(self.qedit_settling_time.text())
        except:
            System_settling_time = 1e-3
            pass
        
        try:
            first_modulation_frequency_in_hz = float(self.qedit_freq_start.text())
            last_modulation_frequency_in_hz = float(self.qedit_freq_end.text())
        except:
            first_modulation_frequency_in_hz = 10e3
            last_modulation_frequency_in_hz = 1e6
            pass
        
        try:
            number_of_frequencies = int(float(self.qedit_freq_number.text()))
        except:
            number_of_frequencies = 16
            pass
        
        try:
            output_amplitude = int(float(self.sl.DACs_limit_high[output_select] - self.sl.DACs_limit_low[output_select])*float(self.qedit_output_amplitude.text())/2)
            if output_select == 2:
                # The DAC2 has a particularity in that the VNA outputs only a 16-bit number, and it is multiplied by 4 to fit the 20-bit range of DAC2.
                output_amplitude = output_amplitude/4
        except:
            output_amplitude = 1
            pass
#        if output_amplitude == 0:
#            output_amplitude = 1
            
        return (input_select, output_select, first_modulation_frequency_in_hz, last_modulation_frequency_in_hz, number_of_frequencies, System_settling_time, output_amplitude)
        
        
    def readDitherSettings(self):

        # Output select
        # Amplitude
        # Frequency
        # Sine or square wave
        try:
            output_select = self.qcombo_dither_output.currentIndex()
        except:
            output_select = 0
            pass
        
        try:
            modulation_frequency_in_hz = float(self.qedit_dither_freq.text())
        except:
            modulation_frequency_in_hz = 1e3
            pass
        
        
        try:
            output_amplitude = int(float(self.sl.DACs_limit_high[output_select] - self.sl.DACs_limit_low[output_select])*float(self.qedit_dither_amplitude.text())/2)
            if output_select == 2:
                # The DAC2 has a particularity in that the VNA outputs only a 16-bit number, and it is multiplied by 4 to fit the 20-bit range of DAC2.
                output_amplitude = output_amplitude/4
        except:
            output_amplitude = 0
            pass
#        if output_amplitude == 0:
#            output_amplitude = 1
            
        try:
            if self.qradio_squarewave.isChecked():
                bSquareWave = 1
            else:
                bSquareWave = 0
        except:
            bSquareWave = 0
            pass
        
        try:
            if self.qbtn_dither.isChecked():
                bEnableDither = 1
            else:
                bEnableDither = 0
        except:
            bEnableDither = 0
            pass
        return (output_select, modulation_frequency_in_hz, output_amplitude, bSquareWave, bEnableDither)
        
    def stopClicked(self):
        self.bStop = True   # This signals the waiting loop to cancel the operation
        return
        
    def ditherClicked(self):
        # Check if dither is set, then call 
#        setVNA_mode_register(self, trigger_dither, stop_flag, bSquareWave):
        (output_select, modulation_frequency_in_hz, output_amplitude, bSquareWave, bEnableDither) = self.readDitherSettings()
        # This is only really to set the dither
        # we don't care about these values:
        input_select = 0
        number_of_frequencies = 8
        System_settling_time = 1e-3
        self.sl.setup_system_identification(input_select, output_select, modulation_frequency_in_hz, modulation_frequency_in_hz, number_of_frequencies, System_settling_time, output_amplitude)
        
        print('(output_select, modulation_frequency_in_hz, output_amplitude, bSquareWave, bEnableDither) = %d, %f, %f, %d, %d' % (output_select, modulation_frequency_in_hz, output_amplitude, bSquareWave, bEnableDither))
        
        trigger_dither = bEnableDither
        if bEnableDither == False:
            stop_flag = 1
        else:
            stop_flag = 0
        bSquareWave = bSquareWave
        self.sl.setVNA_mode_register(trigger_dither, stop_flag, bSquareWave)
        print('(trigger_dither, stop_flag, bSquareWave) = %d, %d, %d' % (trigger_dither, stop_flag, bSquareWave))
        return
    
    def initUI(self):

        # Create the widgets which control the system identification module:
        
        # Input select
        transfer_input_label = Qt.QLabel('Input:')
        self.qcombo_transfer_input = Qt.QComboBox()
        self.qcombo_transfer_input.addItems(['ADC 0', 'ADC 1', 'DDC 0', 'DDC 1'])
        self.qcombo_transfer_input.setCurrentIndex(2)
#        transfer_input_label.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
#        self.qcombo_transfer_input.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        
        # Output select
        transfer_output_label = Qt.QLabel('Output:')
        self.qcombo_transfer_output = Qt.QComboBox()
        self.qcombo_transfer_output.addItems(['DAC 0', 'DAC 1', 'DAC 2'])
        self.qcombo_transfer_output.setCurrentIndex(0)
#        transfer_output_label.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
#        self.qcombo_transfer_output.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        
        # 
        settling_time_label = Qt.QLabel('System settling time [s]:')
        self.qedit_settling_time = Qt.QLineEdit('1e-3')
        self.qedit_settling_time.setMaximumWidth(60)
#        settling_time_label.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
#        self.qedit_settling_time.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        
        freq_start_label = Qt.QLabel('Freq start [Hz]:')
        self.qedit_freq_start = Qt.QLineEdit('10e3')
        self.qedit_freq_start.setMaximumWidth(60)
#        freq_start_label.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
#        self.qedit_freq_start.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        
        freq_end_label = Qt.QLabel('Freq end [Hz]:')
        self.qedit_freq_end = Qt.QLineEdit('2e6')
        self.qedit_freq_end.setMaximumWidth(60)
#        self.qedit_freq_end.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        
        freq_number_label = Qt.QLabel('Number of freq:')
        self.qedit_freq_number = Qt.QLineEdit('160')
        self.qedit_freq_number.setMaximumWidth(60)
#        self.qedit_freq_number.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        
        amplitude_label = Qt.QLabel('Modulation amplitude [0-1]:')
        self.qedit_output_amplitude = Qt.QLineEdit('0.01')
        self.qedit_output_amplitude.setMaximumWidth(60)
#        self.qedit_output_amplitude.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        
        # Button which triggers the system identification
        self.qbtn_ident = QtGui.QPushButton('Run identification')
        self.qbtn_ident.clicked.connect(self.runSytemIdentification)
#        self.qbtn_ident.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        
        self.qbtn_stop_ident = QtGui.QPushButton('Stop identification')
        self.qbtn_stop_ident.clicked.connect(self.stopClicked)
        
        
        # Progress bar which indicates the progression of the identification
        self.qprogress_ident = Qt.QProgressBar()
        self.qprogress_ident.setTextVisible(False)
        self.qprogress_ident.setValue(0)
#        self.qprogress_ident.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        
        # Controls for the dither mode:        
        # Needs: output select, frequency, amplitude, Square/Sine select, dither on/off
        ######################################################################
        # Settings
        ######################################################################
        self.qgroupbox_dither = Qt.QGroupBox('Continuous output', self)
        
        
        self.dither_output_label = Qt.QLabel('Output:')
        self.qcombo_dither_output = Qt.QComboBox()
        self.qcombo_dither_output.addItems(['DAC 0', 'DAC 1', 'DAC 2'])
        self.qcombo_dither_output.setCurrentIndex(0)
        self.qcombo_dither_output.currentIndexChanged.connect(self.ditherClicked)
        
        # Modulation frequency:
        self.qedit_freq_label = Qt.QLabel('Frequency [Hz]:')
        self.qedit_dither_freq = Qt.QLineEdit('1e6')
        self.qedit_dither_freq.textChanged.connect(self.ditherClicked)
        self.qedit_dither_freq.setMaximumWidth(60)
        
        # Amplitude:
        self.qlabel_dither_amplitude = Qt.QLabel('Amplitude [0-1]:')
        self.qedit_dither_amplitude = Qt.QLineEdit('0.01')
        self.qedit_dither_amplitude.textChanged.connect(self.ditherClicked)
        self.qedit_dither_amplitude.setMaximumWidth(60)
        
        # Sine/Square wave
        self.qradio_sinewave = Qt.QRadioButton('Sine wave')
        self.qradio_squarewave = Qt.QRadioButton('Square wave')
        self.qsign_group = Qt.QButtonGroup(self)
        self.qsign_group.addButton(self.qradio_sinewave)
        self.qsign_group.addButton(self.qradio_squarewave)
        
        self.qradio_sinewave.setChecked(True)
        self.qradio_squarewave.setChecked(False)
        self.qradio_sinewave.clicked.connect(self.ditherClicked)
        self.qradio_squarewave.clicked.connect(self.ditherClicked)
        
        # On/Off button
        self.qbtn_dither = QtGui.QPushButton('Activate dither')
        self.qbtn_dither.clicked.connect(self.ditherClicked)
        self.qbtn_dither.setCheckable(True)
        
        
        # Put all the widgets into a grid layout
        grid = QtGui.QGridLayout()
        
        grid.addWidget(self.dither_output_label,            0, 0)
        grid.addWidget(self.qcombo_dither_output,           0, 1)
        grid.addWidget(self.qedit_freq_label,               1, 0)
        grid.addWidget(self.qedit_dither_freq,              1, 1)
        grid.addWidget(self.qlabel_dither_amplitude,        2, 0)
        grid.addWidget(self.qedit_dither_amplitude,         2, 1)
        grid.addWidget(self.qradio_sinewave,                3, 0)
        grid.addWidget(self.qradio_squarewave,              3, 1)
        
        grid.addWidget(self.qbtn_dither,                    4, 0, 1, 2)
        self.qgroupbox_dither.setLayout(grid)    
        
        # Spacer which takes up the rest of the space:
        spacerItem = QtGui.QSpacerItem(1, 1, QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Expanding)
        
        # Put all the widgets into a grid layout
        grid = QtGui.QGridLayout()
        
        grid.addWidget(transfer_input_label, 0, 0)
        grid.addWidget(self.qcombo_transfer_input, 0, 1)
        grid.addWidget(transfer_output_label, 1, 0)
        grid.addWidget(self.qcombo_transfer_output, 1, 1)
        grid.addWidget(settling_time_label, 2, 0)
        grid.addWidget(self.qedit_settling_time, 2, 1)
        grid.addWidget(freq_start_label, 3, 0)
        grid.addWidget(self.qedit_freq_start, 3, 1)
        grid.addWidget(freq_end_label, 4, 0)
        grid.addWidget(self.qedit_freq_end, 4, 1)
        grid.addWidget(freq_number_label, 5, 0)
        grid.addWidget(self.qedit_freq_number, 5, 1)
        grid.addWidget(amplitude_label, 6, 0)
        grid.addWidget(self.qedit_output_amplitude, 6, 1)
        grid.addWidget(self.qbtn_ident, 7, 0, 1, 2)
        grid.addWidget(self.qbtn_stop_ident, 8, 0, 1, 2)
        
        grid.addWidget(self.qprogress_ident, 9, 0, 1, 2)
        
        self.qgroupbox_vna = Qt.QGroupBox('Swept sine', self)
        self.qgroupbox_vna.setLayout(grid)
        
        vbox = Qt.QVBoxLayout()
        vbox.addWidget(self.qgroupbox_vna)
        vbox.addWidget(self.qgroupbox_dither)
        vbox.addItem(spacerItem)

        self.setLayout(vbox)
        

        # Adjust the size and position of the window
#        self.resize(800, 600)
        self.center()
        self.setWindowTitle('VNA control')    
        self.show()
        

        
    def center(self):
        
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
#        self.move(qr.topLeft())
        self.move(QtGui.QDesktopWidget().availableGeometry().topLeft() + Qt.QPoint(50, 50))
        

        
        
        