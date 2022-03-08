import numpy as np
import serial

datalength = 29


class Counter:
    def __init__(self, COM):
        self.COM = COM
        self.ser = serial.Serial()
        self.ser.port = self.COM
        self.ser.baudrate = 9600
        self.select_high_freq_channel()

    def select_high_freq_channel(self):
        # initialization from Scott Egbert
        # Power up select CH2 frequency mode (the high speed chacxnnel)
        self.open()
        self.ser.write(b"$E2222*")
        self.close()

    def readonce(self, size):
        self.open()
        read = self.ser.read(size)
        self.close()
        return read

    def open(self):
        self.ser.open()

    def close(self):
        self.ser.close()


c = Counter('COM18')
print(c.readonce(29))
