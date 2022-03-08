from __future__ import division
try: # python 2
    range = xrange
except NameError: # python 3
    pass
from six import iteritems

import serial, sys, glob
from copy import deepcopy

# Modified 2018-09-24 rjw

######## See  ORION Laser Module Remote Command Interface R5 0.3.pdf #########

#################### ORION Serial Settings ###################################
##### 9600 Baud, 8 Data Bits, No Parity Bit, 1 Stop Bit, No Flow Control #####
##############################################################################

########################### GENERAL PACKET FORM ###############################
## Packet sent to laser:                                                    ###
##   |HDR|PKT ID|LEN|SRC ID|DEST ID|CMD TYPE|CMD ID|DATA|CHKSUM|FTR|        ###
## Packet received from laser:                                              ###
##   |HDR|PKT ID|LEN|SRC ID|DEST ID|CMD TYPE|STATUS|CMD ID|DATA|CHKSUM|FTR| ###
###############################################################################

# Constants set up by ORION Laser
# header and footer
HDR = 0xA9
FTR = 0xA5
try: # Works on Py2, not 3
    HDRCHR = bytes(chr(HDR))
    FTRCHR = bytes(chr(FTR))
except TypeError:
    HDRCHR = bytes([HDR])
    FTRCHR = bytes([FTR])

# SCR ID and DEST ID codes
# Sending from computer SRC ID = ID_COMPUTER, DEST ID = ID_LASER; received
# packet should be reversed
ID_COMPUTER = 0x00
ID_LASER = 0xFF

# CMD TYPE codes
TYPE_READ = 0x01
TYPE_WRITE = 0x02

# PKT ID is echoed in the respose to identify packets
PKT_ID_DEFAULT = 0x00

# LEN does not include HDR and FTR bytes, = toal len - 2

# See chksum_gen for formalua used for CHKSUM

# Plain text name for HEX code commands (valid values for CMD ID)
COMMAND_NAMES = {
    0x01:'frmwRead',
    0x04:'defIRead',
    0x06:'defTempRead',
    0x08:'snRead',
    0x0A:'ontimeRead',
    0x0E:'statusRead',
    0x11:'actTempRead',
    0x12:'brdTempRead',
    0x13:'phtVRead',
    0x1D:'volIRead',
    0x1E:'volIWrt',
    0x1F:'volTempRead',
    0x20:'volTempWrt',
    0x24:'enbSer',
    0x25:'disSer',
    0x26:'nvlIRead',
    0x27:'nvlIWrt',
    0x28:'nvlTempRead',
    0x29:'nvlTempWrt',
    0x42:'pnRead',
    0x44:'ituRead'
}

# Allow lookup of HEX code based on plain text command name
COMMANDS = dict((v,k) for k,v in iteritems(COMMAND_NAMES))

# The command type (read or write) for each command
COMMAND_TYPES = {
    0x01:TYPE_READ,
    0x04:TYPE_READ,
    0x06:TYPE_READ,
    0x08:TYPE_READ,
    0x0A:TYPE_READ,
    0x0E:TYPE_READ,
    0x11:TYPE_READ,
    0x12:TYPE_READ,
    0x13:TYPE_READ,
    0x1D:TYPE_READ,
    0x1E:TYPE_WRITE,
    0x1F:TYPE_READ,
    0x20:TYPE_WRITE,
    0x24:TYPE_WRITE,
    0x25:TYPE_WRITE,
    0x26:TYPE_READ,
    0x27:TYPE_WRITE,
    0x28:TYPE_READ,
    0x29:TYPE_WRITE,
    0x42:TYPE_READ,
    0x44:TYPE_READ,
}

# Plain text eplaination of laser status codes
STATUSES = {
    0x00:'no error',
    0x01:'invalid command (incorrect packet format - header, footer, checksum)',
    0x04:'command timeout (packet has not been correctly terminated in 65 sec)',
    0x08:'correct packet format, invalid command type, command ID',
    0x20:'invalid switch command (during firmware update)',
    0x21:'invalid commit command (during firmware update)',
    0x22:'invalid erase command (during firmware update)',
    0x23:'write flash error (during firmware update)',
    0x24:'invalid flash address (in the firmware update write flash command)',
    0x25:'invalid page checksum (during firmware update)',
    0x30:'correct packet format, command argument (set-point) out of range',
}

