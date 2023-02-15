# %% package imports
import pyvisa as visa
import sys, math

# %% global variables
COUNTER_ID_PREFIX = "HEWLETT-PACKARD,53132A,0,"
DEFAULT_GATE_TIME = 0.1


# %% agilent counter
#######HP Agilent Counter Class##########
class AgilentCounter:
    def __init__(
        self,
        counter_id=None,
        use_external_clock=False,
        gate_time=DEFAULT_GATE_TIME,
        name=None,
    ):

        # Shoulde be 'GPIB0::3::INSTR'

        print("")
        if counter_id is None:
            print("Attempting to connect any HP 53131A counter")
        else:
            print("Attempting to connect counter " + counter_id)

        self.rm = visa.ResourceManager()
        GPIB_list = self.rm.list_resources("GPIB?*INSTR")

        print(
            "Found "
            + str(len(GPIB_list))
            + " GPIB device(s), searching for counter...\n"
        )

        found_counter = False
        for resource_name in GPIB_list:  # Likely will be 'GPIB0::3::INSTR'
            try:
                self.counter = self.rm.open_resource(resource_name)
                devname = str(self.counter.query("*IDN?")).strip()
                if counter_id is None:
                    if devname.lower().startswith(COUNTER_ID_PREFIX.lower()):
                        found_counter = True
                        break
                else:
                    if devname.lower() == counter_id.lower():
                        found_counter = True
                        break
                self.counter.before_close()
                self.counter.close()
            except Exception as e:
                print("Failed to test device at " + resource_name)
                print(e)

        if not found_counter:
            if counter_id is None:
                error = "Failed to find an Agilent Counter attached on GPIB."
            else:
                error = "Failed to find " + counter_id + " attached on GPIB."
            print(error)
            print("")
            raise UserWarning(error)

        print("Found counter at " + resource_name)

        self.gate_time = gate_time

        try:
            self.set_config_default()

        except Exception as e:
            print(e)
            error = "Discovered counter failed initial configuration."
            print(error)
            print("")
            #            try:
            #                self.close()
            #            except Exception:
            #                sys.exc_clear()
            self.counter.before_close()
            self.counter.close()
            self.rm.close()
            raise UserWarning(error)

        self.set_clock_external(use_external_clock)

        self.counter_id = devname

        self.resource_name = resource_name

        if name is None:
            self.name = (
                "HP Counter (" + str(self.counter_id) + ") at " + self.resource_name
            )
        else:
            self.name = name

        print(self.name + " was connected successfully.")
        print("")

    def set_config_default(self):

        # Based on "To Optimize Throughput"
        #   Agilent 53131A/132A Programming Guide, Page 142 (3-73)
        #   (53131_Prog.pdf)

        # Reset counter for setup
        self.counter.write("*RST")  # Reset the counter
        self.counter.write("*CLS")  # Clear event registers and error queue
        self.counter.write("*SRE 0")  # Clear service request enable register
        self.counter.write("*ESE 0")  # Clear event status enable register
        self.counter.write(
            ":STAT:PRES"
        )  
        # Preset enable registers and transition filters for operation and
        # questionable status structures.

        # Changes to optimize throughput
        self.counter.write(":FORMAT ASCII")  # ASCII format for fastest throughput
        self.counter.write(":EVENT1:LEVEL 0")  # Set Ch 1 trigger level to 0 volts
        self.counter.write(":EVENT2:LEVEL 0")  # Set Ch 2 trigger level to 0 volts

        ## These two lines enable the AUTO arming mode (fast, low precision)
        # self.counter.write(":FREQ:ARM:STAR:SOUR IMM")
        # self.counter.write(":FREQ:ARM:STOP:SOUR IMM")

        ## These three lines enable the DIGit arming mode. 
        # NOTE: Values over 9 lead to timeout errors with querry() or if read()
        # is performed to0 quickly after trigger. Must wait ~>0.75s for 9 digit
        # arm, ~>20 seconds for 10
        # self.counter.write(":FREQ:ARM:STAR:SOUR IMM")
        # self.counter.write(":FREQ:ARM:STOP:SOUR DIG")
        # self.counter.write(":FREQ:ARM:STOP:DIG 8")

        # These three lines enable using time arming, with a 0.1 second gate time
        self.counter.write(":FREQ:ARM:STAR:SOUR IMM")
        self.counter.write(":FREQ:ARM:STOP:SOUR TIM")
        self.counter.write(":FREQ:ARM:STOP:TIM " + str(self.gate_time))

        self.counter.write(
            ":DIAG:CAL:INT:AUTO OFF"
        )  
        # Disable automatic interpolater calibration. The most recent
        # calibration values are used in the calculation of frequency
        # self.counter.write("DIAGnostic:CALibration:INTerpolator:AUTO ONCE") 
        # Calibrates the interpolator circuit in the Counter when the ONCE
        # parameter is used.
        self.counter.write(
            ":DISP:ENAB OFF"
        )  # Turn off the counter display. This greatly increases measurement throughput.

        # Disable any post processing.
        self.counter.write(":CALC:MATH:STATE OFF")
        self.counter.write(":CALC2:LIM:STATE OFF")
        self.counter.write(":CALC3:AVER:STATE OFF")
        self.counter.write(":HCOPY:CONT OFF")  # Disable any printing operation
        self.counter.write(
            "*DDT #15FETC?"
        )  
        # Define the Trigger command. This means the command FETC? does not
        # need to be sent for every measurement, decreasing the number of bytes
        # transferred over the bus. Can use "READ?" command too.

        self.counter.write(":FUNC 'FREQ 2'")  # Select frequency mode and channel
        self.counter.write(":INIT:CONT ON")  # Put counter in Run mode

    def set_apporx_freq(self, channels=[1, 2], approx_freqs=None):
        results = []
        if type(channels) is not list:
            channels = [channels]

        if approx_freqs is None:
            for channel in channels:
                if channel == -1:
                    channel = 2
                self.begin_freq_measure(channel)
                measured_freq = self.get_result()
                self.counter.write(
                    ":FREQ:EXP" + str(int(channel)) + " " + str(measured_freq)
                )
                results.append(measured_freq)

        else:
            if type(approx_freqs) is not list:
                approx_freqs = [approx_freqs]

            if len(approx_freqs) < len(channels):
                approx_freqs = approx_freqs * int(
                    math.ceil(len(channels) / len(approx_freqs))
                )

            for channel, measured_freq in zip(channels, approx_freqs):
                if channel == -1:
                    channel = 2

                self.counter.write(
                    ":FREQ:EXP" + str(int(channel)) + " " + str(measured_freq)
                )
                results.append(measured_freq)

        return results

    def set_clock_external(self, use_external_clock=True):

        if use_external_clock:
            self.counter.write(":ROSC:SOUR EXT")
            self.counter.write(":ROSC:EXT:CHECK OFF")
        else:
            # Use internal oscillator. If you want to use an external timebase,
            # you must select it and turn off the automatic detection using:
            # ":ROSC:EXT:CHECK OFF"
            self.counter.write(":ROSC:SOUR INT")

    def set_gate_time(self, gate_time):
        self.gate_time = gate_time
        self.counter.write(":FREQ:ARM:STOP:TIM " + str(gate_time))

    def get_gate_time(self):
        return self.gate_time

    def get_all_freqs(self):
        self.begin_freq_measure(1)
        f1 = self.get_result()
        self.begin_freq_measure(2)
        return (f1, self.get_result())

    def begin_freq_measure(self, channel=1):
        if channel == 1:
            self.counter.write(":FUNC 'FREQ 1'")
            self.counter.assert_trigger()
        elif channel == 2 or channel == -1:
            self.counter.write(":FUNC 'FREQ 2'")
            self.counter.assert_trigger()
        else:
            raise UserWarning(str(channel) + " is not a valid channel number.")

    def get_result(self):
        return float(self.counter.read())

    def close(self):
        self.counter.write("*RST")  # Reset the counter
        self.counter.write("*CLS")  # Clear event registers and error queue
        self.counter.write("*SRE 0")  # Clear service request enable register
        self.counter.write("*ESE 0")  # Clear event status enable register
        self.counter.write(
            ":STAT:PRES"
        )  
        # Preset enable registers and transition filters for operation and
        # questionable status structures.
        self.counter.before_close()
        self.counter.close()
        self.rm.close()


# %% run
if __name__ == "__main__":
    c = AgilentCounter()
