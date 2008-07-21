"""Event handling and functions for joysticks and the Wii Remote.

Handles keyboard, joystick, and Wii Remote events.
"""

import pygame
from pygame.locals import *
import engine_util
import math
try:
    from engine_wiimote import *
except:
    print "NO WIIMOTE SUPPORT"
    class WiimoteNotSupported(IOError):
        """Raised if there is any problem related to the Wii Remote."""
    class Wiimote:
        def __init__(self, num=0, lightpattern=[True, False, False, False]):
            raise WiimoteNotSupported

# joystick axes identification
JOYAXIS_X = 0
JOYAXIS_Y = 1

# Constants to represent joystick actions
# Designed to mimic pygame.locals keyboard constants e.g. K_UP

J_START = 1024
J_BUTTON1 = 0 + 1024
J_BUTTON2 = 1 + 1024
J_BUTTON3 = 2 + 1024
J_BUTTON4 = 3 + 1024
J_BUTTON5 = 4 + 1024
J_BUTTON6 = 5 + 1024
J_BUTTON7 = 6 + 1024
J_BUTTON8 = 7 + 1024
J_BUTTON9 = 8 + 1024
J_BUTTON10 = 9 + 1024
J_MAXBUTTON = J_BUTTON10

W_START = 2048
W_A = 0 + 2048
W_B = 1 + 2048
W_ONE = 2 + 2048
W_TWO = 3 + 2048
W_MINUS = 4 + 2048
W_HOME = 5 + 2048
W_PLUS = 6 + 2048
W_UP = 7 + 2048
W_DOWN = 8 + 2048
W_LEFT = 9 + 2048
W_RIGHT = 10 + 2048
W_NUNCHUK_Z = 11 + 2048
W_NUNCHUK_C = 12 + 2048

W_SHAKE = 4096
W_NUNCHUK_SHAKE = 4097

W_MAXBUTTON = W_NUNCHUK_C

W_MAX_CLOSENESS = 0.05
W_SENSITIVITY = 0.2

M_START = 6000
M_BUTTON1 = 6000
M_BUTTON2 = 6002
M_WHEELUP = 6003
M_WHEELDOWN = 6004
M_MAXBUTTON = M_WHEELDOWN


def joystick_axes(x, y):
    """Set up joystick axes depending on brand of joystick.
    
    Classroom joysticks use 0 and 1, other funky models might use 2 and 3.
    """
    global JOYAXIS_X
    global JOYAXIS_Y
    JOYAXIS_X = x
    JOYAXIY_y = y

# Event handlers are:
# (key/button/direction, func, should_repeat, is_currently_repeating)
# For case of not should_repeat, last one is happened
_event_handlers = []
# Event list is timed events that will happen
# format is (time when event happens, func)
# times are seconds
_event_list = []
_joystick = []
_joystick_data = []
_wii = []

def light_pattern(i):
    if i == 0: return [True, False, False, False]
    if i == 1: return [False, True, False, False]
    return [True, True, True, True]

def connect_to_wiimote(num=0, lightpattern=[True, False, False, False], all=False):
    """Connect to Wiimote using Bluetooth connection.
    
    May take some time, connects to first Wiimote found unless num is
    given.  If num is given, connects to that remote/
      0 = first one found
      1 = second one found etc.
    lightpattern is a list of booleans that indicate how to set the lights
    to avoid confusion.
    all - whether to connect to all wiimotes up to that number
    (lightpattern is ignored in this case, uses default patterns)
    """
    global _wii
    if all:
        for i in range(num):
            w = Wiimote(i, light_pattern(i))
            w.orientation = [0, 0, 1]
            w.norientation = [0, 0, 1]
            w.when_triggered = [0, 0]
            w.triggered = [False, False]
            w.pointer_history = []
            _wii.append(w)
    else:
        w = Wiimote(num, lightpattern)
        w.orientation = [0, 0, 1]
        w.norientation = [0, 0, 1]
        w.when_triggered = [0, 0]
        w.triggered = [False, False]
        w.pointer_history = []
        _wii.append(w)

def close_wiimote():
    global _wii
    del _wii
    _wii = None


