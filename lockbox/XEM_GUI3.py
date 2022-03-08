"""
XEM6010 Phase-lock box main GUI script,
by JD Deschenes, Octobe
r 2013"""

import sys
from PyQt4 import QtGui, Qt, QtCore
import numpy as np

from win32gui import SetWindowPos
import win32con

import winsound

from SuperLaserLand_JD2 import SuperLaserLand_JD2
from XEM_GUI_MainWindow import XEM_GUI_MainWindow
#from FreqErrorWindow import FreqErrorWindow
from FreqErrorWindowWithTempControlV2 import FreqErrorWindowWithTempControlV2
#from DisplayPhaseResponseWindow import DisplayPhaseResponseWindow
from DisplayVNAWindow import DisplayVNAWindow
from initialConfiguration import initialConfiguration
from SLLSystemParameters import SLLSystemParameters
from SLLConfigurationWindow import SLLConfigurationWindow

from DisplayTransferFunctionWindow import DisplayTransferFunctionWindow
from DisplayDitherSettingsWindow import DisplayDitherSettingsWindow

from DisplayDividerAndResidualsStreamingSettingsWindow import DisplayDividerAndResidualsStreamingSettingsWindow
from DFr_timing_module_settings import DFr_timing_module_settings

import time

#import gc

import allowSetForegroundWindow # This is a workaround to make our window show on top on Windows 7:
#import os   # used by allowSetForegroundWindow()