# Limits; Orion suggestions: Temp < 80 deg C, I < 125mA
# [Min, Max] allowable values for the associated commands
# Example, 0x1E:[800, 1100] sets allowable volatile pump current between 80mA and 110mA
I_LIMITS = [600, 1200] # Current range (in 10's of mA)
T_LIMITS = [6500, 15000] # Temp range (in ohms)
LIMITS_DEFAULT = {0x1E:I_LIMITS,
                  0x20:T_LIMITS,
                  0x27:I_LIMITS,
                  0x29:T_LIMITS}

###############################################################################
################### General Data Manipulation Methods #########################
def twos_complement_byte(val):
    """Convert a byte val to a signed integer"""
    if val > 127: # Max number that can be represented by a signed byte
        return val - 256
    return val

def num2bytes(val):
    """Convert positive integer to a list of bytes in big-endian format"""
    if val is None:
        return bytearray()
    num_bytes = (val.bit_length() - 1)//8 # = (num of bytes needed for val) - 1
    if num_bytes < 0:
        return bytearray(b'\x00')
    return bytearray((val >> i) & 0xFF for i in range(num_bytes*8, -1, -8))

def bytes2num(byte_list):
    """Convert list of bytes in big-endian format to an integer"""
    if not len(byte_list):
        return None
    return sum(b << (8*i) for i, b in enumerate(reversed(byte_list)))

def num2str(val):
    if val is None:
        return ''
    num_bytes = (val.bit_length() - 1)//8 # = (num of bytes needed for val) - 1
    if num_bytes < 0:
        return '\x00'
    s = ''
    for i in range(num_bytes*8, -1, -8):
        s += chr((val >> i) & 0xFF)
    return s

def list_serial_ports():
    # From http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    """ Lists active serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

###############################################################################
##################### Orion Laser Specific Methods ############################

def chksum_gen(byte_list):
    """Generates a checksum value based on the ORION Laser algorithm"""
    chksum = sum(twos_complement_byte(b) for b in byte_list[:-2])*-1
    return chksum & 0xFF #Returns only 1 byte (disreguards overflow)

def chksum_insert(byte_list):
    """Inserts checksum value based on the ORION Laser algorithm"""
    byte_list[-2] = chksum_gen(byte_list)
    return byte_list

def pkt_gen(cmd_id, val=None, pkt_id=PKT_ID_DEFAULT):
    """Generates a list of bytes to send to ORION Laser based on input"""
    cmd_type = COMMAND_TYPES[cmd_id]; data = num2bytes(val)
    # General packet format with len and chksum temporarily 0x00
    pkt = bytearray([HDR, pkt_id, 0x00, ID_COMPUTER, ID_LASER, cmd_type, cmd_id]) + data + b'\x00' + FTRCHR

    # Generate and insert len and chksum values
    pkt[2] = len(pkt) - 2
    return chksum_insert(pkt)

def pkt_read(ser):
    # Get bytes until there is a HDR byte
    b = ser.read(1)
    while b != HDRCHR and len(b): # 9 is min packet size
        b = ser.read(1)
    if b != HDRCHR:
        raise IOError('Serial stream did not contain header')

    # Read up until the length byte
    s1 = ser.read(2)
    if len(s1) != 2:
        raise IOError('Insufficient bytes in serial stream')
    l = s1[-1]
    try:
        remaining_bytes = l - 1
    except TypeError: # Python 2 serial read is str not bytes
        remaining_bytes = ord(l) - 1

    # Get rest of packet
    s2 = ser.read(remaining_bytes)
    if len(s2) != remaining_bytes:
        raise IOError('Insufficient bytes in serial stream to match packet size (%i vs %i)' % (3 + len(s2), remaining_bytes + 3))

    return bytearray(b + s1 + s2)