def wait_for_keypress(lst=[K_RETURN, K_SPACE, K_ESCAPE, M_BUTTON1, W_A, W_B, J_BUTTON9, J_BUTTON10]):
    """Wait for a keyboard keypress, joystick button press, Wiimote button, or mouse button.
    """
    while True:
        if len(_wii) > 0:
            for w in _wii:
                w.tick()
                for e in lst:
                    if e >= W_A and e <= W_MAXBUTTON and w.get_button(e - W_A): return
        for evt in pygame.event.get():
            if evt.type == QUIT:
                engine_util.exit()
            if evt.type == KEYDOWN:
                if evt.key == K_q and ((evt.mod & KMOD_META > 0) or (evt.mod & KMOD_CTRL > 0)):
                    engine_util.exit()
                for e in lst:
                    if evt.key == e: return
            if evt.type == JOYBUTTONDOWN:
                for e in lst:
                    if evt.button == e - J_BUTTON1: return
            if evt.type == MOUSEBUTTONDOWN:
                for e in lst:
                    if evt.button == e - M_BUTTON1: return

def add_event(func, when=0.0, relative=True):
    """Call an event function at a specified time.

    func - function to call
    when - when to call it, measured in seconds
    relative - if True, when is relative to now
    otherwise when is absolute from start of game
    """
    global _event_list
    if relative:
        _event_list.append((when + time(), func))
    else:
        _event_list.append((when, func))

def add_recurring_event(func, often=0.0):
    """Call a function repeatedly every 'often' seconds."""
    def f():
        func()
        add_event(f, often, relative=True)
    add_event(f)

def clear_events():
    """Cancel all events and recurring events."""
    global _event_list
    _event_list = []

def add_event_handler(evt, func, repeat = False, device = 0):
    """For a given event, add an event handler function that will
    be called when the event triggers.
    
    The optional argument repeat indicates whether the event
    handler should be called repeatedly as the key or button
    is held down.  The event handler only triggers when the
    main engine tick() function is called, so don't forget
    to call tick() in your main loop.
    
    device - specify this if you are using more than 1 joystick/wiimote
    """
    # Fourth argument is current state of repeat, starts off (False)
    global _event_handlers
    _event_handlers.append([evt, func, repeat, False, device])
    
def clear_event_handlers(evt):
    """Clear all the event handlers for a given event."""
    global event_handlers
    for i in range(len(_event_handlers)):
        if i < len(_event_handlers) and _event_handlers[i][0] == evt:
            _event_handlers[i:i+1] = []
        
def time():
    """Return the current time since game start, in seconds."""
    return pygame.time.get_ticks() / 1000.0

