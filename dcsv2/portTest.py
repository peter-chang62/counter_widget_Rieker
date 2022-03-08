# -*- coding: utf-8 -*-
"""
Created on Wed Nov 11 13:09:05 2015

@author: Rob
"""


import sys
sys.path.insert(0, 'C:\Users\Rob\Desktop\Software\temperature_control\version 6')
import AsyncSocketComms

testnum = 2

socCli = AsyncSocketComms.AsyncSocketClient(60003)
socCli.send_text('%f\n' % testnum)



