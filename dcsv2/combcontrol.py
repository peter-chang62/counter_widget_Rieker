from packfind import find_package; find_package('pld')

from PyQt4 import QtGui, QtCore
from pumplaser import PumpLaser
from pld.arduinoplotwidget import ArduinoPlotWidget
from pld import arduino

import numpy as np

TEMP_MIN = 0.8
TEMP_MAX = 1.4
TEMP_STRIKES = 4

def find_run_lengths(bool_array):
    np.diff(np.where(np.concatenate(([bool_array[0]],
                                     bool_array[:-1] != bool_array[1:],
                                     [True])))[0])[::2]

class DualCombControlWidget(QtGui.QWidget):

    def __init__(self, arduino_port, parent=None):
        ard = arduino.Arduino(arduino_port)

        # Digital pins to enable/disable things
        # Comb 1 temp/45 is purple
        # Comb 2 temp/44 is brown
        comb_dict = {'Comb 1':{'osc':49,'famp':51,'bamp':53,'temp':45},
                    'Comb 2':{'osc':48,'famp':50,'bamp':52,'temp':44}}
        # Analog pins to monitor things
        temp_dict = {1:'Laser 1 Temp',
                     3:'Laser 2 Temp',
                     5:'Laser 3 Temp',
                     7:'Laser 4 Temp',
                     9:'Laser 5 Temp',
                     11:'Laser 6 Temp'}

        super(DualCombControlWidget, self).__init__(parent)
        layout = QtGui.QVBoxLayout(self)

        l_safety = QtGui.QHBoxLayout()
        layout.addLayout(l_safety)
        self.push_clear_fault = QtGui.QPushButton('Clear Fault', self)
        self.push_clear_fault.setEnabled(False)
        self.push_clear_fault.clicked.connect(self.clear_fault)
        l_safety.addWidget(self.push_clear_fault)
        check_enable_fault_check = QtGui.QCheckBox('Enable Fault Checking', self)
        l_safety.addWidget(check_enable_fault_check)
        check_enable_fault_check.setChecked(True)
        check_enable_fault_check.clicked.connect(self.set_fault_check_enabled)

        self.ard = ard
        self.combs = []
        self.widget_combs = QtGui.QWidget(self)
        layout.addWidget(self.widget_combs)
        layout_combs = QtGui.QHBoxLayout(self.widget_combs)
        for comb_name in comb_dict:
            comb_widget = CombLaserControlWidget(ard, comb_dict[comb_name], comb_name, self)
            self.combs.append(comb_widget)
            layout_combs.addWidget(comb_widget)

        self.ardpw = ArduinoPlotWidget(ard, temp_dict)
        for channel in temp_dict:
            self.ardpw.add_channel(channel)
        layout.addWidget(self.ardpw)

        self.timer_safety = QtCore.QTimer(self)
        self.timer_safety.setInterval(3000)
        self.timer_safety.timeout.connect(self.check_lasers)
        if check_enable_fault_check.isChecked:
            self.timer_safety.start()

    def set_fault_check_enabled(self, is_enabled):
        if is_enabled:
            self.timer_safety.start()
            print('Enabling fault checking')
        else:
            self.timer_safety.stop()
            print('Disabling fault checking')

    def check_lasers(self):
        for channel in self.ardpw.channels_active:
            _, data_array, _, name = self.ardpw.channel_items[channel]
            array = data_array.get_array()
            if np.any(find_run_lengths(array < TEMP_MIN) > TEMP_STRIKES):
                print('%s temp below limit %0.2f' % (name, TEMP_MIN))
            elif np.any(find_run_lengths(array > TEMP_MAX) > TEMP_STRIKES):
                print('%s temp above limit %0.2f' % (name, TEMP_MAX))
            else:
                continue
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            for comb in self.combs:
                comb.is_osc_enabled = False
            self.timer_safety.stop()
            self.widget_combs.setEnabled(False)
            self.push_clear_fault.setEnabled(True)
            return

    def clear_fault(self):
        for channel in self.ardpw.channels_active:
            time_array, data_array, _, _ = self.ardpw.channel_items[channel]
            time_array.clear_array()
            data_array.clear_array()
        self.timer_safety.start()
        self.widget_combs.setEnabled(True)
        self.push_clear_fault.setEnabled(False)

    def temp_set_enable(self, index, state):
        self.combs[index].temp_set_enable(state)

    def panic(self, index):
        self.combs[index].panic()

    def closeEvent(self, event):
        print('GUI exit; cleaning up')
        self.timer_safety.stop()
        self.ardpw.preclose()
        for comb in self.combs:
            comb.preclose()
        self.ard.close()
        event.accept()

