# -*- coding: utf-8 -*-
"""
Created on Wed Aug 05 16:31:20 2015

@author: hnb3

Created by Hugo Bergeron on August 5, 2015.

This is the main computation class. I took the code in the old NIUSB_DAQ class
that was about "computation", and used it as the base for this class.

This class' job is to convert voltages and temperature, set, verify & 
enforce limits, handle user setpoint, adjust values, etc. This class does no
DAQ operations at all. 
"""

################################################################################################################################
## Libraries
################################################################################################################################
import numpy as np

################################################################################################################################
## Control loop class
################################################################################################################################
class control_loop():
    def __init__(self, control_loop_configuration):
        
        # Copy configuration
        self.control_loop_configuration = control_loop_configuration        
        # Get name
        self.name = self.control_loop_configuration['name']
        # Get channel settings
        self.ni6009_actual_ch   = self.control_loop_configuration['ni6009_actual_ch']
        self.ni6009_setpoint_ch = self.control_loop_configuration['ni6009_setpoint_ch']
        self.ni9264_output_ch   = self.control_loop_configuration['ni9264_output_ch']
        self.ni6009_enable_port = self.control_loop_configuration['ni6009_enable_port']
        self.ni6009_enable_line = self.control_loop_configuration['ni6009_enable_line']
        self.enabled_is_high = bool(int(self.control_loop_configuration['enabled_is_high']))
        # Get Steinhart coefs
        temp = [float(x.strip()) for x in self.control_loop_configuration['steinhart_coefs'].split(',')]
        self.A = temp[0]
        self.B = temp[1]
        self.C = temp[2]
        # Get bias current
        self.Ibias = float(self.control_loop_configuration['bias_current'])
        # Get default setpoint and temperature limits
        self.temperature_default = float(self.control_loop_configuration['temperature_default'])  
        self.temperature_minimum = float(self.control_loop_configuration['temperature_minimum'])  
        self.temperature_maximum = float(self.control_loop_configuration['temperature_maximum'])
        # Get default enable state
        self.enabled_default = bool(int(self.control_loop_configuration['enabled_default']))
        
        # If applies, get port number
        if self.control_loop_configuration['outer_loop_port'] == '':
            self.port = None
        else:
            self.port = int(self.control_loop_configuration['outer_loop_port'])
        
        # Get filter taps (num[0]+num[1]z^-1+num[2]z^-2+...)/(den[0]+den[1]z^-1+den[2]z^-2+...)
        self.compensator_num = [float(x.strip()) for x in self.control_loop_configuration['compensator_num'].split(',')]
        self.compensator_den = [float(x.strip()) for x in self.control_loop_configuration['compensator_den'].split(',')]
        # Initialize filter
        self.filt_x = [self.temperature_default]*len(self.compensator_num)
        self.filt_y = [self.temperature_default]*len(self.compensator_den)
        
        # Input values
        self.read_actual = 0.0
        self.read_setpoint = 0.0
        
        # User input
        self.requested_enable = self.enabled_default
        self.requested_setpoint = self.temperature_default
        self.requested_adjust = 0.0
        
    # Validation function
    def is_acceptable_setpoint(self, setpoint):
        if setpoint > self.temperature_maximum:
            return False
        if setpoint < self.temperature_minimum:
            return False
        return True
        
    # Main computation function
    def do_step(self, voltage_in0, voltage_in1):
        
        ################################################################
        ## Read values and safety interlock
        ################################################################
        self.read_actual   = self.volt_to_temp(voltage_in0)
        self.read_setpoint = self.volt_to_temp(voltage_in1)
        
        panic = False
        self.safe_enable = self.requested_enable
        if self.read_actual > self.temperature_maximum or \
           self.read_actual < self.temperature_minimum:
            panic = True
            self.safe_enable = False
            
        ################################################################
        ## Request temperature
        ################################################################
        # Add adjust values to sum. Because of this, the value might exceed 
        # limits. 
        self.requested_temperature = self.requested_setpoint + self.requested_adjust
        # Limit the sum
        if self.requested_temperature > self.temperature_maximum:
            self.requested_temperature = self.temperature_maximum
        if self.requested_temperature < self.temperature_minimum:
            self.requested_temperature = self.temperature_minimum
            
        # This is the input of the filter
        filter_input = self.requested_temperature
        
        ################################################################
        ## Digital filter (OPTIONAL)
        ## You can bypass this by writing:
        ## filtered_temperature = self.requested_temperature
        ## and commenting the rest.
        ## This filter can help with badly tuned PI loops. This is a
        ## very standard digital filter implementation.
        ################################################################
        # 1) Shift current vectors
        filt_x_new = [0.0]*len(self.compensator_num)
        for i in range(len(self.compensator_num)-1):
            filt_x_new[i+1] = self.filt_x[i]
        filt_y_new = [0.0]*len(self.compensator_den)
        for i in range(len(self.compensator_den)-1):
            filt_y_new[i+1] = self.filt_y[i]
        # 2) Insert new point in x
        filt_x_new[0] = filter_input
        # 3) Compute new filter value y
        for i in range(0,len(self.compensator_num)):
            filt_y_new[0] = filt_y_new[0] + (filt_x_new[i]*self.compensator_num[i])/self.compensator_den[0]
        for i in range(1,len(self.compensator_den)):
            filt_y_new[0] = filt_y_new[0] - (filt_y_new[i]*self.compensator_den[i])/self.compensator_den[0]
        # 4) Save current state of filter
        self.filt_x = filt_x_new
        self.filt_y = filt_y_new
        filter_output = self.filt_y[0]
        
        ################################################################
        ## Output
        ################################################################
        
        filtered_temperature = filter_output
        # Limit the output!
        if filtered_temperature > self.temperature_maximum:
            filtered_temperature = self.temperature_maximum
        if filtered_temperature < self.temperature_minimum:
            filtered_temperature = self.temperature_minimum
            
        # Convert to voltage
        voltage_out0 = self.temp_to_volt(filtered_temperature)
        # Compute logic output
        logic_out = int(self.safe_enable ^ (not self.enabled_is_high))
        return (voltage_out0, logic_out, panic)
        
    # Conversion function
    def volt_to_temp(self,volt):
        if volt == 0.0:
            temp = np.NaN
            #print "voltage = 0"
        elif volt < 0.0:
            temp = np.NaN
            #print volt
        else:
            #convert voltage to temperature using Steinhart-Hart equation
            #Convert Measured Voltage into resistance of 10 k thermistor
            R = 1.0*volt/self.Ibias
            temp = 1/(self.A+self.B*np.log(R)+self.C*(np.log(R))**3) - 273.15 #Steinhart&Hart eqn
        return temp
        
    # Conversion function
    def temp_to_volt(self,temp):
        #convert temperature to voltage using Steinhart-Hart equation
        y = (self.A-1/(temp+273.15))/(2*self.C)        
        x = np.sqrt((self.B/(3*self.C))**3+y**2)        
        R = np.exp(np.power(x-y,1/3.0)-np.power(x+y,1/3.0))
        volt = self.Ibias*R
        #print('%f'%volt)
        return volt
        

        