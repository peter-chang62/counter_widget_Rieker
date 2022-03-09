import numpy as np
import serial

datalength = 29


class Counter:
    def __init__(self, COM):
        # initialize the Serial instance
        self.ser = serial.Serial()

        # set the serial's communication port
        self.COM = COM

        # the baudrate should already be 9600, but just so you know
        self.ser.baudrate = 9600

        # select the high frequency channel
        self.select_high_freq_channel()

    @property
    def COM(self):
        return self.ser.port

    @COM.setter
    def COM(self, port):
        assert type(port) == str, f"the port must be a string, but got: {port}"
        assert port[:3] == 'COM', f"the port must start with 'COM' but got {port}"

        self.ser.port = port

    def select_high_freq_channel(self):
        # initialization from Scott Egbert
        # Power up select CH2 frequency mode (the high speed channel)
        self.open()
        self.ser.write(b"$E2222*")
        self.close()

    def readonce(self, size):
        self.open()
        read = self.ser.read(size)
        self.close()
        return read

    def writeonce(self, byt):
        self.open()
        self.ser.write(byt)
        self.close()

    def open(self):
        self.ser.open()

    def close(self):
        self.ser.close()


# com18 is green fa-2 counter
# com17 is the fa-5 counter

# fa-5 counter works
c = Counter('COM18')
print(c.readonce(datalength * 5))

# fa-2 doesn't work
c = Counter('COM17')
print(c.readonce(datalength * 5))
