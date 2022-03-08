"""
XEM6010 Phase-lock box GUI, Transfer function display window
by JD Deschenes, October 2013

"""

import sys
import time
from PyQt4 import QtGui, Qt
import PyQt4.Qwt5 as Qwt
import numpy as np
import math
from scipy.signal import lfilter
from scipy.signal import decimate
import copy

# For make_sure_path_exists()
import os
import errno

class DisplayTransferFunctionWindow(QtGui.QWidget):

        
    def __init__(self, frequency_axis, transfer_function, window_number, vertical_units):
        super(DisplayTransferFunctionWindow, self).__init__()

        self.vertical_units = copy.copy(vertical_units)
        self.frequency_axis = copy.copy(frequency_axis)
        self.transfer_function = copy.copy(transfer_function)
        self.window_number = window_number
        
        self.writeOutputFile()
        
        self.initUI()
#        self.initSL()
        
        self.updateGraph()


    def writeOutputFile(self):
        
        
        # Create the subdirectory if it doesn't exist:
        self.make_sure_path_exists('transfer_functions')

        # Open file for output
        self.strNameTemplate = time.strftime("transfer_functions\%m_%d_%Y_%H_%M_%S")
        strCurrentName1 = self.strNameTemplate + ('_no_%03d.txt' % (self.window_number))
        
        
        
        DAT = np.array([self.frequency_axis, np.real(self.transfer_function), np.imag(self.transfer_function)])
        with open(strCurrentName1, 'w') as f_handle:
            # Write header for the file:
            f_handle.write('Frequency [Hz]\tReal_part [%s]\tImag_part [%s]\n' % (self.vertical_units, self.vertical_units))
            # write actual data:
            np.savetxt(f_handle,np.column_stack(DAT), delimiter='\t')
        
#        f_handle = open(strCurrentName1, 'w')
#        np.savetxt(f_handle,np.column_stack(DAT))
#        f_handle.close()
            
        
    def initUI(self):

        # Add a first QwtPlot to the UI:
        self.qplt_mag = Qwt.QwtPlot()
        self.qplt_mag.setTitle('Magnitude response')
        self.qplt_mag.setCanvasBackground(Qt.Qt.white)
        self.qplt_mag.setAxisScaleEngine(Qwt.QwtPlot.xBottom, Qwt.QwtLog10ScaleEngine())
        
        plot_grid = Qwt.QwtPlotGrid()
        plot_grid.setMajPen(Qt.QPen(Qt.Qt.black, 0, Qt.Qt.DotLine))
        plot_grid.attach(self.qplt_mag)
        
        # Create the curve in the plot
        
    
        
        self.curve_mag = Qwt.QwtPlotCurve('qplt_freq')
        self.curve_mag.attach(self.qplt_mag)
        self.curve_mag.setPen(Qt.QPen(Qt.Qt.red))
        self.curve_mag.setSymbol(Qwt.QwtSymbol(Qwt.QwtSymbol.Ellipse,
                                    Qt.QBrush(Qt.Qt.red),
                                    Qt.QPen(Qt.Qt.red),
                                    Qt.QSize(3, 3)))
        self.curve_mag.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased);
        
        self.curve_mag_closedloop = Qwt.QwtPlotCurve('qplt_freq')
        self.curve_mag_closedloop.attach(self.qplt_mag)
        self.curve_mag_closedloop.setPen(Qt.QPen(Qt.Qt.black))
#        self.curve_mag_closedloop.setSymbol(Qwt.QwtSymbol(Qwt.QwtSymbol.Ellipse,
#                                    Qt.QBrush(Qt.Qt.black),
#                                    Qt.QPen(Qt.Qt.black),
#                                    Qt.QSize(3, 3)))
        self.curve_mag_closedloop.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased);    
        
        self.curve_mag_model = Qwt.QwtPlotCurve('qplt_freq')
        self.curve_mag_model.attach(self.qplt_mag)
        self.curve_mag_model.setPen(Qt.QPen(Qt.Qt.blue))
        self.curve_mag_model.setSymbol(Qwt.QwtSymbol(Qwt.QwtSymbol.Ellipse,
                                    Qt.QBrush(Qt.Qt.blue),
                                    Qt.QPen(Qt.Qt.blue),
                                    Qt.QSize(3, 3)))
        self.curve_mag_model.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased);
        


        
        # Add a second QwtPlot to the UI:
        
        self.qplt_phase = Qwt.QwtPlot()
        self.qplt_phase.setTitle('Phase response')
        self.qplt_phase.setCanvasBackground(Qt.Qt.white)
        self.qplt_phase.setAxisScaleEngine(Qwt.QwtPlot.xBottom, Qwt.QwtLog10ScaleEngine())
        
        plot_grid = Qwt.QwtPlotGrid()
        plot_grid.setMajPen(Qt.QPen(Qt.Qt.black, 0, Qt.Qt.DotLine))
        plot_grid.attach(self.qplt_phase)
        
        # Create the curve in the plot
        self.curve_phase = Qwt.QwtPlotCurve('qplt_freq')
        self.curve_phase.attach(self.qplt_phase)
        self.curve_phase.setPen(Qt.QPen(Qt.Qt.red))
        self.curve_phase.setSymbol(Qwt.QwtSymbol(Qwt.QwtSymbol.Ellipse,
                                    Qt.QBrush(Qt.Qt.red),
                                    Qt.QPen(Qt.Qt.red),
                                    Qt.QSize(3, 3)))
        self.curve_phase.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased);
        
        self.curve_phase_model = Qwt.QwtPlotCurve('qplt_freq')
        self.curve_phase_model.attach(self.qplt_phase)
        self.curve_phase_model.setPen(Qt.QPen(Qt.Qt.blue))
        self.curve_phase_model.setSymbol(Qwt.QwtSymbol(Qwt.QwtSymbol.Ellipse,
                                    Qt.QBrush(Qt.Qt.blue),
                                    Qt.QPen(Qt.Qt.blue),
                                    Qt.QSize(3, 3)))
        self.curve_phase_model.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased);
        