def pkt_validate(byte_list, pkt_id=None):
    """
    Validates list of bytes as a genuine ORION packet format
    by checking header, footer, length, packet id, and check sum
    """
    if len(byte_list) < 9:
        print('Packet too short')
        return False

    chksum_pass = (chksum_gen(byte_list) == byte_list[-2])
    if not chksum_pass:
        print('Packet failed chksum test')

    length_pass = (len(byte_list) - 2 == byte_list[2])
    if not length_pass:
        print('Packet failed len test')

    hdr_pass = (byte_list[0] == HDR)
    if not hdr_pass:
        print('Packet failed hdr test')

    ftr_pass = (byte_list[-1] == FTR)
    if not ftr_pass:
        print('Packet failed ftr test')

    if pkt_id == None:
        pkt_id_pass = True
    else:
        pkt_id_pass = (pkt_id == byte_list[1])
        if not pkt_id_pass:
            print('Packet failed id test')

    return chksum_pass and length_pass and hdr_pass and ftr_pass and pkt_id_pass

def pkt_interpret(byte_list):
    """Validates a list of bytes recieved from the ORION Laser
    and returns the data and status fields
    """
    # Remove any leading zeros
    while byte_list[0] == 0x00 and len(byte_list) > 9:
        byte_list.pop(0)

    # Validate byte_list, raise exception if not valid
    if not pkt_validate(byte_list):
        raise ValueError('Invlaid packet %s' % str(byte_list))

    # Return status and data
    val = bytes2num(byte_list[8:len(byte_list)-2])
    status = byte_list[6]
    return val, status

def find(sn=None):
    result = []
    for port in list_serial_ports():
        try:
            test_laser = OrionLaser(port)
            print('Orion (%i) found on port %s' % (test_laser.sn, port))
            if sn is None:
                result.append(port)
            else:
                if test_laser.sn == sn:
                    result.append(port)
            test_laser.close()
        except Exception as e:
            print('No Orion on %s (%s)' % (port,e))
    return result

###############################################################################
############################ Orion Laser Class ################################