_orientation = [0, 0, 0]
def handle_events():
    """Handle pygame events according to previously set event handlers."""
    # First do time events
    global _event_list
    t = time()
    for (tm, func) in _event_list[:]:
        if tm < t:
            func()
            _event_list.remove((tm, func))
    for i in _event_handlers:
        if i[2] and i[3]:
            i[1]()
    # Now do Wiimote events
    if len(_wii) > 0:
        for wi in range(len(_wii)):
            w = _wii[wi]
            w.tick()
            # Wiimote buttons
            for e in _event_handlers:
                event, func, should_repeat, is_repeat, device = e
                if event >= W_A and event <= W_MAXBUTTON and device == wi:
                    if should_repeat:
                        e[3] = w.get_button(event - W_START)
                    else:
                        if is_repeat:
                            e[3] = w.get_button(event - W_START)
                        else:
                            if w.get_button(event - W_START):
                                func()
                                e[3] = True
            # Wiimote triggers
            acc = w.get_acc()
            l = vlen(acc)
            if l > 0.8 and l < 1.2:
                w.orientation = [0.5 * w.orientation[i] + 0.5 * acc[i] for i in range(3)]
                w.orientation = vnorm(w.orientation)
            else:
                if 0 * acc[0] - acc[2] > W_SENSITIVITY and w.triggered[0]:
                    w.triggered[0] = False
                if 0 * acc[0] - acc[2] < W_SENSITIVITY - 0.5 and not w.triggered[0] and time() > w.when_triggered[0] + W_MAX_CLOSENESS:
                    w.triggered[0] = True
                    w.when_triggered[0] = time()
                    for (event, func, shld_rep, repeating, device) in _event_handlers:
                        if event == W_SHAKE and device == wi:
                            func()

            acc = w.get_nunchuk_acc()
            l = vlen(acc)
            if l > 0.8 and l < 1.2:
                w.norientation = [0.5 * w.norientation[i] + 0.5 * acc[i] for i in range(3)]
                w.norientation = vnorm(w.norientation)
            else:
                sens = 0.8
                if 0 * acc[0] - acc[2] > W_SENSITIVITY and w.triggered[1]:
                    w.triggered[1] = False
                if 0 * acc[0] - acc[2] < W_SENSITIVITY - 0.5 and not w.triggered[1] and time() > w.when_triggered[1] + W_MAX_CLOSENESS:
                    w.triggered[1] = True
                    w.when_triggered[1] = time()
                    for (event, func, shld_rep, repeating, device) in _event_handlers:
                        if event == W_NUNCHUK_SHAKE and device == wi:
                            func()


    # Now do pygame events (keyboard and joystick)
    for evt in pygame.event.get():
        if evt.type == QUIT:
            engine_util.exit()
        if evt.type == KEYDOWN:
            if evt.key == K_q and ((evt.mod & KMOD_META > 0) or (evt.mod & KMOD_CTRL > 0)):
                engine_util.exit()
        for e in _event_handlers:
            event, func, should_repeat, is_repeat, device = e
            if evt.type == KEYUP and event == evt.key:
                e[3] = False
            if evt.type == JOYBUTTONUP and event == evt.button + J_START and device == evt.joy:
                e[3] = False
            if evt.type == MOUSEBUTTONUP and event == evt.button - 1 + M_START:
                e[3] = False
            if evt.type == KEYDOWN and event == evt.key:
                if should_repeat:
                    e[3] = True
                else:
                    func()
            if evt.type == JOYBUTTONDOWN and event == evt.button + J_START and device == evt.joy:
                if should_repeat:
                    e[3] = True
                else:
                    func()
            if evt.type == MOUSEBUTTONDOWN and event == evt.button - 1 + M_START:
                if should_repeat:
                    e[3] = True
                else:
                    func()

class JoystickData:
    pass
    
# Setup joystick if present
def connect_to_joysticks():
    global _joystick
    _joystick = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in _joystick: 
        j.init()
        data = JoystickData()
        data.p = [0, 0]
        data.vel = [0, 0]
        _joystick_data.append(data)

def get_mouse_position():
    """Return mouse coordinate, will always be in [0,0] through [800,600]."""
    return [x for x in pygame.mouse.get_pos()]
    
def get_mouse_button(b):
    """Return a boolean representing whether button b is held down."""
    if b == M_BUTTON1:
        return pygame.mouse.get_pressed()[0]
    if b == M_BUTTON2:
        return pygame.mouse.get_pressed()[2]
    return False

def get_joystick_direction(num=0):
    """Return current angle joystick is pushed, or None if centered."""
    global _joystick
    if len(_joystick) <= num:
        return None
    x = _joystick[num].get_axis(JOYAXIS_X)
    y = _joystick[num].get_axis(JOYAXIS_Y)
    if x > 0.5:
        if y < -0.5: return 360 - 45
        if y > 0.5: return 45
        return 0
    if x < -0.5:
        if y < -0.5: return 180 + 45
        if y > 0.5: return 90 + 45
        return 180
    if y < -0.5: return 270
    if y > 0.5: return 90
    return None

def get_wiimote_button(b, num=0):
    if num > len(_wii): return False
    w = _wii[num]
    if b >= W_A and b <= W_MAXBUTTON:
        return w.get_button(b - W_A)
    return False
    
def get_joystick_button(b, num=0):
    if num > len(_joystick): return False
    w = _joystick[num]
    if b >= J_BUTTON1 and b <= J_MAXBUTTON:
        return w.get_button(b - J_BUTTON1)
    return False