class CombLaserControlWidget(QtGui.QGroupBox):

    def __init__(self, ard, comb_dict, name='', parent=None):
        super(CombLaserControlWidget, self).__init__(name, parent)
        self.ard = ard
        self.setup_gui()

        osc_pin, famp_pin, bamp_pin, self.temp_pin = \
            comb_dict['osc'], comb_dict['famp'], comb_dict['bamp'], comb_dict['temp']
        self.osc = PumpLaser(ard, osc_pin, name='Oscillator ' + name)
        famp = PumpLaser(ard, famp_pin, name='Front Amp ' + name)
        bamp = PumpLaser(ard, bamp_pin, name='Back Amp ' + name)
        self.amps = [famp, bamp]
        self.amp_locks = [self.check_ampFront, self.check_ampBack]

        self.push_oscillator.clicked.connect(lambda checked: setattr(self,'is_osc_enabled',checked))
        self.push_ampBoth.clicked.connect(lambda checked: setattr(self,'is_amp_enabled',checked))
        self.amp_locks[0].clicked.connect(lambda checked: self.laser_lock(self.amps[0], not checked))
        self.amp_locks[1].clicked.connect(lambda checked: self.laser_lock(self.amps[1], not checked))

        self.is_osc_enabled = False

    def setup_gui(self):

        self.push_oscillator = QtGui.QPushButton('Oscillator Pump', self)
        self.push_oscillator.setMaximumWidth(100)
        self.push_oscillator.setCheckable(True)
        self.push_ampBoth = QtGui.QPushButton('Amplifiers', self)
        self.push_ampBoth.setMaximumWidth(100)
        self.push_ampBoth.setCheckable(True)
        self.check_ampFront = QtGui.QCheckBox('Front Amp', self)
        self.check_ampFront.setChecked(True)
        self.check_ampBack = QtGui.QCheckBox('Back Amp', self)
        self.check_ampBack.setChecked(True)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.push_oscillator)
        layout.addWidget(self.push_ampBoth)
        layout.addWidget(self.check_ampFront)
        layout.addWidget(self.check_ampBack)

    @property
    def is_osc_enabled(self):
        return self.osc.is_enabled
    @is_osc_enabled.setter
    def is_osc_enabled(self,boolean):
        self.osc.is_enabled = boolean
        if not self.is_osc_enabled:
            self.is_amp_enabled = False
        self.push_oscillator.setChecked(self.is_osc_enabled)
        self.push_ampBoth.setEnabled(self.is_osc_enabled)
        self.check_ampFront.setEnabled(self.is_osc_enabled)
        self.check_ampBack.setEnabled(self.is_osc_enabled)

    @property
    def is_amp_enabled(self):
        return self._is_amp_enabled
    @is_amp_enabled.setter
    def is_amp_enabled(self,boolean):
        self._is_amp_enabled = boolean
        self.push_ampBoth.setChecked(boolean)
        for amp in self.amps:
            amp.is_enabled = boolean

    def laser_lock(self,laser,should_lock):
        laser.is_locked = should_lock
        if self.is_amp_enabled and not laser.is_locked:
            laser.is_enabled = True

    def temp_set_enable(self, should_enable):
        self.ard.digital_write(self.temp_pin, should_enable)

    def panic(self):
        self.temp_set_enable(False)
        self.is_amp_enabled = False

    def preclose(self):
        self.is_osc_enabled = False

    def closeEvent(self, event):
        print('GUI exit; cleaning up')
        self.preclose()
        event.accept()

    def __del__(self):
        try:
            self.is_osc_enabled = False
        except:
            pass

def main():
    arduino_port = 'COM5'

    app = QtGui.QApplication([])
    form = DualCombControlWidget(arduino_port)
    form.show(); form.setWindowTitle('Dual Pump Laser Monitor')
    app.exec_()

if __name__ == '__main__':
    main()
