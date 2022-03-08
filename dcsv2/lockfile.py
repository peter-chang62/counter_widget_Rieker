"""
Created on Thu Aug 06 23:04:23 2015

@author: hnb3

This is a sort of hack to prevent two processes to open the same devices. 

edited 4/18/18 by rjw to fix bug that causes failure to start if specified path
did not previously exist
"""

import winerror
import pywintypes
import win32file
import os

# Dummy exception
class LockError(StandardError):
    pass
# Lock file class
class LockedFile(object):
    # This opens the lock file, preventing other processes from doing so
    def __init__(self, path):
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        try:
            self._handle = win32file.CreateFile(path, win32file.GENERIC_WRITE, 0, None, win32file.OPEN_ALWAYS, win32file.FILE_ATTRIBUTE_NORMAL, None)
        except pywintypes.error, e:
            if e[0] == winerror.ERROR_SHARING_VIOLATION:
                raise LockError(e[2])
            raise
    # Close the file when you are done
    def close(self):
        self._handle.close()
        
        