def main():

    # Create the object that handles the communication with the FPGA board:
    sl = SuperLaserLand_JD2()




    #SERIAL NUMBER LIST
    #14370009MV = R1
    #14370009M9 = R2
    #14370009MW = N1
    #1540000CVG = N2
    #1540000CVI = P1
    #1540000CVH = P2
    #1729000IOV = 31
    #1729000INW = 32
    #1729000INP = 31.1
    #1729000IMR = 31.2
    #1540000CWG = 31.3

    # Specify the mapping between the serial numbers and their colors:
    serial_to_color_mapping = {}
    serial_to_color_mapping['14370009MW'] = '#CCFFFF'   # N1 comb
    serial_to_color_mapping['1540000CVG'] = '#FF0000'   # N2 comb
    serial_to_color_mapping['1540000CVI'] = '#CCFFFF'   # P1 comb
    serial_to_color_mapping['1540000CVH'] = '#FF0000'   # P2 comb
    serial_to_color_mapping['14370009MV'] = '#CCFFFF'   # R1 comb
    serial_to_color_mapping['14370009M9'] = '#FF0000'   # R2 comb
    serial_to_color_mapping['1729000IOV'] = '#CCFFFF'   # 31 comb
    serial_to_color_mapping['1729000INW'] = '#FF0000'   # 32 comb
    serial_to_color_mapping['1729000INP'] = '#CCFFFF'   # 31.1 comb
    serial_to_color_mapping['1729000IMR'] = '#CCFFFF'   # 31.2 comb
    serial_to_color_mapping['1540000CWG'] = '#CCFFFF'   # 31.3 comb

    # Specify the mapping between the serial numbers and their names:
    serial_to_name_mapping = {}
    serial_to_name_mapping['14370009MW'] = 'N1 Comb'
    serial_to_name_mapping['1540000CVG'] = 'N2 Comb'
    serial_to_name_mapping['1540000CVI'] = 'P1 Comb'
    serial_to_name_mapping['1540000CVH'] = 'P2 Comb'
    serial_to_name_mapping['14370009MV'] = 'R1 Comb'
    serial_to_name_mapping['14370009M9'] = 'R2 Comb'
    serial_to_name_mapping['1729000IOV'] = '31 Comb'
    serial_to_name_mapping['1729000INW'] = '32 Comb'
    serial_to_name_mapping['1729000INP'] = '31.1 Comb'

    serial_to_name_mapping['1729000IMR'] = '31.2 Comb'
    serial_to_name_mapping['1540000CWG'] = '31.3 Comb'


    # Add a shorthand for the name so we can add to the window name:
    serial_to_shorthand_mapping = {}
    serial_to_shorthand_mapping['14370009MW'] = 'N1 Comb'
    serial_to_shorthand_mapping['1540000CVG'] = 'N2 Comb'
    serial_to_shorthand_mapping['1540000CVI'] = 'P1 Comb'
    serial_to_shorthand_mapping['1540000CVH'] = 'P2 Comb'
    serial_to_shorthand_mapping['14370009MV'] = 'R1 Comb'
    serial_to_shorthand_mapping['14370009M9'] = 'R2 Comb'
    serial_to_shorthand_mapping['1729000IOV'] = '31 Comb'
    serial_to_shorthand_mapping['1729000INW'] = '32 Comb'
    serial_to_shorthand_mapping['1729000INP'] = '31.1 Comb'
    serial_to_shorthand_mapping['1729000IMR'] = '31.2 Comb'
    serial_to_shorthand_mapping['1540000CWG'] = '31.3 Comb'

    serial_to_config_file_mapping = {}

    serial_to_config_file_mapping['14370009MW'] = 'system_parameters_N1comb.xml'
    serial_to_config_file_mapping['1540000CVG'] = 'system_parameters_N2comb.xml'
    serial_to_config_file_mapping['1540000CVI'] = 'system_parameters_P1.xml'
    serial_to_config_file_mapping['1540000CVH'] = 'system_parameters_P2.xml'
    serial_to_config_file_mapping['14370009MV'] = 'system_parameters_R1.xml'
    serial_to_config_file_mapping['14370009M9'] = 'system_parameters_R2.xml'
    serial_to_config_file_mapping['1729000IOV'] = 'system_parameters_31.xml'
    serial_to_config_file_mapping['1729000INW'] = 'system_parameters_32.xml'
    serial_to_config_file_mapping['1729000INP'] = 'system_parameters_31.xml' # 31.1
    serial_to_config_file_mapping['1729000IMR'] = 'system_parameters_31.xml' # 31.2
    serial_to_config_file_mapping['1540000CWG'] = 'system_parameters_31.xml' # 31.3



    # Specify the mapping between the serial numbers and the ports that they have to connect to for the temperature control
    # Currentl 50001 is orange, 50002 is blue (hard-coded port numbers in the temperature control script)
    port_number_mapping = {}
    port_number_mapping['14370009MW'] = 60002   # N1 comb
    port_number_mapping['1540000CVG'] = 60003   # N2 comb
    port_number_mapping['1540000CVI'] = 60002   # P1 comb
    port_number_mapping['1540000CVH'] = 60003   # P2 comb
    port_number_mapping['14370009MV'] = 60002   # R1 comb
    port_number_mapping['14370009M9'] = 60003   # R2 comb
    port_number_mapping['1729000IOV'] = 60002   # 31 comb
    port_number_mapping['1729000INW'] = 60003   # 32 comb
    port_number_mapping['1729000INP'] = 60002   # 31.1 comb
    port_number_mapping['1729000IMR'] = 60002   # 31.2 comb
    port_number_mapping['1540000CWG'] = 60002   # 31.3 comb


    ###########################################################################
    # Start the User Interface
    allowSetForegroundWindow.allowSetForegroundWindow()

    # Start Qt:
    app = QtGui.QApplication(sys.argv)

    strList = sl.getDeviceList()
    initial_config = initialConfiguration(strList, serial_to_name_mapping, serial_to_color_mapping, 'superlaserland_v12.bit')


    # this will remove minimized status
    # and restore window with keeping maximized/normal state
    allowSetForegroundWindow.allowSetForegroundWindow()
#    initial_config.setWindowState(initial_config.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
    # this will activate the window