#        self.curve_phase_closedloop = Qwt.QwtPlotCurve('qplt_freq')
#        self.curve_phase_closedloop.attach(self.qplt_phase)
#        self.curve_phase_closedloop.setPen(Qt.QPen(Qt.Qt.black))
#        self.curve_phase_closedloop.setSymbol(Qwt.QwtSymbol(Qwt.QwtSymbol.Ellipse,
#                                    Qt.QBrush(Qt.Qt.black),
#                                    Qt.QPen(Qt.Qt.black),
#                                    Qt.QSize(3, 3)))
#        self.curve_phase_closedloop.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased);
        
        
        ######################################################################
        # Controls to adjust the model
        ######################################################################
        
        # Units select
        units_label = Qt.QLabel('Units:')
        self.qcombo_units = Qt.QComboBox()
        self.qcombo_units.addItems(['dB', 'Linear', 'real part', 'imag part'])
        self.qcombo_units.setCurrentIndex(0)
#        self.qcombo_units.changeEvent.connect(self.updateGraph)
        self.qcombo_units.currentIndexChanged.connect(self.updateGraph)
        
        self.qchk_DDCFilter = Qt.QCheckBox('DDC sinc filter')
        self.qchk_DDCFilter.clicked.connect(self.updateGraph)
        
        self.qradio_signp = Qt.QRadioButton('+ Sign')
        self.qradio_signp.setChecked(True)
        self.qradio_signn = Qt.QRadioButton('- Sign')
        button_group = Qt.QButtonGroup()
        button_group.addButton(self.qradio_signp)
        button_group.addButton(self.qradio_signn)
        
        self.qradio_signp.clicked.connect(self.updateGraph)
        self.qradio_signn.clicked.connect(self.updateGraph)
        
        # set the default DC gain to the value of the transfer function at the lowest frequency:
        
        self.qlabel_k = Qt.QLabel('DC Gain [dB]')
        self.qedit_k = Qt.QLineEdit(str(np.round(1000.*20.*np.log10(np.abs(self.transfer_function[0])))/1000.))
        self.qedit_k.setMaximumWidth(60)
        self.qedit_k.textChanged.connect(self.updateGraph)
        
        
        self.qlabel_f1 = Qt.QLabel('1st order poles')
        self.qedit_f1 = Qt.QLineEdit('20e3,600e3')
        self.qedit_f1.setMaximumWidth(120)
        self.qedit_f1.textChanged.connect(self.updateGraph)
        
        
        

        
        self.qlabel_f0 = Qt.QLabel('2nd order poles')
        self.qedit_f0 = Qt.QLineEdit('1.5e6')
        self.qedit_f0.setMaximumWidth(120)
        self.qedit_f0.textChanged.connect(self.updateGraph)
        
        self.qlabel_zeta = Qt.QLabel('zeta')
        self.qedit_zeta = Qt.QLineEdit('0.1')
        self.qedit_zeta.setMaximumWidth(120)
        self.qedit_zeta.textChanged.connect(self.updateGraph)
        
        self.qlabel_T = Qt.QLabel('Pure delay')
        self.qedit_T = Qt.QLineEdit('570e-9')
        self.qedit_T.setMaximumWidth(60)
        self.qedit_T.textChanged.connect(self.updateGraph)
        
        
        
        self.qchk_controller = Qt.QCheckBox('Closed-loop prediction')
        self.qchk_controller.clicked.connect(self.updateGraph)
        
        
        self.qlabel_pgain = Qt.QLabel('P gain [dB]')
        self.qedit_pgain = Qt.QLineEdit('-100')
        self.qedit_pgain.setMaximumWidth(60)
        self.qedit_pgain.textChanged.connect(self.updateGraph)
        
        self.qlabel_icorner = Qt.QLabel('I corner [Hz]')
        self.qedit_icorner = Qt.QLineEdit('0')
        self.qedit_icorner.setMaximumWidth(60)
        self.qedit_icorner.textChanged.connect(self.updateGraph)
        
        
        
        self.qedit_comment = Qt.QTextEdit('')
