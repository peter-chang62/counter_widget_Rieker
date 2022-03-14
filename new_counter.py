import time
import matplotlib.pyplot as plt
import numpy as np
import serial
import clipboard_and_style_sheet
import counter.hpcounters as HPC

datalength = 25


class Counter:
    def __init__(self, COM):
        # initialize the Serial instance
        self.ser = serial.Serial()

        # set the serial's communication port
        self.COM = COM

        # the baudrate should already be 9600, but just so you know
        self.ser.baudrate = 9600

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

    def select_low_freq_channel(self):
        # initialization from Scott Egbert
        # Power up select CH2 frequency mode (the high speed channel)
        self.open()
        self.ser.write(b"$E2020*")
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


# %% test 1
# c1 = Counter('COM16')
# c2 = Counter('COM18')
#
# c1.select_high_freq_channel()
# c2.select_high_freq_channel()
# c1.readonce(100)
# c2.readonce(100)
# time.sleep(1)
#
# c1.ser.open()
# c2.ser.open()
#
# npts = 100
# Data1 = np.zeros(npts)
# Data2 = np.zeros(npts)
# for i in range(npts):
#     data1 = c1.ser.read(25)
#     data2 = c2.ser.read(29)
#
#     data1 = data1[:-5]
#     data2 = data2[7:-2]
#
#     Data1[i] = float(data1)
#     Data2[i] = float(data2)
#     print(i, data1, data2)
#
# plt.figure()
# plt.plot(Data1, '.-', label='black counter')
# plt.plot(Data2, '.-', label='green counter')
# # plt.plot(Data1 - Data2 + np.mean(Data1), '.-', label='diff')
# plt.legend(loc='best')

# window = np.ones(10)
# conv1 = np.convolve(Data1, window, mode='valid') / np.sum(window)
# conv2 = np.convolve(Data2, window, mode='valid') / np.sum(window)
# plt.figure()
# plt.plot(conv1, '.-', label='fa-5 counter')
# plt.plot(conv2, '.-', label='fa-2 counter')
# plt.plot(conv1 - conv2 + np.mean(conv1), '.-', label='diff')
# plt.legend(loc='best')

# %% test2
# npts = 100
# Data1 = np.zeros(npts)
# Data2 = np.zeros(npts)
# counter = Counter('COM18')
# 
# # initially open
# counter.open()
# for i in range(npts):
#     # select low frequency channel
#     counter.ser.write(b"$E2020*")
# 
#     # close and open
#     counter.close()
#     counter.open()
# 
#     # read
#     dat = str(counter.ser.read(100))
# 
#     # select high frequency
#     counter.ser.write(b"$E2222*")
# 
#     # close and open
#     counter.close()
#     counter.open()
# 
#     dat = float((dat.split('F-CH1:')[1]).split('\\r')[0])
#     Data1[i] = dat
# 
#     # read
#     dat = str(counter.ser.read(100))
#     dat = float((dat.split('F-CH2:')[1]).split('\\r')[0])
#     Data2[i] = dat
# 
#     print(i)

# %% test2 for green counter
# npts = 100
# Data_chin = np.zeros(npts)
# Data_hpc = np.zeros(npts)
# chin_cnt = Counter('COM18')
# hpc = HPC.AgilentCounter()
#
# # initially open
# chin_cnt.open()
# # chin_cnt.ser.write(b"$E2020*")
# chin_cnt.ser.write(b"$E2222*")
# chin_cnt.ser.read(100)
# chin_cnt.close()
# chin_cnt.open()
#
# for i in range(npts):
#     # read
#     dat = str(chin_cnt.ser.read(29))
#     hpc.begin_freq_measure(1)
#     Data_hpc[i] = hpc.get_result()
#
#     # dat = float((dat.split('F-CH1:')[1]).split('\\r')[0])
#     dat = float((dat.split('F-CH2:')[1]).split('\\r')[0])
#     Data_chin[i] = dat
#
#     print(i, dat, Data_hpc[i])

# plt.figure()
# plt.plot(Data_hpc, label='hpc')
# plt.plot(Data_chin, label='chin')
# plt.legend(loc='best')


# %% test2 for black counter
# npts = 100
# Data_chin = np.zeros(npts)
# Data_hpc = np.zeros(npts)
# chin_cnt = Counter('COM16')
# hpc = HPC.AgilentCounter()
#
# # initially open
# chin_cnt.open()
# # chin_cnt.ser.write(b"$E2020*")
# chin_cnt.ser.write(b"$E2222*")
# time.sleep(1)
# chin_cnt.ser.read(100)
# chin_cnt.close()
# chin_cnt.open()
# time.sleep(1)
#
# for i in range(npts):
#     # read
#     dat = str(chin_cnt.ser.read(25))
#     hpc.begin_freq_measure(1)
#     Data_hpc[i] = hpc.get_result()
#
#     dat = float(dat.split("b'")[1].split(',\\r')[0])
#     Data_chin[i] = dat
#
#     print(i, dat, Data_hpc[i])
#
# plt.figure()
# plt.plot(Data_hpc, label='hpc')
# plt.plot(Data_chin, label='chin')
# plt.legend(loc='best')

# %% all at one time
npts = 100
Data_hpc1 = np.zeros(npts)
Data_hpc2 = np.zeros(npts)
Data_black = np.zeros(npts)
Data_green = np.zeros(npts)

hpc = HPC.AgilentCounter()
green = Counter('COM18')
# black = Counter('COM16')

green.select_low_freq_channel()
# black.select_low_freq_channel()
green.readonce(100)
# black.readonce(100)
time.sleep(1)

green.open()
# black.open()
for i in range(npts):
    hpc.begin_freq_measure(1)
    dat_hpc1 = hpc.get_result()
    # dat_black = str(black.ser.read(25))
    dat_green = str(green.ser.read(29))
    hpc.begin_freq_measure(2)
    dat_hpc2 = hpc.get_result()

    # dat_black = float(dat_black.split("b'")[1].split(',\\r')[0])
    dat_green = float((dat_green.split('F-CH1:')[1]).split('\\r')[0])
    
    Data_hpc1[i] = dat_hpc1
    Data_hpc2[i] = dat_hpc2
    Data_green[i] = dat_green
    # Data_black[i] = dat_black

    print(i, dat_hpc1, dat_green, dat_hpc2)

plt.figure()