#    initial_config.activateWindow()
#    initial_config.show()
  #  initial_config.raise_()
  #  initial_config.show()

    SetWindowPos(initial_config.winId(),
                    win32con.HWND_TOPMOST, # = always on top. only reliable way to bring it to the front on windows
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
    SetWindowPos(initial_config.winId(),
                    win32con.HWND_NOTOPMOST, # disable the always on top, but leave window at its top position
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
    initial_config.raise_()
    initial_config.show()
    initial_config.activateWindow()

    #initial_config.setWindowState(initial_config.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
    # Run the event loop for this window
    app.exec_()
#    print('After app.exec_()()')


    if initial_config.bOk == False:
        # User clicked cancel. simply close the program:
        return
    print(initial_config.strFirmware)
    print(initial_config.strSelectedSerial)

#    # Fairly dirty hack: if we are using a firmware file which ends in "_highbw.bit", we set the high bandwidth flag to true
#    if initial_config.strFirmware.endswith('_highbw.bit'):
#        sl.bHighBandwidthFilter = True
#    else:
#        sl.bHighBandwidthFilter = False

    bUpdateFPGA = False
    if initial_config.bSendFirmware:

        bUpdateFPGA = True

    # Open the selected FPGA:
    error_code = sl.openDevice(initial_config.bSendFirmware, initial_config.strSelectedSerial, initial_config.strFirmware, bUpdateFPGA)
#    error_code = sl.openDevice(initial_config.bSendFirmware, initial_config.strSelectedSerial)
    if error_code != 0:
        print(initial_config.strFirmware)
        print(sl.convertErrorCodeToString(error_code))
        rep = QtGui.QMessageBox.warning(None, 'Error', sl.convertErrorCodeToString(error_code), QtGui.QMessageBox.Ok)
        return

    sl.optimize_AD9783_timing()
    ###########################################################################
    # Create the object which handles the configuration parameters (DAC offsets, DAC gains, beat frequency modulation range, etc):
    sp = SLLSystemParameters()
    # Send the values to the FPGA only if we have just re-programmed it. Otherwise we use whatever value is already in so we don't disturb the operation
    bTriggerEvents = False
    if initial_config.bSendFirmware:

        bTriggerEvents = True

    # Lookup filename and load if file is there:
    try:
        custom_config_file = serial_to_config_file_mapping[initial_config.strSelectedSerial]
        sp.loadFromFile(custom_config_file)
        print('Loaded configuration from %s' % custom_config_file)
    except KeyError:
        custom_config_file = ''

    # sp.saveToFile('system_parameters_current.xml')

    bSendToFPGA = bTriggerEvents
    sp.sendToFPGA(sl, bSendToFPGA)

    config_window = SLLConfigurationWindow()
    config_window.loadParameters(sp)
    config_window.hide()



    # # This is a hack to start the modelocok before we switch to external clock mode
    # set_dac_offset(self, dac_number, offset)
    # # Output offsets values:
    # output_offset_in_volts = float(self.sp.getValue('Output_offset_in_volts', strDAC))
    # # Scale this to the correct units for the output offset slider:
    # min_output_in_volts = float(self.sp.getValue('Output_limits_low', strDAC))
    # max_output_in_volts = float(self.sp.getValue('Output_limits_high', strDAC))
    # slider_units = (output_offset_in_volts - min_output_in_volts)/(max_output_in_volts-min_output_in_volts) * 1e6
    # print('calling dac offset slider setValue()')
    # self.q_dac_offset[k].blockSignals(True)
    # self.q_dac_offset[k].setValue(slider_units)
    # self.q_dac_offset[k].blockSignals(False)
    # print('done calling dac offset slider setValue()')

#    ###########################################################################
#    # Run a performance test on reading our wires from the FPGA:
#    N_reads = 1
#    start_time = time.clock()
#    sl.measureWireOutsPerformance(N_reads)
#    stop_time = time.clock()
#    print('Reading 1 WireOut: Elapsed time = %f sec\tThroughput = %f reads/sec' % (stop_time-start_time, N_reads/(stop_time-start_time)))
#
#    N_reads = 10
#    start_time = time.clock()
#    sl.measureWireOutsPerformance(N_reads)
#    stop_time = time.clock()
#    print('Reading 1 WireOut: Elapsed time = %f sec\tThroughput = %f reads/sec' % (stop_time-start_time, N_reads/(stop_time-start_time)))
#
#    N_reads = 100
#    start_time = time.clock()
#    sl.measureWireOutsPerformance(N_reads)
#    stop_time = time.clock()
#    print('Reading 1 WireOut: Elapsed time = %f sec\tThroughput = %f reads/sec' % (stop_time-start_time, N_reads/(stop_time-start_time)))
#
#    N_reads = 1000
#    start_time = time.clock()
#    sl.measureWireOutsPerformance(N_reads)
#    stop_time = time.clock()
#    print('Reading 1 WireOut: Elapsed time = %f sec\tThroughput = %f reads/sec' % (stop_time-start_time, N_reads/(stop_time-start_time)))
#



#    trigger_delay = 50
#    boxcar_filter_size = 5
#    rst_residuals_streaming = 1
#    sl.setResidualsStreamingSettings(trigger_delay, boxcar_filter_size, rst_residuals_streaming)
#    rst_residuals_streaming = 0
#    sl.setResidualsStreamingSettings(trigger_delay, boxcar_filter_size, rst_residuals_streaming)


    ############################
    # Set a test pattern on the ADC output:

#    sl.set_LTC2195_spi_register(address=0xA2, register_value=int('00000001', 2))    # default output current, internal termination off, digital outputs are enabled, test pattern OFF, 4-lane output mode
#    sl.set_LTC2195_spi_register(address=0xA2, register_value=int('00000101', 2))    # default output current, internal termination off, digital outputs are enabled, test pattern ON, 4-lane output mode
#    # set all zeros:
#    sl.set_LTC2195_spi_register(address=0xA3, register_value=0)
#    sl.set_LTC2195_spi_register(address=0xA4, register_value=1)


    ###########################################################################
    # Load all our windows:

    # Style sheet which includes the color scheme for each specific box:
    try:
        custom_style_sheet = ('#MainWindow {color: white; background-color: %s;}' % serial_to_color_mapping[initial_config.strSelectedSerial])
    except KeyError:
        custom_style_sheet = ''

    # The shorthand name which gets added to the window names:
    try:
        custom_shorthand = serial_to_shorthand_mapping[initial_config.strSelectedSerial]
    except KeyError:
        custom_shorthand = ''

    # Have to be careful with the modulus setting (double-check with a scope to make sure the output frequency is right)
    # I think the output frequency for the square wave mode is given by:
    # 200 MHz/(2*(modulus+1))
    # While for the pulsed mode (bPulses = 1), the frequency is:
    # 200 MHz/(modulus+1)
#    sl.set_clk_divider_settings(bOn=1, bPulses=0, modulus=67e3-1)
#    sl.set_clk_divider_settings(bOn=1, bPulses=0, modulus=67e3+1-1)
    divider_settings_window = DisplayDividerAndResidualsStreamingSettingsWindow(sl, clk_divider_modulus=67e3, bDividerOn=0, bPulses=0, custom_style_sheet=custom_style_sheet, custom_shorthand=custom_shorthand, bUpdateFPGA = bSendToFPGA)



    # Optical lock window
    xem_gui_mainwindow2 = XEM_GUI_MainWindow(sl, custom_shorthand + ': Optical lock', 1, (False, True, True), sp, custom_style_sheet, initial_config.strSelectedSerial)
    xem_gui_mainwindow2.initSL(bTriggerEvents)

    # CEO Lock window
    xem_gui_mainwindow = XEM_GUI_MainWindow(sl, custom_shorthand + ': CEO lock', 0, (True, False, False), sp, custom_style_sheet, initial_config.strSelectedSerial)
    xem_gui_mainwindow.initSL(bTriggerEvents)



    #########################################################
    # The dfr trigger settings, just for debugging:
#    fake_mode_number = 1e6
#    sl.set_dfr(fbeat1=25e6+10*fake_mode_number, fbeat2=25e6, fceo1=25e6, fceo2=25e6)
#    sl.set_dfr_modulus(mode_number=fake_mode_number)
    dfr_timing_gui = DFr_timing_module_settings(sl, custom_style_sheet, custom_shorthand=custom_shorthand)
#    set_dfr_modulus

    # The two frequency counter:
    strOfTime = time.strftime("%m_%d_%Y_%H_%M_%S_")

    try:
        temp_control_port = port_number_mapping[initial_config.strSelectedSerial]
    except:
        temp_control_port = 0


    strNameTemplate = 'data_logging\%s' % strOfTime
    strNameTemplate = '%s_%s_' % (strNameTemplate, initial_config.strSelectedSerial)
    freq_error_window1 = FreqErrorWindowWithTempControlV2(sl, 'CEO beat in-loop counter', 0, strNameTemplate, custom_style_sheet, 0, xem_gui_mainwindow)
    freq_error_window2 = FreqErrorWindowWithTempControlV2(sl, 'Optical beat in-loop counter', 1, strNameTemplate, custom_style_sheet, temp_control_port, None)

    counters_window = Qt.QWidget()
    counters_window.setObjectName('MainWindow')
    counters_window.setStyleSheet(custom_style_sheet)
    vbox = Qt.QVBoxLayout()
    vbox.addWidget(freq_error_window1)
    vbox.addWidget(freq_error_window2)
    counters_window.setLayout(vbox)
    counters_window.setWindowTitle(custom_shorthand + ': Frequency counters')
    #counters_window.setGeometry(993, 40, 800, 1010)
    #counters_window.setGeometry(0, 0, 750, 1000)
#    counters_window.resize(600, 1080-100+30)
    counters_window.move(QtGui.QDesktopWidget().availableGeometry().topLeft() + Qt.QPoint(985, 10))
    counters_window.show()

    # Dither windows, this code could be moved to another class/file to help with clutter:
    dither_widget0 = DisplayDitherSettingsWindow(sl, 0, modulation_frequency_in_hz='1.1e3', output_amplitude='4e-4', integration_time_in_seconds='0.1', bEnableDither=True, custom_style_sheet=custom_style_sheet)
    dither_widget1 = DisplayDitherSettingsWindow(sl, 1, modulation_frequency_in_hz='5e3',   output_amplitude='1e-3', integration_time_in_seconds='0.1', bEnableDither=True, custom_style_sheet=custom_style_sheet)
    dither_widget2 = DisplayDitherSettingsWindow(sl, 2, modulation_frequency_in_hz='100',   output_amplitude='1e-4', integration_time_in_seconds='0.1', bEnableDither=True, custom_style_sheet=custom_style_sheet)

    dither_window = Qt.QWidget()
    dither_window.setObjectName('MainWindow')
    dither_window.setStyleSheet(custom_style_sheet)
    vbox = Qt.QVBoxLayout()
    vbox.addWidget(dither_widget0)
    vbox.addWidget(dither_widget1)
    vbox.addWidget(dither_widget2)
    dither_window.setLayout(vbox)
    dither_window.setWindowTitle(custom_shorthand + ': Dither controls')
    dither_window.show()
#
#
#    ###########################################################################
#    # Create another log file which indicates which FPGA generated these logs:
#    # FreqErrorWindow() should have made sure that the data_logging folder exists:
#    strCurrentName = strNameTemplate + 'info.txt'
#    file_output_info = open(strCurrentName, 'w')
#    file_output_info.write('XEM_GUI3.py started on %s.\n' % strOfTime)
#    file_output_info.write('FPGA serial number = %s\n' % initial_config.strSelectedSerial)
#    try:
#        file_output_info.write('FPGA name = %s\n' % serial_to_name_mapping[initial_config.strSelectedSerial])
#    except KeyError:
#        file_output_info.write('FPGA name = \n')
#    try:
#        file_output_info.write('FPGA color = %s\n' % serial_to_color_mapping[initial_config.strSelectedSerial])
#    except KeyError:
#        file_output_info.write('FPGA color = \n')
#    file_output_info.close()

#    ###########################################################################
#    # For testing out the transfer function window:
#    frequency_axis = np.logspace(np.log10(10e3), np.log10(2e6), 10e3)
#    transfer_function = 1/(1 + 1j*frequency_axis/100e3)
#    window_number = 1
#    vertical_units = 'V/V'
#    tf_window1 = DisplayTransferFunctionWindow(frequency_axis, transfer_function, window_number, vertical_units)
#

#    # Regroup the two windows into a single one:
    main_windows = Qt.QWidget()
    main_windows.setObjectName('MainWindow')
    main_windows.setStyleSheet(custom_style_sheet)


    ###########################################################################
    # Select clock source
    # clock_source = 0: Internal clock at 100 MHz
    # clock_source = 1: External clock at 200 MHz on DIN[0]/CLKIN, divided by 2 internally for a system clock still at 100 MHz
    if initial_config.bSendFirmware:
        if initial_config.bExternalClock == True:
            clock_source = 1
            print('External clock mode')
        else:
            clock_source = 0
            print('Internal clock mode')
        sl.selectClockSource(clock_source)
        # Now we just need to reset the frontend to make sure we start everything in a nice state
        sl.resetFrontend()



    tabs = QtGui.QTabWidget()
    # xem_gui_mainwindow2.resize(600, 700)

    # xem_gui_mainwindow.setContentsMargins(0, 0, 0, 0)
    # xem_gui_mainwindow.layout().setContentsMargins(0, 0, 0, 0)
    # xem_gui_mainwindow2.setContentsMargins(0, 0, 0, 0)
    # xem_gui_mainwindow2.layout().setContentsMargins(0, 0, 0, 0)
    # counters_window.setContentsMargins(0, 0, 0, 0)
    # counters_window.layout().setContentsMargins(0, 0, 0, 0)
    # dither_window.setContentsMargins(0, 0, 0, 0)
    # dither_window.layout().setContentsMargins(0, 0, 0, 0)
    # dfr_timing_gui.setContentsMargins(0, 0, 0, 0)
    # dfr_timing_gui.layout().setContentsMargins(0, 0, 0, 0)
    # divider_settings_window.setContentsMargins(0, 0, 0, 0)
    # divider_settings_window.layout().setContentsMargins(0, 0, 0, 0)

    tabs.setMaximumSize(1920,1080-100+30)
    # main_windows.setMaximumSize(600,600)
    # xem_gui_mainwindow.setMaximumSize(600,600)
    # xem_gui_mainwindow2.setMaximumSize(600,600)
    # counters_window.setMaximumSize(600,600)
    # dither_window.setMaximumSize(600,600)
    # dfr_timing_gui.setMaximumSize(600,600)
    # divider_settings_window.setMaximumSize(600,600)
    tabs.addTab(xem_gui_mainwindow, "CEO Lock")
    tabs.addTab(xem_gui_mainwindow2, "Optical Lock")
    tabs.addTab(counters_window, "Counters")
    tabs.addTab(dither_window, "Dither")
    tabs.addTab(dfr_timing_gui, "DFr trigger generator")
    tabs.addTab(divider_settings_window, "Peripherals settings")
    # tabs.setGeometry(0, 0, 750, 1000)

    box = QtGui.QHBoxLayout()
    box.addWidget(tabs)
    main_windows.setLayout(box)
    main_windows.setWindowTitle(custom_shorthand)
    # main_windows.setContentsMargins(0, 0, 0, 0)
    # main_windows.layout().setContentsMargins(0, 0, 0, 0)

    # main_windows.setGeometry(0, 0, 750, 750)
    # main_windows.resize(600, 700)
    main_windows.move(QtGui.QDesktopWidget().availableGeometry().topLeft() + Qt.QPoint(985, 10))

    main_windows.show()

#    hbox = Qt.QHBoxLayout()
#    hbox.addWidget(xem_gui_mainwindow)
#    hbox.addWidget(xem_gui_mainwindow2)
#    main_windows.setLayout(hbox)
#    main_windows.setWindowTitle('Phase-lock controls')
##    main_windows.setGeometry(993, 40, 800, 1010)
##    main_windows.resize(600, 1080-100+30)
##    main_windows.move(QtGui.QDesktopWidget().availableGeometry().topLeft() + Qt.QPoint(985, 10))
#    main_windows.show()


    # Enter main event loop
    app.exec_()
#    del xem_gui_mainwindow
#    del sl


if __name__ == '__main__':
    main()