#        self.qedit_comment.setMaximumWidth(80)
        self.qedit_comment.textChanged.connect(self.updateGraph)



        # Put all the widgets into a grid layout
        grid = Qt.QGridLayout()
        

        grid.addWidget(units_label, 0, 0)
        grid.addWidget(self.qcombo_units, 0, 1)
        
        grid.addWidget(self.qradio_signp, 1, 0)
        grid.addWidget(self.qradio_signn, 1, 1)
        
        grid.addWidget(self.qlabel_k, 2, 0)
        grid.addWidget(self.qedit_k, 2, 1)
        grid.addWidget(self.qlabel_f1, 3, 0)
        grid.addWidget(self.qedit_f1, 3, 1)
        grid.addWidget(self.qlabel_f0, 4, 0)
        grid.addWidget(self.qedit_f0, 4, 1)

        grid.addWidget(self.qlabel_zeta, 5, 0)
        grid.addWidget(self.qedit_zeta, 5, 1)
        
        grid.addWidget(self.qlabel_T, 6, 0)
        grid.addWidget(self.qedit_T, 6, 1)
        
        grid.addWidget(self.qchk_controller, 7, 0, 1, 2)        
        
        grid.addWidget(self.qlabel_pgain, 8, 0)
        grid.addWidget(self.qedit_pgain, 8, 1)
        
        grid.addWidget(self.qlabel_icorner, 9, 0)
        grid.addWidget(self.qedit_icorner, 9, 1)
        grid.addWidget(self.qchk_DDCFilter, 10, 0, 1, 2)
        
        grid.addWidget(self.qedit_comment, 11, 0, 1, 2)
        grid.setRowStretch(11, 0)
#        grid.addWidget(Qt.QLabel(''), 12, 0, 1, 2)
#        grid.setRowStretch(14, 1)

        vbox = Qt.QVBoxLayout()
        vbox.addWidget(self.qplt_mag)
        vbox.addWidget(self.qplt_phase)
        
        
        hbox = Qt.QHBoxLayout()
        hbox.addLayout(grid)
        hbox.addLayout(vbox, 1)
#        hbox.setStretch(2, 1)
        
        self.setLayout(hbox)

        # Adjust the size and position of the window
        # self.resize(800, 500)
        self.center()
        self.setWindowTitle('Transfer function #%d' % self.window_number)    
        self.show()
        
    def center(self):
        
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
#        print()
#        5435sdfsf
        qr.moveCenter(cp)
        self.move(QtGui.QDesktopWidget().availableGeometry().topLeft() + Qt.QPoint(800+100, 50))
        
    def timerEvent(self, e):
        
#        print('timerEvent, timerID = %d' % self.timerID)
        self.displayFreqCounter()
        
        return
        
    def updateGraph(self):
        
        if self.qcombo_units.currentIndex() == 0:
            bGraphIndBs = True
        else:
            bGraphIndBs = False
            
        if bGraphIndBs == True:
            self.curve_mag.setData(self.frequency_axis, 20*np.log10(np.abs(self.transfer_function)))
            self.qplt_mag.setAxisTitle(Qwt.QwtPlot.yLeft, 'dB[(%s)^2]' % self.vertical_units)
        else:
            if self.qcombo_units.currentIndex() == 2:
                # Linear real part
                self.curve_mag.setData(self.frequency_axis, (np.real(self.transfer_function)))
                self.qplt_mag.setAxisTitle(Qwt.QwtPlot.yLeft, '%s' % self.vertical_units)
            elif self.qcombo_units.currentIndex() == 3:
                # Linear imag part
                self.curve_mag.setData(self.frequency_axis, (np.imag(self.transfer_function)))
                self.qplt_mag.setAxisTitle(Qwt.QwtPlot.yLeft, '%s' % self.vertical_units)
            else:
                # linear magnitude and phase
                self.curve_mag.setData(self.frequency_axis, (np.abs(self.transfer_function)))
                self.qplt_mag.setAxisTitle(Qwt.QwtPlot.yLeft, '%s' % self.vertical_units)
        
        # Generate controller TF:
        try:
            Kc_in_dB = float(self.qedit_pgain.text())
        except:
            Kc_in_dB = 0

        try:
            Ic_in_Hz = float(self.qedit_icorner.text())
        except:
            Ic_in_Hz = 0
        
        
        # Generate model TF:
        # System sign:
        if self.qradio_signp.isChecked():
            sign = 1
        else:
            sign = -1
            

            
            
            
        self.curve_phase.setData(self.frequency_axis, np.angle(sign*(self.transfer_function)))

        # System model:

        f = self.frequency_axis
        fs = 100e6
        N_filter = 5
        # System model:
