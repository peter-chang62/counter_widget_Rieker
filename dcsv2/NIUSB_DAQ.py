# -*- coding: utf-8 -*-
"""
Created on Wed Aug 05 23:58:39 2015

@author: hnb3
"""

import PyDAQmx
import numpy as np

class NI_USB_Analog_In():
    def __init__(self, analog_in_devname, analog_in_channels):
        
        self.Navg = 128
        self.Nchan = len(analog_in_channels)
        
        catstr= '';
        for i in range(self.Nchan):
            catstr = catstr + '%s/%s,' % (analog_in_devname, analog_in_channels[i])
        self.channel_string = catstr[:-1]
        self.daqtask = None
        self.acq_started = False
        
    def start(self):
        
        self.daqtask = PyDAQmx.Task()
        self.daqtask.CreateAIVoltageChan(self.channel_string,"",PyDAQmx.DAQmx_Val_RSE,-10.0,10.0,PyDAQmx.DAQmx_Val_Volts,None)
        self.daqtask.StartTask()
        self.acq_started = True
        
    def read_values(self):
        if self.acq_started == True:
            values = list()
            read = PyDAQmx.int32()
            new_val = np.zeros((self.Nchan*self.Navg,),dtype=np.float64)
            self.daqtask.ReadAnalogF64(self.Navg,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,new_val,len(new_val),PyDAQmx.byref(read),None)
            for i in range(self.Nchan):
                in0 = float(np.mean(new_val[((i+0)*self.Navg):((i+1)*self.Navg)]))
                values.append(in0)
        else:
            values = [None]*self.Nchan
        return values
        
    def stop(self):
        
        self.daqtask.StopTask()
        self.daqtask.ClearTask()
        self.acq_started = False
        
class NI_USB_Analog_Out():
    def __init__(self, analog_out_devname, analog_out_channels):
        
        self.Navg = 128
        self.Nchan = len(analog_out_channels)
        
        catstr= '';
        for i in range(self.Nchan):
            catstr = catstr + '%s/%s,' % (analog_out_devname, analog_out_channels[i])
        self.channel_string = catstr[:-1]
        self.daqtask = None
        self.acq_started = False
    
    def start(self):
        
        self.daqtask = PyDAQmx.Task()
        self.daqtask.CreateAOVoltageChan(self.channel_string,"",0.0,5.0,PyDAQmx.DAQmx_Val_Volts,None) 
        self.daqtask.StartTask()
        self.acq_started = True
        
    def write_values(self, values):
        if self.acq_started == True:
            write = PyDAQmx.int32()
            input_val = np.array(values, dtype=np.float64)
            self.daqtask.WriteAnalogF64(1,True,10,PyDAQmx.DAQmx_Val_GroupByChannel,input_val,PyDAQmx.byref(write),None)
        
    def stop(self):
        
        self.daqtask.StopTask()
        self.daqtask.ClearTask()
        self.acq_started = False

class NI_USB_Digital_Out():
    def __init__(self, devname, ports, lines):
        
        self.devname = devname
        self.ports = ports
        self.lines = lines
        
    def write_value(self, index, value):
        
        channel_string = '%s/port%s/line%s' % (self.devname, self.ports[index], self.lines[index])
        
        val_array = np.array([0,0,0,0,0,0,0,0])
        val_array[7-int(self.lines[index])] = (value & 0x1)
        val_T = np.packbits(val_array)
        
        write = PyDAQmx.int32()
        tempdaqtask = PyDAQmx.Task() #initialize task
        tempdaqtask.CreateDOChan(channel_string,"",PyDAQmx.DAQmx_Val_ChanPerLine) 
        tempdaqtask.StartTask()      
        tempdaqtask.WriteDigitalU8(1,True,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,val_T,PyDAQmx.byref(write),None)        
        tempdaqtask.StopTask()
        tempdaqtask.ClearTask()