def call(f, *args):
    """Return a function that calls a given function with some arguments.

    f - the function to call
    args - the arguments to pass to f

    Use this function in event callbacks.  Instead of saying:
      add_event_handler(K_RIGHT, move_sprite(100))
    say this:
      add_event_handler(K_RIGHT, call(move_sprite, 100))

    It works on functions that take zero, one, or more arguments.
      add_event_handler(K_RIGHT, call(do_it))
      add_event_handler(K_RIGHT, call(do_lots_of_it, 1, 2, 3, 4))

    You need to wrap functions because otherwise they would be evaluated
    directly one time as you add the event handler.  You don't want to
    call your function and pass the return value to add_event_handler,
    you want to pass a function to the event handler.

    Instead of using call_function, you can define your functions
    directly like this:
      def f():
          do_it()
      add_event_handler(K_RIGHT, f)
    """
    def func():
        return f(*args)
    return func


def vlen(v):
    s = 0
    for vi in v: s += vi * vi
    if s > 1e300:
        return 1e300
    return s ** 0.5

def vscale(v, s):
    return [vi * s for vi in v]

def vnorm(v):
    l = vlen(v)
    if l < 0.0000001: return v
    return vscale(v, 1.0 / l)

_smooth_dict = {}

def smooth(k, func, avg):
    global _smooth_dict
    if _smooth_dict.has_key(k):
        n, hist = _smooth_dict[k]
    else:
        n, hist = avg, [0] * avg
    hist = hist[:n - 1]
    hist[0:0] = [func()]
    _smooth_dict[k] = (n, hist)
    s = 0
    for r in hist:
        if r != None:
            s += r
    return s * (1.0 / n)

def get_wiimote_acc(num=0):
    if len(_wii) <= num:
        return [0, 0, 0]
    return _wii[num].get_acc()

def get_wiimote_roll(num=0, avg=8):
    return smooth('roll', call(_get_wiimote_roll, num), avg=avg)
def _get_wiimote_roll(num):
    """Return current angle wii is rolled, or None.

    Roll is rotation about y axis.  Values are in angles,
    from -180 to 180.  Zero is level like a regular remote.
    Negative roll is to the left, positive is to the right
    (clockwise rotation).
    """
    global _wii
    if len(_wii) <= num:
        return None
    x, y, z = _wii[num].get_acc()
    v = vnorm([x, z])
    return math.atan2(v[0], v[1]) * 180.0 / 3.14159

def get_nunchuk_roll(num=0, avg=8):
    return smooth('nroll', call(_get_nunchuk_roll, num), avg=avg)
def _get_nunchuk_roll(num):
    global _wii
    if len(_wii) <= num:
        return None
    x, y, z = _wii[num].get_nunchuk_acc()
    v = vnorm([x, z])
    return math.atan2(v[0], v[1]) * 180.0 / 3.14159

def get_wiimote_pitch(num=0, avg=8):
    return smooth('pitch', call(_get_wiimote_pitch, num), avg=avg)
def _get_wiimote_pitch(num):
    """Return current angle wii is pitched, or None.

    Pitch is rotation about x axis.  Values are in angles,
    from -180 to 180.  Zero is level like a regular remote.
    Negative pitch is up, positive is down
    (clockwise rotation when looking from the right)."""
    global _wii
    if len(_wii) <= num:
        return None
    x, y, z = _wii[num].get_acc()
    v = vnorm([y, z])
    return math.atan2(v[0], v[1]) * 180.0 / 3.14159

def get_nunchuk_pitch(num=0, avg=8):
    return smooth('npitch', call(_get_nunchuk_pitch, num), avg=avg)
def _get_nunchuk_pitch(num):
    global _wii
    if len(_wii) <= num:
        return None
    x, y, z = _wii[num].get_nunchuk_acc()
    v = vnorm([y, z])
    return math.atan2(v[0], v[1]) * 180.0 / 3.14159

def get_wiimote_tilt(num=0, avg=8):
    return smooth('tilt', call(_get_wiimote_tilt, num), avg=avg)