class OrionLaser():

    def __init__(self, port, name=None, verbose=False):
        self.verbose = verbose
        self.ser = serial.Serial(port.strip(),
                                 baudrate=9600,
                                 parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE,
                                 bytesize=serial.EIGHTBITS,
                                 xonxoff=False,
                                 timeout=0.1)
        self.port = self.ser.portstr
        self.limits = deepcopy(LIMITS_DEFAULT)

        try:
            self.execute_cmd(0x24, None) # Enable RS232

            self.i_factory = self.execute_cmd(0x04, None) # Read factory default current (in 0.1 mA)
            self.t_factory = self.execute_cmd(0x06, None) # Read factory default temp (ohms)

            self.i_invol = self.execute_cmd(0x26, None) # Read involatile current (in 0.1 mA)
            self.t_invol = self.execute_cmd(0x28 ,None) # Read involatile temp (ohms)

            self.i_0 = self.execute_cmd(0x1D, None) # Read current setpoint at initialization (in 0.1 mA)
            self.t_0 = self.execute_cmd(0x1F, None) # Read temp setpoint at initialization (ohms)

            self.sn = self.execute_cmd(0x08, None) # Read device serial number
            self.pn = num2str(self.execute_cmd(0x42, None)).strip() # Read product ID

            self.execute_cmd(0x25, None) #Disable RS232

        except Exception as e:
            print('Failed initial configuration of ORION laser on %s: %s' % (self.port, e))
            try:
                self.execute_cmd(0x25, None) # Disable RS232
            except Exception:
                pass
            self.ser.close()
            raise e

        if name is None:
            self.name = 'ORION Laser (SN%i) on %s' % (self.sn, self.port)
        else:
            self.name = name

        print(self.name + ' was connected successfully.')

    def execute_cmd(self, cmd, val):
        try:
            lim = self.limits[cmd]
            if val < lim[0] or val > lim[1]:
                raise ValueError('Requested value (%i) is outside limits (%i to %i)' % (val, lim[0], lim[1]))
        except KeyError:
            pass
        pkt_send = pkt_gen(cmd, val)
        self.ser.write(pkt_send)
        resp = pkt_read(self.ser)
        if self.verbose:
            print(COMMAND_NAMES[cmd])
            print(list(pkt_send))
            print('response:')
            print(list(resp))
            print('')
        return_value, status_code = pkt_interpret(resp)
        if status_code != 0x00:
            print('Laser status error: ' + STATUSES[status_code])
        elif return_value != val and val is not None:
            print('Reported set point (%i) does not match requested (%i)' % (return_value, val))
        return return_value

    def get_t(self):
        self.execute_cmd(0x24, None) # Enable RS232
        temp = self.execute_cmd(0x1F, None) # Read vol temp
        self.execute_cmd(0x25, None) # Disable RS232
        return temp

    def set_to_default(self, reset_to_factory=False):
        self.execute_cmd(0x24, None) # Enable RS232
        if reset_to_factory:
            self.execute_cmd(0x27, self.i_factory) # Set invol current
            self.execute_cmd(0x29, self.t_factory) # Set invol temp
            self.i_invol = self.i_factory
            self.t_invol = self.t_factory
        self.execute_cmd(0x1E, self.i_invol) # Set vol current
        self.execute_cmd(0x20, self.t_invol) # Set vol temp
        self.execute_cmd(0x25, None) # Disable RS232

    def set_t(self, temp):
        self.execute_cmd(0x24, None) # Enable RS232
        self.execute_cmd(0x20, temp) # Set vol temp
        self.execute_cmd(0x25, None) # Disable RS232

    def set_i(self, i):
        self.execute_cmd(0x24, None) # Enable RS232
        self.execute_cmd(0x1E, i) # Set vol current
        self.execute_cmd(0x25, None) # Disable RS232

    def change_t(self, dTemp):
        self.execute_cmd(0x24, None) # Enable RS232
        temp = self.execute_cmd(0x1F, None) # Read vol temp
        new_temp = temp + dTemp
        self.execute_cmd(0x20, new_temp) # Set vol temp
        self.execute_cmd(0x25, None) # Disable RS232
        return new_temp

    def change_i(self, dI):
        self.execute_cmd(0x24, None) # Enable RS232
        i = self.execute_cmd(0x1D, None) # Read vol current
        new_i = i + dI
        self.execute_cmd(0x1E, new_i) # Set vol current
        self.execute_cmd(0x25, None) # Disable RS232
        return new_i

    def close(self):
        print('\nClosing ' + self.name)
        try:
            self.execute_cmd(0x25, None) # Disable RS232
        except Exception:
            pass
        self.ser.close()
        print(self.name + ' is closed\n')

###############################################################################
################################ Testing ######################################

def main():
    print('')
    # laser = OrionLaser(find()[0], verbose=True)
    laser = OrionLaser('COM8', verbose=True)
    laser.execute_cmd(0x24, None) # Enable RS232
    print('\nEnter laser cmd, exit, or help')
    while True:
        usr_in = input(">> ").strip()
        #Try to use input as command
        if usr_in.lower() == 'exit':
            break
        elif usr_in.lower() == 'help':
            # print list of acceptable commands
            cmdlist = COMMANDS.keys()
            cmdlist.extend(('exit', 'help'))
            cmdlist = sorted(cmdlist, key=str.lower)
            for command in cmdlist:
                print(command)
            print('')
        else:
            # Get HEX command equivalent to input
            try:
                cmd = COMMANDS[usr_in]
            except KeyError:
                print('Invalid command\n'); continue
            val = None # If command is a write command ask user for desired value
            if COMMAND_TYPES[cmd] == TYPE_WRITE and cmd != 0x24 and cmd != 0x25:
                print('   Enter a value or cancel')
                while True:
                    usr_in = input('   >> ').strip().lower()
                    #Try to use input as integer value
                    try:
                        if usr_in == 'cancel' or usr_in == 'exit': #user canceled command
                            val = 'c'; break
                        val = int(usr_in); break
                    except:
                        print('   Invalid value. Enter an integer or cancel')
            if val != 'c': #User did not cancel command
                #Try to send command to laser
                try:
                    ret = laser.execute_cmd(cmd, val)
                    print(ret)
                except Exception as e:
                    print(e)
            print('')

    # Clean up before close
    laser.close()

if __name__ == '__main__':
    main()