#        H = 1 * (10**(K/20) )/(1 + 1j*f/f1) * 1/(1 + 1j*f/f2) * np.exp(-1j*2*np.pi*f*T)
#        H = H* 1/((1j*2*np.pi*f/(2*np.pi*f0))**2 + 2*1j*zeta/(2*np.pi*f0)*2*np.pi*f + 1)

        
        # start with a flat transfer function:
        H = 0.*f + 1.   
        
        # DC Gain:
        try:
            K = float(self.qedit_k.text())
            H = H * (10**(K/20))
        except:
            K = 0
            
        # First order poles:
        f1_list = self.qedit_f1.text().split(',')
        for k in range(len(f1_list)):
            try:
                f1 = float(f1_list[k])
                H = H * 1/(1 + 1j*f/f1)
            except:
                H = H
        
        # Second order poles:
        f0_list = self.qedit_f0.text().split(',')
        zeta_list = self.qedit_zeta.text().split(',')
        if len(f0_list) == len(zeta_list):
            for k in range(len(f0_list)):
                try:
                    f0 = float(f0_list[k])
                    zeta = float(zeta_list[k])
                    H = H * 1/((1j*2*np.pi*f/(2*np.pi*f0))**2 + 2*1j*zeta/(2*np.pi*f0)*2*np.pi*f + 1)
                except:
                    H = H
        

        # Additional delay:
        try:
            T = float(self.qedit_T.text())
            H = H * np.exp(-1j*2*np.pi*f*T)
        except:
            H = H
            
        if self.qchk_DDCFilter.isChecked():
            H = H * np.sin(np.pi*N_filter*f/fs)  / np.sin(np.pi*f/fs) / N_filter
            
            
        # Controler model:
        Hc = 10**(Kc_in_dB/20) + Ic_in_Hz/(1j*f) / (10**(K/20) )
        # Generate closed-loop prediction:
        G_closed_loop = sign * self.transfer_function / (1 + sign * self.transfer_function * Hc)
            
        if bGraphIndBs == True:
            self.curve_mag_model.setData(self.frequency_axis, 20*np.log10(np.abs(H)))
        else:
            if self.qcombo_units.currentIndex() == 2:
                # Linear real part
                self.curve_mag_model.setData(self.frequency_axis, (np.real(H)))
            elif self.qcombo_units.currentIndex() == 3:
                # Linear imag part
                self.curve_mag_model.setData(self.frequency_axis, (np.imag(H)))
            else:
                # linear magnitude and phase
                self.curve_mag_model.setData(self.frequency_axis, (np.abs(H)))
                
#            self.curve_mag_model.setData(self.frequency_axis, (np.abs(H)))
            
        self.curve_phase_model.setData(self.frequency_axis, np.angle(H))
        
        
        if self.qchk_controller.isChecked():
#            self.curve_mag_closedloop.setCurveType(Qwt.QwtPlotCurve.Lines)
            if bGraphIndBs == True:
                self.curve_mag_closedloop.setData(self.frequency_axis, 20*np.log10(np.abs(G_closed_loop)))
            else:
                self.curve_mag_closedloop.setData(self.frequency_axis, (np.abs(G_closed_loop)))
        else:
#            self.curve_mag_closedloop.setCurveStyle(Qwt.QwtPlotCurve.NoCurve)
            # We essentially want to disable the black curve so we put it under the blue one
            # (I haven't found how to cleanly disable a trace from a graph!)
            if bGraphIndBs == True:
                self.curve_mag_closedloop.setData(self.frequency_axis, 20*np.log10(np.abs(H)))
            else:
                if self.qcombo_units.currentIndex() == 2:
                    # Linear real part
                    self.curve_mag_closedloop.setData(self.frequency_axis, (np.real(H)))
                elif self.qcombo_units.currentIndex() == 3:
                    # Linear imag part
                    self.curve_mag_closedloop.setData(self.frequency_axis, (np.imag(H)))
                else:
                    # linear magnitude and phase
                    self.curve_mag_closedloop.setData(self.frequency_axis, (np.abs(H)))
            
        
#        self.curve_phase_closedloop.setData(self.frequency_axis, np.angle(G_closed_loop))
        
        self.qplt_mag.replot()
            
        self.qplt_phase.replot()
        
    # From: http://stackoverflow.com/questions/273192/create-directory-if-it-doesnt-exist-for-file-write
    def make_sure_path_exists(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
                