def _get_wiimote_tilt(num):
    """Return current angle wii is tilted, or None.

    Tilt is rotation about z axis.  Values are in angles,
    from -180 to 180.  Zero is right.  Positive angles
    are clockwise from right (game standard).
    """
    global _wii
    if len(_wii) <= num:
        return None
    x, y, z = _wii[num].get_acc()
    v = vnorm([y, x])
    return -math.atan2(v[0], v[1]) * 180.0 / 3.14159

def get_nunchuk_tilt(num=0, avg=8):
    return smooth('ntilt', call(_get_nunchuk_tilt, num), avg=avg)
def _get_nunchuk_tilt(num):
    global _wii
    if len(_wii) <= num:
        return None
    x, y, z = _wii[num].get_nunchuk_acc()
    v = vnorm([y, x])
    return -math.atan2(v[0], v[1]) * 180.0 / 3.14159
    
def get_nunchuk_joystick(num=0):
    global _wii
    if len(_wii) <= num:
        return [0, 0]
    x, y = _wii[num].get_nunchuk_joystick()
    d = (x * x + y * y) ** 0.5
    if d == 0.0:
        return [0, 0]
    return [d, math.atan2(-y, x)]

def get_nunchuk_joystick_xy(num=0):
    global _wii
    if len(_wii) <= num:
        return [0, 0]
    x, y = _wii[num].get_nunchuk_joystick()
    return x, -y

def clamp(x, lo, hi):
    if x < lo: return lo
    if x > hi: return hi
    return x


def joystick_pointer(num=0, speed=1.0, maxspeed=None, slide=2.0, rect=[0, 0, 800, 600]):
    if maxspeed==None:
        maxspeed = speed * 5.0
    d = get_joystick_direction(num=num)
    j = _joystick_data[num]
    if d != None:
        dx = math.cos(d / 360.0 * 2 * 3.14159) * speed / 50.0
        dy = math.sin(d / 360.0 * 2 * 3.14159) * speed / 50.0
    else:
        dx, dy = 0, 0
    drag = 0.5 ** (1.0 / slide)
    j.vel = [clamp((j.vel[0] + dx) * drag, -maxspeed/50.0, maxspeed/50.0), 
        clamp((j.vel[1] + dy) * drag, -maxspeed/50.0, maxspeed/50.0)]
    j.p = [clamp(j.p[0] + j.vel[0], -1, 1),
        clamp(j.p[1] + j.vel[1], -1, 1)]
    return [rect[0] + (rect[2] - rect[0]) * (j.p[0] * 0.5 + 0.5),
        rect[1] + (rect[3] - rect[1]) * (j.p[1] * 0.5 + 0.5)]
        


p = [0, 0]
v = [0, 0]
g = [0, 0, 1]
def wiimote_pointer(num=0, speed=5.0, slide=5.0, rect=[0, 0, 800, 600], average=8, anchor=False):
    global p
    global v
    global g
    if num >= len(_wii):
        return [rect[0] + rect[2] / 2, rect[1] + rect[3] / 2]
    w = _wii[num]
    f = get_wiimote_acc(num)
    if anchor:
        g = f
    else:
        dif = [(f[i] - g[i]) * speed / 100.0 for i in range(3)]
        dif[1] *= 1.8
        p = [clamp(p[i] + dif[i] + v[i], -1, 1) for i in range(2)]
        if abs(vlen(dif) - 1.0) > 0.1:
            v = [v[i] + dif[i] / 2.0 for i in range(2)]
        g = [g[i] + (f[i] - g[i]) * 0.1 for i in range(3)]
        v = [v[i] * (0.5 ** (1.0 / slide)) for i in range(2)]

    x = rect[0] + (rect[2] - rect[0]) * (p[0] * 0.5 + 0.5)
    y = rect[1] + (rect[3] - rect[1]) * (p[1] * 0.5 + 0.5)
    if len(w.pointer_history) < average:
        w.pointer_history = [[rect[0] + rect[2] / 2, rect[1] + rect[3] / 2] for i in range(average)]
    w.pointer_history = w.pointer_history[1:]
    w.pointer_history.append([x, y])
    sx, sy = 0.0, 0.0
    for h in w.pointer_history:
        sx += h[0]
        sy += h[1]
    return [sx / average, sy / average]
