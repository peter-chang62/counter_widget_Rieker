from datetime import datetime

def log(string,timefmt='%Y-%m-%d_%H%M%S'):
    print(datetime.now().strftime(timefmt)+': '+string)

class PumpLaser(object):

    def __init__(self, ard, enable_pin, temp_pin=None, power_pin=None, name=None):
        self.ard = ard
        self.enable_pin = enable_pin
        self.temp_pin = temp_pin
        self.power_pin = power_pin
        if name is None:
            self.name = 'Laser on arduino pin %i' % self.enable_pin
        else:
            self.name = name

        self._is_enabled = False
        self.is_locked = False

    @property
    def is_enabled(self):
        """True if laser is on, otherwise false
        """
        return self._is_enabled
    @is_enabled.setter
    def is_enabled(self,boolean):
        if boolean is not self.is_enabled:
            if self.is_locked:
                log('cannot enable/disable "%s", laser is locked' % self.name)
            else:
                self._is_enabled = boolean
                self.ard.digital_write(self.enable_pin, self.is_enabled)
                if self.is_enabled: log('"%s" enabled' % self.name)
                else: log('"%s" disabled' % self.name)

    @property
    def is_locked(self):
        """Enable to prevent the laser from being turned on
        """
        return self._is_locked
    @is_locked.setter
    def is_locked(self,boolean):
        self._is_locked = boolean
        if self.is_locked:
            self.is_enabled = False

    def __del__(self):
        self.is_enabled = False
