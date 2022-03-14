import os, time, datetime, random, logging
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow
# from Qt.QtCompat import loadUi
import hpcounters, orionlasers
import AsyncSocketComms, socket
import numpy as np
from Window import Ui_MainWindow

# USETEMP = True
USETEMP = False

array = np.zeros((2, 200))
count = np.array([0, 0])


def read_text(edit_field):
    usr_in = edit_field.text()
    try:
        return float(usr_in)
    except ValueError:
        print('%s is not a valid input for "%s"' % (usr_in, edit_field.whatsThis()))
    return None


def setup_ui(uifile, base_instance=None):
    """Load a Qt Designer .ui file and returns an instance of the user interface
    Args:
        uifile (str): Absolute path to .ui file
        base_instance (QWidget): The widget into which UI widgets are loaded
    Returns:
        QWidget: the base instance
    """
    # from https://github.com/mottosso/Qt.py/blob/master/examples/loadUi/baseinstance1.py
    ui = loadUi(uifile)  # Qt.py mapped function
    if not base_instance:
        return ui
    else:
        for member in dir(ui):
            if not member.startswith('__') and \
                    member != 'staticMetaObject':
                setattr(base_instance, member, getattr(ui, member))
        return ui


# GUI Subclass
class CounterWidget(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # super(CounterWidget, self).__init__(parent)
        # self.base_instance = setup_ui('counter_widget.ui', self)
        self.setupUi(self)

        ##################################################################
        ### Set simData = True to test program w/o a counter hooked up ###
        ##################################################################
        self.simData = False
        self.channels = [1, 2]

        # Create indexed tuples of UI items that exist for each channel
        self.display_channels = (self.display_channel1, self.display_channel2)
        self.display_channelsErrors = (self.display_channel1Error, self.display_channel2Error)
        self.edit_freqTargets = (self.edit_f1Target, self.edit_f2Target)
        self.check_logChannels = (self.check_logChan1, self.check_logChan2)
        self.check_activateChannels = (self.check_actChan1, self.check_actChan2)
        self.check_refFeedbacks = (self.check_refFeedback1, self.check_refFeedback2)
        self.check_tempFeedbacks = (self.check_tempFeedback1, self.check_tempFeedback2)
        self.button_commitTempAdjustments = (self.button_commitTempAdjust1, self.button_commitTempAdjust2)
        self.edit_portNumbers = (self.edit_chan1Port, self.edit_chan2Port)

        # Connect buttons to functions
        self.button_close.clicked.connect(self.close_cleanup)
        self.button_beginLogging.clicked.connect(lambda: self.enable_all_logs(True))
        self.button_stopLogging.clicked.connect(lambda: self.enable_all_logs(False))
        self.button_resetLaser.clicked.connect(self.reset_laser)
        self.button_findLaser.clicked.connect(self.find_laser)
        self.button_nqReset.clicked.connect(self.reset_nq)
        self.edit_tempFeedbackPeriod.editingFinished.connect(self.adjust_parameters)
        self.edit_tempFeedbackThreshold.editingFinished.connect(self.adjust_parameters)
        self.edit_tempStepSize.editingFinished.connect(self.adjust_parameters)
        self.edit_laserFeedbackPeriod.editingFinished.connect(self.adjust_parameters)
        self.edit_laserFeedbackThreshold.editingFinished.connect(self.adjust_parameters)

        self.check_activateChannels[0].clicked.connect(self.enable_channels)
        self.check_activateChannels[1].clicked.connect(self.enable_channels)

        self.check_logChannels[0].clicked.connect(lambda: self.enable_frequency_logging(0))
        self.edit_freqTargets[0].editingFinished.connect(lambda: self.user_set_target(0))
        self.check_refFeedbacks[0].clicked.connect(lambda: self.enable_reference_feedback(0))
        self.check_tempFeedbacks[0].clicked.connect(lambda: self.enable_temperature_feedback(0))
        self.button_commitTempAdjustments[0].clicked.connect(lambda: self.commit_to_temp_adjustment(0))
        self.edit_portNumbers[0].editingFinished.connect(lambda: self.set_temperature_port(0))

        self.check_logChannels[1].clicked.connect(lambda: self.enable_frequency_logging(1))
        self.edit_freqTargets[1].editingFinished.connect(lambda: self.user_set_target(1))
        self.check_refFeedbacks[1].clicked.connect(lambda: self.enable_reference_feedback(1))
        self.check_tempFeedbacks[1].clicked.connect(lambda: self.enable_temperature_feedback(1))
        self.button_commitTempAdjustments[1].clicked.connect(lambda: self.commit_to_temp_adjustment(1))
        self.edit_portNumbers[1].editingFinished.connect(lambda: self.set_temperature_port(1))

        self.check_laserConnect.clicked.connect(self.connect_laser)
        self.check_enableLaserTemp.clicked.connect(lambda checked: self.edit_laserTemp.setEnabled(checked))
        self.edit_laserTemp.returnPressed.connect(self.set_laser_temp)

        ########## Turns out this doesn't work :( ##############################################################
        #        for index in range(len(self.channels)):
        #            print(index)
        #            self.check_activateChannels[index].clicked.connect(self.enable_channels)
        #            self.check_logChannels[index].clicked.connect(lambda: self.enable_frequency_logging(index))
        #            self.edit_freqTargets[index].editingFinished.connect(lambda: self.user_set_target(index))
        #            self.check_refFeedbacks[index].clicked.connect(lambda: self.enable_reference_feedback(index))
        #            self.check_tempFeedbacks[index].clicked.connect(lambda: self.enable_temperature_feedback(index))
        ########################################################################################################

        ##################################################################
        ########### SET COUNTER BEHAVIOR IN THIS SECTION #################

        # Name of the counter to be loaded
        # counterName = 'HEWLETT-PACKARD,53131A,0,3427' #????
        # counterName = 'HEWLETT-PACKARD,53131A,0,3536' #PDCS System

        # How often to log frequencies
        self.freq_log_period = .1  # s

        # How often to feedback to reference laser
        self.laser_feedback_period = 2  # s
        # Deviation from target frequency that triggers laser feedback
        self.laser_feedback_threshold = 5  # Hz
        # Max frequency deviation from target before laser feedback is canceled
        self.laser_allowed_frequency_detune = 120  # Hz
        # Number of consecutive times the frequency deviation can be bigger than max allowed before feedback is canceled
        self.laser_feedback_strike_limit = 3

        # How often to feedback to comb temperature
        self.temp_feedback_period = 10  # s
        # Temperature step size during temperature tuning
        self.temp_step = 0.08  # deg C
        # Deviation from target frequency that triggers temperature feedback
        self.temp_feedback_threshold = 100  # Hz
        # Max magnitude temperature adjustment that is allowed
        self.temp_max_allowed_adjust = 5  # deg C
        # IPC socket port numbers for [channel 1, channel 2] temperature feedback
        self.temp_port_numbers = [60002, 60003]

        # [min,max] frequencies that are allowed to be entered as targets
        self.acceptableFreqRange = [199000000, 204690000]  # Hz

        # Deliminator used in log file
        self.delim = ','
        # Log file header (set to '' for none)
        self.hdr_str = 'Time (s)' + self.delim + 'Frequency (Hz)'
        # String written on each line of log. First number is filled with time,
        # in seconds, from the log start; second number filled with frequency in Hz
        self.logfmt = '\n{:.2f}' + self.delim + '{}'
        # Datetime format used in logfile names, logging events, etc
        self.timefmt = '%Y-%m-%d_%H%M%S'

        # Make log directory
        cwd = os.getcwd()
        self.log_dir = cwd + '\\counterlogs\\'
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # Set up logger
        self.logger_name = 'counter'
        self.logger_level = logging.DEBUG
        fh = logging.FileHandler(
            '%s\\%s_counterlog.log' % (self.log_dir, datetime.datetime.now().strftime(self.timefmt)), 'w')
        sh = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s  %(message)s', self.timefmt)
        fh.setFormatter(formatter)
        sh.setFormatter(formatter)

        self.log = logging.getLogger(self.logger_name)
        self.log.setLevel(self.logger_level)
        self.log.handlers = [fh, sh]

        ##################################################################

        # Initialize variables
        num = len(self.channels)

        self.IPC_clients = [None] * num
        self.tempFeedbacks = [False] * num
        self.tempFeedbackStartDatetimes = [None] * num
        self.lastTempFeedbackTimes = [0] * num
        self.tempAdjustValues = [0] * num

        self.refLaserFeedbacks = [False] * len(self.channels)
        self.refFeedbackStrikes = [0] * len(self.channels)
        self.laser_connected = False
        self.lastRefFeedbackTime = 0

        self.logging_channel = [False] * num
        self.log_files = [None] * num
        self.last_log_time = [0] * num
        self.log_start_times = [0] * num

        self.index = 0
        self.channel_is_active = [True] * num
        self.startTime = time.clock()
        self.disp_format = '{:,.1f}'
        self.dispSmallFormat = '{:.1f}'
        self.edit_laserPort.setText('COM6')

        # Pick some random starting frequencies
        self.freqs = [199867900.421, 199868526.215]
        self.freqTargets = self.freqs[:]
        self.freqTargets = [199869965.598, 199870591.410]
        self.nqAverages = 0
        self.nq = 0
        self.calc_values()
        for index in range(len(self.channels)):
            self.update_display(index)
            self.edit_freqTargets[index].setText('{:.3f}'.format(self.freqTargets[index]))

        # Load counter
        if self.simData:
            self.gateTime = 0.1
        else:
            """initializes the counter, and takes the first measurement index tells it which channel to take the 
            measurement for, it toggles between the two since you have two frequency combs """

            self.counter = hpcounters.AgilentCounter(None, False, 0.1)
            self.counter.set_clock_external(True)
            self.counter.set_apporx_freq([1, 2], 199868311)
            self.gateTime = self.counter.get_gate_time()
            self.counter.begin_freq_measure(self.channels[self.index])

        # Set up timer to handle measurement events
        # Timer interval is set to couter gate time;
        # this is the fastest we can acquire measurements
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_handler)
        self.timer.start(round(1500 * self.gateTime))

        # Show the GUI
        self.populate_textboxes()
        self.show()

        # TODO delete this
        self.array = np.zeros((2, 200))
        self.count = np.array([0, 0])

    def timer_handler(self):

        thisTime = time.clock()

        # self.index is last channel that counter was set to measure
        index = self.index
        self.increment_index()
        # Now self.index is set to next channel to be measured

        # Get measurement result
        if self.simData:
            self.freqs[index] = self.freqs[index] + (random.random() - .5) * 20
        else:
            try:
                # Get result of last measurement
                self.freqs[index] = self.counter.get_result()

                # TODO delete this
                if self.count[index] < len(self.array[0]):
                    self.array[index][self.count[index]] = self.freqs[index]
                    print(self.count[index])
                    self.count[index] += 1


            except Exception as e:
                print(e)
                # This is likely a counter timeout; probably there is no signal
                # on self.channel[index], so stop trying to measure it

                self.log.warning('Read failed on channel ' + str(self.channels[index]))
                self.check_activateChannels[index].setChecked(False)
                self.enable_channels()
                return
            # Start new measurement for the incremented index
            self.counter.begin_freq_measure(self.channels[self.index])

        self.calc_values()

        # Update display
        self.update_display(index)

        # Log data
        if self.logging_channel[index]:
            if thisTime - self.last_log_time[index] > self.freq_log_period:
                # Time to log another point...
                self.log_files[index].write(
                    self.logfmt.format(thisTime - self.log_start_times[index], self.freqs[index]))
                self.log_files[index].flush()
                # If it has been too long since last log, set current time to last log
                # Otherwise just add log period to last log time to keep interval constant
                if thisTime - self.last_log_time[index] < self.freq_log_period * 2:
                    self.last_log_time[index] += self.freq_log_period
                else:
                    self.last_log_time[index] = thisTime

        # Feedback to reference laser
        if self.refLaserFeedbacks[index]:
            if thisTime - self.lastRefFeedbackTime > self.laser_feedback_period:
                dF = self.freqs[index] - self.freqTargets[index]

                if abs(dF) > self.laser_allowed_frequency_detune:
                    self.log.warning('Frequency difference from target (%.1f) greater than allowed (%.1f)' % (
                        dF, self.laser_allowed_frequency_detune))
                    self.refFeedbackStrikes[index] += 1
                    self.log.warning('Strike #%i (%i strikes allowed)' % (
                        self.refFeedbackStrikes[index], self.laser_feedback_strike_limit))
                    if self.refFeedbackStrikes[index] > self.laser_feedback_strike_limit:
                        # Frequency is too far off, turn off feedback
                        self.check_refFeedbacks[index].setChecked(False)
                        self.enable_reference_feedback(index)

                else:  # Rep rate has NOT drifted too far from target
                    self.refFeedbackStrikes[index] = 0
                    if abs(dF) > self.laser_feedback_threshold:
                        # Frequency has drifted far enough to feedback to laser
                        # Change laser temp tocorrect problem
                        try:
                            if USETEMP:
                                # Temp up, R down -> wl up, f down
                                # So if dF > 0 turn R down
                                if dF > 0:
                                    dT = -1  # Ohms
                                else:
                                    dT = 1  # Ohms
                                # dT changes thermister setpoint of laser in Ohms
                                # dT>0 raises rep rate; dT<0 drops rep rate
                                new_temp = self.reference_laser.change_t(dT)
                                self.log.info('Ref laser temp set to %i' % new_temp)
                                self.edit_laserTemp.setText(str(new_temp))
                            else:
                                # I up -> wl up, f down
                                # So if dF > 0 turn I up
                                if dF > 0:
                                    dI = 1  # 0.1 mA
                                else:
                                    dI = -1  # 0.1 mA
                                new_I = self.reference_laser.change_i(dI)
                                self.log.info('Ref laser current set to %i (0.1mA)' % new_I)

                        except Exception as e:
                            # Failed to set new laser temp; turn off feedback

                            self.log.warning('Failed to communicate with ref laser')
                            print(e)
                            self.check_refFeedbacks[index].setChecked(False)
                            self.enable_reference_feedback(index)
                        self.lastRefFeedbackTime = thisTime

        # Feedback to comb temperature
        if self.tempFeedbacks[index]:
            if thisTime - self.lastTempFeedbackTimes[index] > self.temp_feedback_period:
                dF = self.freqs[index] - self.freqTargets[index]
                if abs(dF) > self.temp_feedback_threshold:
                    try:
                        # Temp increase lowers rep rate, temp decrease raises it
                        if dF > 0:
                            feedbackSign = 1
                        else:
                            feedbackSign = -1
                        self.tempAdjustValues[index] += feedbackSign * self.temp_step

                        # Limit temperature feedback value
                        if abs(self.tempAdjustValues[index]) > self.temp_max_allowed_adjust:
                            self.tempAdjustValues[index] = feedbackSign * self.temp_max_allowed_adjust
                            self.log.warning('Channel %i temp adjust at limit (%.2f)' % (
                                self.channels[index], self.tempAdjustValues[index]))

                        self.IPC_clients[index].send_text('%f\n' % self.tempAdjustValues[index])
                        self.log.info('Channel %i temperature adjusted by %.2f' % (
                            self.channels[index], self.tempAdjustValues[index]))
                    except socket.error:
                        # Failed to send to the socket port; the server has
                        # been disconnected (happens if temp program closed).
                        # Stop feedback

                        self.log.warning('Unable to communicate with server at port %i' % self.temp_port_numbers[index])
                        self.check_tempFeedbacks[index].setChecked(False)
                        self.enable_temperature_feedback(index)
                    self.lastTempFeedbackTimes[index] = thisTime

    def calc_values(self):
        self.deltaF = abs(self.freqs[1] - self.freqs[0])
        self.nq = (self.nq * self.nqAverages + min(self.freqs) / self.deltaF) / (self.nqAverages + 1)
        self.nqAverages += 1

    def reset_nq(self):
        self.nq = 0
        self.nqAverages = 0

    def update_display(self, index):
        self.display_channels[index].display(self.disp_format.format(self.freqs[index]))
        self.display_channelsErrors[index].display(
            self.dispSmallFormat.format(self.freqs[index] - self.freqTargets[index]))
        self.display_dchannel.display(self.dispSmallFormat.format(self.deltaF))
        self.display_nq.display(self.dispSmallFormat.format(self.nq))
        self.display_nqAverages.display(self.nqAverages)

    def get_next_index(self, index=None):
        # Returns next index, looping back to zero when last index is passed
        if index is None:
            index = self.index
        if index == len(self.channels) - 1:
            return 0
        else:
            return index + 1

    def increment_index(self, n=0):
        # Moves self.index to the next index and loops back to 0 when last index is passed
        num = len(self.channels)
        if self.index == num - 1:
            self.index = 0
        else:
            self.index += 1
        if not self.channel_is_active[self.index]:
            n += 1
            if n >= num:
                return
            else:
                self.increment_index()

    def enable_channels(self):
        # Turns each channel on or off based on state of its GUI checkbox
        for index in range(len(self.channels)):
            if self.check_activateChannels[index].isChecked():
                # Enable channel measurement
                self.channel_is_active[index] = True
                self.index = index
            else:
                # Disable channel and all related feedback and logging
                self.channel_is_active[index] = False

                self.check_logChannels[index].setChecked(False)
                self.enable_frequency_logging(index)

                self.check_refFeedbacks[index].setChecked(False)
                self.enable_reference_feedback(index)

                self.check_tempFeedbacks[index].setChecked(False)
                self.enable_temperature_feedback(index)

        # If all channels are off then turn off the event timer
        if any(self.channel_is_active):
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()

    def enable_frequency_logging(self, index):
        channel = self.channels[index]
        try:
            self.log_files[index].close()
        except Exception:
            pass

        if self.check_logChannels[index].isChecked():
            self.logging_channel[index] = True
            startDateTime = datetime.datetime.now().strftime(self.timefmt)  # YYY-MM-DD_HHMMSS
            self.log_files[index] = open(self.log_dir + startDateTime + '_chan' + str(channel), 'w')
            self.log_files[index].write(self.hdr_str)
            self.log_start_times[index] = time.clock()
            self.last_log_time[index] = -9999
            self.log.warning('Channel %i logging started' % channel)
        else:
            if self.logging_channel[index]:
                self.log.warning('Channel %i logging stopped' % channel)
                self.logging_channel[index] = False

    def enable_all_logs(self, logEnable=True):
        for index in range(len(self.channels)):
            if self.channel_is_active[index]:
                self.check_logChannels[index].setChecked(logEnable)
                self.enable_frequency_logging(index)

    def user_set_target(self, index):
        try:
            userInput = float(self.edit_freqTargets[index].text())
            if userInput < self.acceptableFreqRange[0] or userInput > self.acceptableFreqRange[1]:
                raise UserWarning('Requested value (' + str(userInput) + ') is outside allowed range (' + str(
                    self.acceptableFreqRange[0]) + ' to ' + str(self.acceptableFreqRange[1]) + ')')
            self.freqTargets[index] = userInput
        except Exception as e:

            self.edit_freqTargets[index].setText('{:.3f}'.format(self.freqTargets[index]))
            print('')
            print('Invalid input:')
            print(e)
            print('')

    def enable_reference_feedback(self, index):
        if self.check_refFeedbacks[index].isChecked() and self.laser_connected:
            for ii in range(len(self.check_refFeedbacks)):
                if ii != index:
                    self.check_refFeedbacks[ii].setChecked(False)
                    self.refLaserFeedbacks[index] = False
            self.log.warning('Feedback to reference laser enabled on channel %i' % self.channels[index])
            self.refLaserFeedbacks[index] = True
            self.refFeedbackStartDatetime = datetime.datetime.now().strftime(self.timefmt)  # YYY-MM-DD_HHMMSS
            self.lastRefFeedbackTime = -9999
            self.refFeedbackStrikes[index] = 0
        else:
            self.log.warning('Feedback to reference laser disabled on channel %i' % self.channels[index])
            self.check_refFeedbacks[index].setChecked(False)
            self.refLaserFeedbacks = [False] * len(self.refLaserFeedbacks)

    def connect_laser(self):
        if self.check_laserConnect.isChecked():
            port = ''.join(str(self.edit_laserPort.text()).split())
            try:
                self.reference_laser = orionlasers.OrionLaser(port)
                self.laser_connected = True
                self.edit_laserTemp.setText(str(self.reference_laser.t_0))
            except Exception as e:
                self.check_laserConnect.setChecked(False)
                print(e)
                self.log.warning('Failed to connect ORION Laser on ' + port)
        else:
            for index in range(len(self.refLaserFeedbacks)):
                self.check_refFeedbacks[index].setChecked(False)
                self.enable_reference_feedback(index)
            self.reference_laser.close()
            self.laser_connected = False

    def find_laser(self):
        if self.check_laserConnect.isChecked():
            print('Laser currently connected!')
        else:
            laser_ports = orionlasers.find()
            if laser_ports:
                self.edit_laserPort.setText(laser_ports[0])
            else:
                print('Failed to find an available Orion Laser')

    def reset_laser(self):
        if self.laser_connected:
            for index in range(len(self.channels)):
                self.check_refFeedbacks[index].setChecked(False)
                self.enable_reference_feedback(index)
            self.reference_laser.set_to_default()
            self.edit_laserTemp.setText(str(self.reference_laser.t_0))

    def set_laser_temp(self):
        usr_in = read_text(self.edit_laserTemp)
        if usr_in is None:
            self.edit_laserTemp.setText(str(self.reference_laser.get_t()))
        else:
            self.reference_laser.set_t(int(usr_in))

    def set_temperature_port(self, index):
        try:
            self.temp_port_numbers[index] = int(self.edit_portNumbers[index].text())
        except Exception:

            print('Invalid input')
            self.populate_textboxes()

    def enable_temperature_feedback(self, index):
        if self.check_tempFeedbacks[index].isChecked():
            try:
                test = AsyncSocketComms.AsyncSocketClient(self.temp_port_numbers[index])
                self.IPC_clients[index] = test
                self.tempFeedbacks[index] = True
                self.tempFeedbackStartDatetimes[index] = datetime.datetime.now().strftime(
                    self.timefmt)  # YYY-MM-DD_HHMMSS
                self.lastTempFeedbackTimes[index] = -9999
                self.log.warning(
                    'Socket connection on port  %i successful; begin temp feedback' % self.temp_port_numbers[index])
            except socket.error:

                self.log.warning(
                    'No server detected at port %i; cannot start temp feedback' % self.temp_port_numbers[index])
                self.check_tempFeedbacks[index].setChecked(False)
        else:
            self.log.warning('Temperature feedback on channel %i disabled' % self.channels[index])
            self.tempFeedbacks[index] = False

    def commit_to_temp_adjustment(self, index):
        if self.tempFeedbacks[index]:
            try:
                self.IPC_clients[index].send_text('COMMITADJUST\n')
                self.log.warning('Channel %i temperature adjust value (%.2f) added to set point' % (
                    self.channels[index], self.tempAdjustValues[index]))
            except socket.error:
                # Failed to send to the socket port; the server has
                # been disconnected (happens if temp program closed).
                # Stop feedback

                self.log.warning('Unable to communicate with server at port %i' % self.temp_port_numbers[index])
        self.check_tempFeedbacks[index].setChecked(False)
        self.enable_temperature_feedback(index)
        self.tempAdjustValues[index] = 0

    def adjust_parameters(self):
        try:
            self.temp_feedback_period = float(self.edit_tempFeedbackPeriod.text())
            self.temp_feedback_threshold = float(self.edit_tempFeedbackThreshold.text())
            self.temp_step = float(self.edit_tempStepSize.text())
            self.laser_feedback_period = float(self.edit_laserFeedbackPeriod.text())
            self.laser_feedback_threshold = float(self.edit_laserFeedbackThreshold.text())
        except ValueError:

            print('Invalid input')
            self.populate_textboxes()

    def populate_textboxes(self):
        for index in range(len(self.channels)):
            self.edit_portNumbers[index].setText('{:}'.format(self.temp_port_numbers[index]))
        self.edit_tempFeedbackPeriod.setText('{:.0f}'.format(self.temp_feedback_period))
        self.edit_tempFeedbackThreshold.setText('{:.0f}'.format(self.temp_feedback_threshold))
        self.edit_tempStepSize.setText('{:.2f}'.format(self.temp_step))
        self.edit_laserFeedbackPeriod.setText('{:.0f}'.format(self.laser_feedback_period))
        self.edit_laserFeedbackThreshold.setText('{:.0f}'.format(self.laser_feedback_threshold))

    def close_cleanup(self):
        # Prints the number 2. Every time.
        print(1 + 1)

    def closeEvent(self, event):
        # QT method, cannot rename
        self.log.warning('GUI exit; cleaning up')
        self.enable_all_logs(False)

        self.timer.stop()

        if not self.simData:
            self.counter.close()

        event.accept()
        return


if __name__ == '__main__':
    # from counter_widget import CounterWidget
    from PyQt5.QtWidgets import QApplication
    import sys
    import allowSetForegroundWindow
    from win32gui import SetWindowPos
    import win32con

    app = QApplication(sys.argv)

    aw = CounterWidget()
    allowSetForegroundWindow.allowSetForegroundWindow()
    SetWindowPos(aw.winId(),
                 win32con.HWND_TOPMOST,  # = always on top. only reliable way to bring it to the front on windows
                 0, 0, 0, 0,
                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
    SetWindowPos(aw.winId(),
                 win32con.HWND_NOTOPMOST,  # disable the always on top, but leave window at its top position
                 0, 0, 0, 0,
                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)

    aw.raise_()
    aw.show()
    aw.setWindowTitle('Counter Display')
    app.exec_()
