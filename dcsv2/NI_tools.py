# -*- coding: utf-8 -*-
"""
NI_tools

@author: hnb3
"""


################################################################
## Load libraries
################################################################
import PyDAQmx
import ctypes


################################################################
## generateNIDevicesDicts
## 
## This function generates a list of devices based on the serial
## number. It also provides dictionaries allowing to get the
## device name and device type from a serial number.
##
################################################################
def generateNIDevicesDicts(allowed_serial_numbers = None):

    # Get device names
    MSG_LENGTH = 1024
    msg = (ctypes.c_char * MSG_LENGTH)()
    PyDAQmx.DAQmxGetSystemInfoAttribute(PyDAQmx.DAQmx_Sys_DevNames, ctypes.byref(msg), MSG_LENGTH)
    
    # Init output list and dicts
    list_of_devices = msg.value.split(", ")
    list_of_serials = []
    device_name_by_serial = {}
    device_type_by_serial = {}
    
    for i in range(len(list_of_devices)):
        # For all devices
    
        # Get the serial number
        MSG_LENGTH = 4
        msg = (ctypes.c_char * MSG_LENGTH)()
        PyDAQmx.DAQmxGetDeviceAttribute(ctypes.create_string_buffer(list_of_devices[i]), PyDAQmx.DAQmx_Dev_SerialNum, ctypes.byref(msg), MSG_LENGTH)
        sn = ''.join(['%02X' % ord(x) for x in reversed(msg)])

        if allowed_serial_numbers is not None:
            if sn not in allowed_serial_numbers:    
                continue
        
        # Add name to dictionary, using serial number as key
        device_name_by_serial[sn] = list_of_devices[i]
        
        # Get the product type
        MSG_LENGTH = 1024
        msg = (ctypes.c_char * MSG_LENGTH)()
        PyDAQmx.DAQmxGetDeviceAttribute(ctypes.create_string_buffer(list_of_devices[i]), PyDAQmx.DAQmx_Dev_ProductType, ctypes.byref(msg), MSG_LENGTH)
        # Add type to dictionary, using serial number as key
        device_type_by_serial[sn] = msg.value
        
        # Add yo serial number list
        list_of_serials.append(sn)
        
    return (list_of_serials, device_name_by_serial, device_type_by_serial)

