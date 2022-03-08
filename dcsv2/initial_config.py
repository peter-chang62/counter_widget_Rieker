# -*- coding: utf-8 -*-
"""
Created on Wed Feb 04 16:40:59 2015

@author: ihk/hnb3
"""

import sys
from PyQt4 import QtGui, uic
#import numpy as np

#Offload the GUI design to this file from Qt designer
initialDialog=uic.loadUiType('tempiconfig.ui')[0]
#subclass the gui form
class initial_config(QtGui.QDialog, initialDialog):
    
    def __init__(self,strDevnameList={},devname_to_name_mapping={}):
        super(initial_config, self).__init__()
        
        self.strDevnameList = strDevnameList
        self.strSelectedDevname = ''
        self.selectedIndex = None
        
        self.setupUi(self)
         
        self.buttonBox.accepted.connect(self.okClicked)
        self.buttonBox.rejected.connect(self.cancelClicked)
    
        
        for key in strDevnameList:
            strDisplay = ''
            
            if (type(strDevnameList) == dict) and (strDevnameList[key] in devname_to_name_mapping):
                box_name = devname_to_name_mapping[strDevnameList[key]]
                strDisplay = 'Name = %s, Device Number # = %s' % (box_name, strDevnameList[key])
            else:
                strDisplay = key
            
            self.comboBox.addItem(strDisplay)
            
            
        self.show()
        
    def okClicked(self):
        self.bOk = True
        self.strSelectedDevname = str(self.strDevnameList[self.comboBox.currentIndex()])    # the str() is to convert the QString to a normal Python string object
        self.selectedIndex = self.comboBox.currentIndex()   
        self.close()
        
    def cancelClicked(self):
        self.bOk = False
        self.close()
        
    def closeEvent(self, e):
#        print('close')
        return

def main():
    
    ###########################################################################
    # Start the User Interface
    
    
    # Start Qt:
    app = QtGui.QApplication(sys.argv)
    
    
    # Load a first window which asks the user a question
    strDict = {0: '01', 1: '02'}
    strList = []
    for key in strDict:
        strList.append(strDict[key])
    Initial_Config = initial_config(strList)
    # Run the event loop for this window
    app.exec_()
    print(Initial_Config.bOk)
    print(Initial_Config.strSelectedDevname)
    print(Initial_Config.selectedIndex)
    
if __name__ == '__main__':
    main()   
    