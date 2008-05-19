import os
import struct

W_MAXBUTTON = 12

_cmdfn = os.path.expanduser('~/WIIMOTEcmd')
_datafn = os.path.expanduser('~/WIIMOTEdata')

class WiimoteError(IOError):
    """Raised if there is any problem related to the Wii Remote."""
class WiimoteButtonError(WiimoteError):
    """Raised if button does not exist."""

class Wiimote:
    def __init__(self, num=0, lightpattern=[True, False, False, False]):
        """Create new WiiMote object representing actual wiimote."""
        self.num = num
        self.lightpattern = lightpattern
        self.acc = [0.0, 0.0, 0.0]
        self.nacc = [0.0, 0.0, 0.0]
        self.button = [0] * (W_MAXBUTTON + 1)
        self.j = [0, 0]
        self._connect()
        
    def _connect(self):
        """Connect Wiimote object to physical wiimote."""
        self.pipe_cmd = os.open(_cmdfn, os.O_WRONLY)
        self.pipe_data = None

#    def __del__(self):
#        os.close(self.pipe_cmd)
#        if self.pipe_data:
#            os.close(self.pipe_data)
        
    def get_button(self, button):
        """Get the state of a Wiimote button."""
        if button >= 0 and button <= W_MAXBUTTON:
            return self.button[button]
        raise WiimoteButtonError

    def get_acc(self):
        """Get the acceleration vector as a 3-tuple (x, y, z).  

        Each value in the tuple ranges from 0 to about 3.0, 
        with 1.0 being gravity (approximately)."""
        return self.acc
        
    def get_nunchuk_acc(self):
        return self.nacc

    def get_nunchuk_joystick(self):
        return self.j

    def set_rumble(self, on=True):
        """Turn rumble on or off on Wiimote."""
        pass

    def tick(self):
        """Update the Wiimote.

        This function reads values from the Wii remote and
        stores them.  To access the values read, use get_button()
        and get_acc().  Generally should be called once a frame.
        """
        fmt = "B" * (W_MAXBUTTON + 1) + "ffffffff"
        os.write(self.pipe_cmd, chr(self.num))
        if self.pipe_data == None:
            self.pipe_data = os.open(_datafn, os.O_RDONLY)
        sdata = os.read(self.pipe_data, struct.calcsize(fmt))
        data = struct.unpack(fmt, sdata)
        self.button = data[0 : W_MAXBUTTON + 1]
        self.acc = data[W_MAXBUTTON + 1 : W_MAXBUTTON + 1 + 3]
        self.nacc = data[W_MAXBUTTON + 1 + 3: W_MAXBUTTON + 1 + 3 + 3]
        self.j = data[W_MAXBUTTON + 1 + 3 + 3: W_MAXBUTTON + 1 + 3 + 3 + 2]

__all__ = [ 'Wiimote' ]
