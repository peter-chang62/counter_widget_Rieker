import time
import threading
import serial as serial
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtCore import QObject, pyqtSignal

# %%
ser = serial.Serial()
ser.baudrate = 9600
ser.port = 'COM5'


# %%
def read(ser, N):
    ser.open()
    _ = ser.read(N)
    print(_)
    ser.close()
    return float(str(_).split("CH2:")[1].split("\\r")[0])


List = []
while True:
    value = read(ser, 29)
    List.append(value)
    print(value)
