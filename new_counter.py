import time
import matplotlib.pyplot as plt
import numpy as np
import serial
import clipboard_and_style_sheet

datalength = 25


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


c1 = Counter('COM16')
c1.readonce(100)

c2 = Counter('COM18')
c2.readonce(100)

time.sleep(1)
c1.ser.open()
c2.ser.open()

npts = 200
Data1 = np.zeros(npts)
Data2 = np.zeros(npts)
for i in range(npts):
    data = c1.ser.read(25)
    data = data[:-5]
    print(data)
    Data1[i] = float(data)

    data = c2.ser.read(29)
    data = data[7:-2]
    print(data)
    Data2[i] = float(data)

    print(i)

plt.figure()
plt.plot(Data1, '.-', label='fa-5 counter')
plt.plot(Data2, '.-', label='fa-2 counter')
plt.plot(Data1 - Data2 + np.mean(Data1), '.-', label='diff')
plt.legend(loc='best')

window = np.ones(10)
conv1 = np.convolve(Data1, window, mode='valid') / np.sum(window)
conv2 = np.convolve(Data2, window, mode='valid') / np.sum(window)
plt.figure()
plt.plot(conv1, '.-', label='fa-5 counter')
plt.plot(conv2, '.-', label='fa-2 counter')
plt.plot(conv1 - conv2 + np.mean(conv1), '.-', label='diff')
plt.legend(loc='best')
