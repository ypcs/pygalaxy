'''Wrapper for wiiuse

Copyright 2008 by Nathan Whitehead

Contains code from pyglet.lib to allow library loading
to be self-contained in this file.
Contains code automatically generated using wraptypes
from tools/wraptypes, part of pyglet
Code was generated from slightly hacked version of
wiiuse.h, to allow wraptypes to parse correctly
without changing wraptypes.

wiiuse.h and wiiuse are GPL or LGPL for noncommercial use
Copyright 2006-2007 by Michael Laforest,  thepara (--AT--) gmail [--DOT--] com

pyglet and wraptypes are BSD-style licensed
Copyright 2008 by Alex Holkner

'''
__docformat__ =  'restructuredtext'
__version__ = '0.1'


import os
import re
import sys

import ctypes
import ctypes.util
from ctypes import *

_debug_lib = False
_debug_trace = False

class _TraceFunction(object):
    def __init__(self, func):
        self.__dict__['_func'] = func

    def __str__(self):
        return self._func.__name__

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._func, name)

    def __setattr__(self, name, value):
        setattr(self._func, name, value)

class _TraceLibrary(object):
    def __init__(self, library):
        self._library = library
        print library

    def __getattr__(self, name):
        func = getattr(self._library, name)
        f = _TraceFunction(func)
        return f

class LibraryLoader(object):
    def load_library(self, *names, **kwargs):
        '''Find and load a library.  
        
        More than one name can be specified, they will be tried in order.
        Platform-specific library names (given as kwargs) are tried first.

        Raises ImportError if library is not found.
        '''
        if 'framework' in kwargs and self.platform == 'darwin':
            return self.load_framework(kwargs['framework'])
        
        platform_names = kwargs.get(self.platform, [])
        if type(platform_names) in (str, unicode):
            platform_names = [platform_names]
        elif type(platform_names) is tuple:
            platform_names = list(platform_names)

        if self.platform == 'linux2':
            platform_names.extend(['lib%s.so' % n for n in names])

        platform_names.extend(names)
        for name in platform_names:
            try:
                lib = ctypes.cdll.LoadLibrary(name)
                if _debug_lib:
                    print name
                if _debug_trace:
                    lib = _TraceLibrary(lib)
                return lib
            except OSError:
                path = self.find_library(name)
                if path:
                    try:
                        lib = ctypes.cdll.LoadLibrary(path)
                        if _debug_lib:
                            print path
                        if _debug_trace:
                            lib = _TraceLibrary(lib)
                        return lib
                    except OSError:
                        pass
        raise ImportError('Library "%s" not found.' % names[0])

    find_library = lambda self, name: ctypes.util.find_library(name)

    platform = sys.platform
    if platform == 'cygwin':
        platform = 'win32'

    def load_framework(self, path):
        raise RuntimeError("Can't load framework on this platform.")

class MachOLibraryLoader(LibraryLoader):
    def __init__(self):
        if 'LD_LIBRARY_PATH' in os.environ:
            self.ld_library_path = os.environ['LD_LIBRARY_PATH'].split(':')
        else:
            self.ld_library_path = []

        if 'DYLD_LIBRARY_PATH' in os.environ:
            self.dyld_library_path = os.environ['DYLD_LIBRARY_PATH'].split(':')
        else:
            self.dyld_library_path = []

        if 'DYLD_FALLBACK_LIBRARY_PATH' in os.environ:
            self.dyld_fallback_library_path = \
                os.environ['DYLD_FALLBACK_LIBRARY_PATH'].split(':')
        else:
            self.dyld_fallback_library_path = [
                os.path.expanduser('~/lib'),
                '/usr/local/lib',
                '/usr/lib']
 
    def find_library(self, path):
        '''Implements the dylib search as specified in Apple documentation:
        
        http://developer.apple.com/documentation/DeveloperTools/Conceptual/DynamicLibraries/Articles/DynamicLibraryUsageGuidelines.html

        Before commencing the standard search, the method first checks
        the bundle's ``Frameworks`` directory if the application is running
        within a bundle (OS X .app).
        '''

        libname = os.path.basename(path)
        search_path = []

        if hasattr(sys, 'frozen') and sys.frozen == 'macosx_app':
            search_path.append(os.path.join(
                os.environ['RESOURCEPATH'],
                '..',
                'Frameworks',
                libname))

        if '/' in path:
            search_path.extend(
                [os.path.join(p, libname) \
                    for p in self.dyld_library_path])
            search_path.append(path)
            search_path.extend(
                [os.path.join(p, libname) \
                    for p in self.dyld_fallback_library_path])
        else:
            search_path.extend(
                [os.path.join(p, libname) \
                    for p in self.ld_library_path])
            search_path.extend(
                [os.path.join(p, libname) \
                    for p in self.dyld_library_path])
            search_path.append(path)
            search_path.extend(
                [os.path.join(p, libname) \
                    for p in self.dyld_fallback_library_path])

        for path in search_path:
            if os.path.exists(path):
                return path

        return None

    def find_framework(self, path):
        '''Implement runtime framework search as described by:

        http://developer.apple.com/documentation/MacOSX/Conceptual/BPFrameworks/Concepts/FrameworkBinding.html
        '''

        # e.g. path == '/System/Library/Frameworks/OpenGL.framework'
        #      name == 'OpenGL'
        # return '/System/Library/Frameworks/OpenGL.framework/OpenGL'
        name = os.path.splitext(os.path.split(path)[1])[0]

        realpath = os.path.join(path, name) 
        if os.path.exists(realpath):
            return realpath

        for dir in ('/Library/Frameworks',
                    '/System/Library/Frameworks'):
            realpath = os.path.join(dir, '%s.framework' % name, name)
            if os.path.exists(realpath):
                return realpath

        return None

    def load_framework(self, path):
        realpath = self.find_framework(path)
        if realpath:
            lib = ctypes.cdll.LoadLibrary(realpath)
            if _debug_lib:
                print realpath
            if _debug_trace:
                lib = _TraceLibrary(lib)
            return lib

        raise ImportError("Can't find framework %s." % path)

class LinuxLibraryLoader(LibraryLoader):
    _ld_so_cache = None

    def _create_ld_so_cache(self):
        # Recreate search path followed by ld.so.  This is going to be
        # slow to build, and incorrect (ld.so uses ld.so.cache, which may
        # not be up-to-date).  Used only as fallback for distros without
        # /sbin/ldconfig.
        #
        # We assume the DT_RPATH and DT_RUNPATH binary sections are omitted.

        directories = []
        try:
            directories.extend(os.environ['LD_LIBRARY_PATH'].split(':'))
        except KeyError:
            pass

        try:
            directories.extend([dir.strip() for dir in open('/etc/ld.so.conf')])
        except IOError:
            pass

        directories.extend(['/lib', '/usr/lib'])

        cache = {}
        lib_re = re.compile('lib(.*)\.so')
        for dir in directories:
            try:
                for file in os.listdir(dir):
                    if '.so' not in file:
                        continue

                    # Index by filename
                    path = os.path.join(dir, file)
                    if file not in cache:
                        cache[file] = path

                    # Index by library name
                    match = lib_re.match(file)
                    if match:
                        library = match.group(1)
                        if library not in cache:
                            cache[library] = path
            except OSError:
                pass

        self._ld_so_cache = cache

    def find_library(self, path):
        # ctypes tries ldconfig, gcc and objdump.  If none of these are
        # present, we implement the ld-linux.so search path as described in
        # the man page.

        result = ctypes.util.find_library(path)
        if result:
            return result

        if self._ld_so_cache is None:
            self._create_ld_so_cache()

        return self._ld_so_cache.get(path)

if sys.platform == 'darwin':
    loader = MachOLibraryLoader()
elif sys.platform == 'linux2':
    loader = LinuxLibraryLoader()
else:
    loader = LibraryLoader()
load_library = loader.load_library


##################################

_lib = load_library('wiiuse')

_int_types = (c_int16, c_int32)
if hasattr(ctypes, 'c_int64'):
    # Some builds of ctypes apparently do not have c_int64
    # defined; it's a pretty good bet that these builds do not
    # have 64-bit pointers.
    _int_types += (ctypes.c_int64,)
for t in _int_types:
    if sizeof(t) == sizeof(c_size_t):
        c_ptrdiff_t = t

class c_void(Structure):
    # c_void_p is a buggy return type, converting to int, so
    # POINTER(None) == c_void_p is actually written as
    # POINTER(c_void), so it can be treated as a real pointer.
    _fields_ = [('dummy', c_int)]



WIIMOTE_LED_NONE = 0 	# wiiuse.h:61
WIIMOTE_LED_1 = 16 	# wiiuse.h:62
WIIMOTE_LED_2 = 32 	# wiiuse.h:63
WIIMOTE_LED_3 = 64 	# wiiuse.h:64
WIIMOTE_LED_4 = 128 	# wiiuse.h:65
WIIMOTE_BUTTON_TWO = 1 	# wiiuse.h:68
WIIMOTE_BUTTON_ONE = 2 	# wiiuse.h:69
WIIMOTE_BUTTON_B = 4 	# wiiuse.h:70
WIIMOTE_BUTTON_A = 8 	# wiiuse.h:71
WIIMOTE_BUTTON_MINUS = 16 	# wiiuse.h:72
WIIMOTE_BUTTON_ZACCEL_BIT6 = 32 	# wiiuse.h:73
WIIMOTE_BUTTON_ZACCEL_BIT7 = 64 	# wiiuse.h:74
WIIMOTE_BUTTON_HOME = 128 	# wiiuse.h:75
WIIMOTE_BUTTON_LEFT = 256 	# wiiuse.h:76
WIIMOTE_BUTTON_RIGHT = 512 	# wiiuse.h:77
WIIMOTE_BUTTON_DOWN = 1024 	# wiiuse.h:78
WIIMOTE_BUTTON_UP = 2048 	# wiiuse.h:79
WIIMOTE_BUTTON_PLUS = 4096 	# wiiuse.h:80
WIIMOTE_BUTTON_ZACCEL_BIT4 = 8192 	# wiiuse.h:81
WIIMOTE_BUTTON_ZACCEL_BIT5 = 16384 	# wiiuse.h:82
WIIMOTE_BUTTON_UNKNOWN = 32768 	# wiiuse.h:83
WIIMOTE_BUTTON_ALL = 8095 	# wiiuse.h:84
NUNCHUK_BUTTON_Z = 1 	# wiiuse.h:87
NUNCHUK_BUTTON_C = 2 	# wiiuse.h:88
NUNCHUK_BUTTON_ALL = 3 	# wiiuse.h:89
CLASSIC_CTRL_BUTTON_UP = 1 	# wiiuse.h:92
CLASSIC_CTRL_BUTTON_LEFT = 2 	# wiiuse.h:93
CLASSIC_CTRL_BUTTON_ZR = 4 	# wiiuse.h:94
CLASSIC_CTRL_BUTTON_X = 8 	# wiiuse.h:95
CLASSIC_CTRL_BUTTON_A = 16 	# wiiuse.h:96
CLASSIC_CTRL_BUTTON_Y = 32 	# wiiuse.h:97
CLASSIC_CTRL_BUTTON_B = 64 	# wiiuse.h:98
CLASSIC_CTRL_BUTTON_ZL = 128 	# wiiuse.h:99
CLASSIC_CTRL_BUTTON_FULL_R = 512 	# wiiuse.h:100
CLASSIC_CTRL_BUTTON_PLUS = 1024 	# wiiuse.h:101
CLASSIC_CTRL_BUTTON_HOME = 2048 	# wiiuse.h:102
CLASSIC_CTRL_BUTTON_MINUS = 4096 	# wiiuse.h:103
CLASSIC_CTRL_BUTTON_FULL_L = 8192 	# wiiuse.h:104
CLASSIC_CTRL_BUTTON_DOWN = 16384 	# wiiuse.h:105
CLASSIC_CTRL_BUTTON_RIGHT = 32768 	# wiiuse.h:106
CLASSIC_CTRL_BUTTON_ALL = 65279 	# wiiuse.h:107
GUITAR_HERO_3_BUTTON_STRUM_UP = 1 	# wiiuse.h:110
GUITAR_HERO_3_BUTTON_YELLOW = 8 	# wiiuse.h:111
GUITAR_HERO_3_BUTTON_GREEN = 16 	# wiiuse.h:112
GUITAR_HERO_3_BUTTON_BLUE = 32 	# wiiuse.h:113
GUITAR_HERO_3_BUTTON_RED = 64 	# wiiuse.h:114
GUITAR_HERO_3_BUTTON_ORANGE = 128 	# wiiuse.h:115
GUITAR_HERO_3_BUTTON_PLUS = 1024 	# wiiuse.h:116
GUITAR_HERO_3_BUTTON_MINUS = 4096 	# wiiuse.h:117
GUITAR_HERO_3_BUTTON_STRUM_DOWN = 16384 	# wiiuse.h:118
GUITAR_HERO_3_BUTTON_ALL = 65279 	# wiiuse.h:119
WIIUSE_SMOOTHING = 1 	# wiiuse.h:123
WIIUSE_CONTINUOUS = 2 	# wiiuse.h:124
WIIUSE_ORIENT_THRESH = 4 	# wiiuse.h:125
WIIUSE_INIT_FLAGS = 5 	# wiiuse.h:126
WIIUSE_ORIENT_PRECISION = 100.0 	# wiiuse.h:128
EXP_NONE = 0 	# wiiuse.h:131
EXP_NUNCHUK = 1 	# wiiuse.h:132
EXP_CLASSIC = 2 	# wiiuse.h:133
EXP_GUITAR_HERO_3 = 3 	# wiiuse.h:134
enum_ir_position_t = c_int
WIIUSE_IR_ABOVE = 0
WIIUSE_IR_BELOW = 1
ir_position_t = enum_ir_position_t 	# wiiuse.h:140
MAX_PAYLOAD = 32 	# wiiuse.h:204
byte = c_ubyte 	# wiiuse.h:215
sbyte = c_char 	# wiiuse.h:216
class struct_wiimote_t(Structure):
    __slots__ = [
    ]
struct_wiimote_t._fields_ = [
    ('_opaque_struct', c_int)
]

class struct_wiimote_t(Structure):
    __slots__ = [
    ]
struct_wiimote_t._fields_ = [
    ('_opaque_struct', c_int)
]

wiiuse_read_cb = CFUNCTYPE(None, POINTER(struct_wiimote_t), POINTER(byte), c_ushort) 	# wiiuse.h:237
class struct_vec2b_t(Structure):
    __slots__ = [
        'x',
        'y',
    ]
struct_vec2b_t._fields_ = [
    ('x', byte),
    ('y', byte),
]

vec2b_t = struct_vec2b_t 	# wiiuse.h:262
class struct_vec3b_t(Structure):
    __slots__ = [
        'x',
        'y',
        'z',
    ]
struct_vec3b_t._fields_ = [
    ('x', byte),
    ('y', byte),
    ('z', byte),
]

vec3b_t = struct_vec3b_t 	# wiiuse.h:271
class struct_vec3f_t(Structure):
    __slots__ = [
        'x',
        'y',
        'z',
    ]
struct_vec3f_t._fields_ = [
    ('x', c_float),
    ('y', c_float),
    ('z', c_float),
]

vec3f_t = struct_vec3f_t 	# wiiuse.h:280
class struct_orient_t(Structure):
    __slots__ = [
        'roll',
        'pitch',
        'yaw',
        'a_roll',
        'a_pitch',
    ]
struct_orient_t._fields_ = [
    ('roll', c_float),
    ('pitch', c_float),
    ('yaw', c_float),
    ('a_roll', c_float),
    ('a_pitch', c_float),
]

orient_t = struct_orient_t 	# wiiuse.h:296
class struct_gforce_t(Structure):
    __slots__ = [
        'x',
        'y',
        'z',
    ]
struct_gforce_t._fields_ = [
    ('x', c_float),
    ('y', c_float),
    ('z', c_float),
]

gforce_t = struct_gforce_t 	# wiiuse.h:305
class struct_accel_t(Structure):
    __slots__ = [
        'cal_zero',
        'cal_g',
        'st_roll',
        'st_pitch',
        'st_alpha',
    ]
struct_accel_t._fields_ = [
    ('cal_zero', struct_vec3b_t),
    ('cal_g', struct_vec3b_t),
    ('st_roll', c_float),
    ('st_pitch', c_float),
    ('st_alpha', c_float),
]

accel_t = struct_accel_t 	# wiiuse.h:319
class struct_ir_dot_t(Structure):
    __slots__ = [
        'visible',
        'x',
        'y',
        'rx',
        'ry',
        'order',
        'size',
    ]
struct_ir_dot_t._fields_ = [
    ('visible', byte),
    ('x', c_uint),
    ('y', c_uint),
    ('rx', c_short),
    ('ry', c_short),
    ('order', byte),
    ('size', byte),
]

ir_dot_t = struct_ir_dot_t 	# wiiuse.h:338
enum_aspect_t = c_int
WIIUSE_ASPECT_4_3 = 0
WIIUSE_ASPECT_16_9 = 1
aspect_t = enum_aspect_t 	# wiiuse.h:348
class struct_ir_t(Structure):
    __slots__ = [
        'dot',
        'num_dots',
        'aspect',
        'pos',
        'vres',
        'offset',
        'state',
        'ax',
        'ay',
        'x',
        'y',
        'distance',
        'z',
    ]
struct_ir_t._fields_ = [
    ('dot', struct_ir_dot_t * 4),
    ('num_dots', byte),
    ('aspect', aspect_t),
    ('pos', ir_position_t),
    ('vres', c_uint * 2),
    ('offset', c_int * 2),
    ('state', c_int),
    ('ax', c_int),
    ('ay', c_int),
    ('x', c_int),
    ('y', c_int),
    ('distance', c_float),
    ('z', c_float),
]

ir_t = struct_ir_t 	# wiiuse.h:375
class struct_joystick_t(Structure):
    __slots__ = [
        'max',
        'min',
        'center',
        'ang',
        'mag',
    ]
struct_joystick_t._fields_ = [
    ('max', struct_vec2b_t),
    ('min', struct_vec2b_t),
    ('center', struct_vec2b_t),
    ('ang', c_float),
    ('mag', c_float),
]

joystick_t = struct_joystick_t 	# wiiuse.h:400
class struct_nunchuk_t(Structure):
    __slots__ = [
        'accel_calib',
        'js',
        'flags',
        'btns',
        'btns_held',
        'btns_released',
        'orient_threshold',
        'accel_threshold',
        'accel',
        'orient',
        'gforce',
    ]
struct_nunchuk_t._fields_ = [
    ('accel_calib', struct_accel_t),
    ('js', struct_joystick_t),
    ('flags', POINTER(c_int)),
    ('btns', byte),
    ('btns_held', byte),
    ('btns_released', byte),
    ('orient_threshold', c_float),
    ('accel_threshold', c_int),
    ('accel', struct_vec3b_t),
    ('orient', struct_orient_t),
    ('gforce', struct_gforce_t),
]

nunchuk_t = struct_nunchuk_t 	# wiiuse.h:423
class struct_classic_ctrl_t(Structure):
    __slots__ = [
        'btns',
        'btns_held',
        'btns_released',
        'r_shoulder',
        'l_shoulder',
        'ljs',
        'rjs',
    ]
struct_classic_ctrl_t._fields_ = [
    ('btns', c_short),
    ('btns_held', c_short),
    ('btns_released', c_short),
    ('r_shoulder', c_float),
    ('l_shoulder', c_float),
    ('ljs', struct_joystick_t),
    ('rjs', struct_joystick_t),
]

classic_ctrl_t = struct_classic_ctrl_t 	# wiiuse.h:440
class struct_guitar_hero_3_t(Structure):
    __slots__ = [
        'btns',
        'btns_held',
        'btns_released',
        'whammy_bar',
        'js',
    ]
struct_guitar_hero_3_t._fields_ = [
    ('btns', c_short),
    ('btns_held', c_short),
    ('btns_released', c_short),
    ('whammy_bar', c_float),
    ('js', struct_joystick_t),
]

guitar_hero_3_t = struct_guitar_hero_3_t 	# wiiuse.h:455
class struct_u1(Union):
    __slots__ = [
        'nunchuk',
        'classic',
        'gh3',
    ]
struct_u1._fields_ = [
    ('nunchuk', struct_nunchuk_t),
    ('classic', struct_classic_ctrl_t),
    ('gh3', struct_guitar_hero_3_t),
]

expunion = struct_u1 	# wiiuse.h:462
class struct_expansion_t(Structure):
    __slots__ = [
        'type',
        'u',
    ]
struct_expansion_t._fields_ = [
    ('type', c_int),
    ('u', expunion),
]

expansion_t = struct_expansion_t 	# wiiuse.h:472
enum_win_bt_stack_t = c_int
WIIUSE_STACK_UNKNOWN = 0
WIIUSE_STACK_MS = 1
WIIUSE_STACK_BLUESOLEIL = 2
win_bt_stack_t = enum_win_bt_stack_t 	# wiiuse.h:483
class struct_wiimote_state_t(Structure):
    __slots__ = [
        'exp_ljs_ang',
        'exp_rjs_ang',
        'exp_ljs_mag',
        'exp_rjs_mag',
        'exp_btns',
        'exp_orient',
        'exp_accel',
        'exp_r_shoulder',
        'exp_l_shoulder',
        'ir_ax',
        'ir_ay',
        'ir_distance',
        'orient',
        'btns',
        'accel',
    ]
struct_wiimote_state_t._fields_ = [
    ('exp_ljs_ang', c_float),
    ('exp_rjs_ang', c_float),
    ('exp_ljs_mag', c_float),
    ('exp_rjs_mag', c_float),
    ('exp_btns', c_ushort),
    ('exp_orient', struct_orient_t),
    ('exp_accel', struct_vec3b_t),
    ('exp_r_shoulder', c_float),
    ('exp_l_shoulder', c_float),
    ('ir_ax', c_int),
    ('ir_ay', c_int),
    ('ir_distance', c_float),
    ('orient', struct_orient_t),
    ('btns', c_ushort),
    ('accel', struct_vec3b_t),
]

wiimote_state_t = struct_wiimote_state_t 	# wiiuse.h:511
enum_WIIUSE_EVENT_TYPE = c_int
WIIUSE_NONE = 0
WIIUSE_EVENT = 1
WIIUSE_STATUS = 2
WIIUSE_CONNECT = 3
WIIUSE_DISCONNECT = 4
WIIUSE_UNEXPECTED_DISCONNECT = 5
WIIUSE_READ_DATA = 6
WIIUSE_NUNCHUK_INSERTED = 7
WIIUSE_NUNCHUK_REMOVED = 8
WIIUSE_CLASSIC_CTRL_INSERTED = 9
WIIUSE_CLASSIC_CTRL_REMOVED = 10
WIIUSE_GUITAR_HERO_3_CTRL_INSERTED = 11
WIIUSE_GUITAR_HERO_3_CTRL_REMOVED = 12
WIIUSE_EVENT_TYPE = enum_WIIUSE_EVENT_TYPE 	# wiiuse.h:532
class struct_wiimote_t(Structure):
    __slots__ = [
        'unid',
        'bdaddr',
        'bdaddr_str',
        'out_sock',
        'in_sock',
        'state',
        'leds',
        'battery_level',
        'flags',
        'handshake_state',
        'read_req',
        'accel_calib',
        'exp',
        'accel',
        'orient',
        'gforce',
        'ir',
        'btns',
        'btns_held',
        'btns_released',
        'orient_threshold',
        'accel_threshold',
        'lstate',
        'event',
        'event_buf',
    ]
class struct_anon_7(Structure):
    __slots__ = [
        'b',
    ]
struct_anon_7._fields_ = [
    ('b', c_uint8 * 6),
]

bdaddr_t = struct_anon_7 	# /usr/include/bluetooth/bluetooth.h:110
class struct_read_req_t(Structure):
    __slots__ = [
    ]
struct_read_req_t._fields_ = [
    ('_opaque_struct', c_int)
]

struct_wiimote_t._fields_ = [
    ('unid', c_int),
    ('bdaddr', bdaddr_t),
    ('bdaddr_str', c_char * 18),
    ('out_sock', c_int),
    ('in_sock', c_int),
    ('state', c_int),
    ('leds', byte),
    ('battery_level', c_float),
    ('flags', c_int),
    ('handshake_state', byte),
    ('read_req', POINTER(struct_read_req_t)),
    ('accel_calib', struct_accel_t),
    ('exp', struct_expansion_t),
    ('accel', struct_vec3b_t),
    ('orient', struct_orient_t),
    ('gforce', struct_gforce_t),
    ('ir', struct_ir_t),
    ('btns', c_ushort),
    ('btns_held', c_ushort),
    ('btns_released', c_ushort),
    ('orient_threshold', c_float),
    ('accel_threshold', c_int),
    ('lstate', struct_wiimote_state_t),
    ('event', WIIUSE_EVENT_TYPE),
    ('event_buf', byte * 32),
]

wiimote = struct_wiimote_t 	# wiiuse.h:584
# wiiuse.h:612
wiiuse_version = _lib.wiiuse_version
wiiuse_version.restype = c_char_p
wiiuse_version.argtypes = []

# wiiuse.h:614
wiiuse_init = _lib.wiiuse_init
wiiuse_init.restype = POINTER(POINTER(struct_wiimote_t))
wiiuse_init.argtypes = [c_int]

# wiiuse.h:615
wiiuse_disconnected = _lib.wiiuse_disconnected
wiiuse_disconnected.restype = None
wiiuse_disconnected.argtypes = [POINTER(struct_wiimote_t)]

# wiiuse.h:616
wiiuse_cleanup = _lib.wiiuse_cleanup
wiiuse_cleanup.restype = None
wiiuse_cleanup.argtypes = [POINTER(POINTER(struct_wiimote_t)), c_int]

# wiiuse.h:617
wiiuse_rumble = _lib.wiiuse_rumble
wiiuse_rumble.restype = None
wiiuse_rumble.argtypes = [POINTER(struct_wiimote_t), c_int]

# wiiuse.h:618
wiiuse_toggle_rumble = _lib.wiiuse_toggle_rumble
wiiuse_toggle_rumble.restype = None
wiiuse_toggle_rumble.argtypes = [POINTER(struct_wiimote_t)]

# wiiuse.h:619
wiiuse_set_leds = _lib.wiiuse_set_leds
wiiuse_set_leds.restype = None
wiiuse_set_leds.argtypes = [POINTER(struct_wiimote_t), c_int]

# wiiuse.h:620
wiiuse_motion_sensing = _lib.wiiuse_motion_sensing
wiiuse_motion_sensing.restype = None
wiiuse_motion_sensing.argtypes = [POINTER(struct_wiimote_t), c_int]

# wiiuse.h:621
wiiuse_read_data = _lib.wiiuse_read_data
wiiuse_read_data.restype = c_int
wiiuse_read_data.argtypes = [POINTER(struct_wiimote_t), POINTER(byte), c_uint, c_ushort]

# wiiuse.h:622
wiiuse_write_data = _lib.wiiuse_write_data
wiiuse_write_data.restype = c_int
wiiuse_write_data.argtypes = [POINTER(struct_wiimote_t), c_uint, POINTER(byte), byte]

# wiiuse.h:623
wiiuse_status = _lib.wiiuse_status
wiiuse_status.restype = None
wiiuse_status.argtypes = [POINTER(struct_wiimote_t)]

# wiiuse.h:624
wiiuse_get_by_id = _lib.wiiuse_get_by_id
wiiuse_get_by_id.restype = POINTER(struct_wiimote_t)
wiiuse_get_by_id.argtypes = [POINTER(POINTER(struct_wiimote_t)), c_int, c_int]

# wiiuse.h:625
wiiuse_set_flags = _lib.wiiuse_set_flags
wiiuse_set_flags.restype = c_int
wiiuse_set_flags.argtypes = [POINTER(struct_wiimote_t), c_int, c_int]

# wiiuse.h:626
wiiuse_set_smooth_alpha = _lib.wiiuse_set_smooth_alpha
wiiuse_set_smooth_alpha.restype = c_float
wiiuse_set_smooth_alpha.argtypes = [POINTER(struct_wiimote_t), c_float]

# wiiuse.h:627
wiiuse_set_bluetooth_stack = _lib.wiiuse_set_bluetooth_stack
wiiuse_set_bluetooth_stack.restype = None
wiiuse_set_bluetooth_stack.argtypes = [POINTER(POINTER(struct_wiimote_t)), c_int, win_bt_stack_t]

# wiiuse.h:628
wiiuse_set_orient_threshold = _lib.wiiuse_set_orient_threshold
wiiuse_set_orient_threshold.restype = None
wiiuse_set_orient_threshold.argtypes = [POINTER(struct_wiimote_t), c_float]

# wiiuse.h:629
wiiuse_resync = _lib.wiiuse_resync
wiiuse_resync.restype = None
wiiuse_resync.argtypes = [POINTER(struct_wiimote_t)]

# wiiuse.h:630
wiiuse_set_timeout = _lib.wiiuse_set_timeout
wiiuse_set_timeout.restype = None
wiiuse_set_timeout.argtypes = [POINTER(POINTER(struct_wiimote_t)), c_int, byte, byte]

# wiiuse.h:631
wiiuse_set_accel_threshold = _lib.wiiuse_set_accel_threshold
wiiuse_set_accel_threshold.restype = None
wiiuse_set_accel_threshold.argtypes = [POINTER(struct_wiimote_t), c_int]

# wiiuse.h:634
wiiuse_find = _lib.wiiuse_find
wiiuse_find.restype = c_int
wiiuse_find.argtypes = [POINTER(POINTER(struct_wiimote_t)), c_int, c_int]

# wiiuse.h:635
wiiuse_connect = _lib.wiiuse_connect
wiiuse_connect.restype = c_int
wiiuse_connect.argtypes = [POINTER(POINTER(struct_wiimote_t)), c_int]

# wiiuse.h:636
wiiuse_disconnect = _lib.wiiuse_disconnect
wiiuse_disconnect.restype = None
wiiuse_disconnect.argtypes = [POINTER(struct_wiimote_t)]

# wiiuse.h:639
wiiuse_poll = _lib.wiiuse_poll
wiiuse_poll.restype = c_int
wiiuse_poll.argtypes = [POINTER(POINTER(struct_wiimote_t)), c_int]

# wiiuse.h:642
wiiuse_set_ir = _lib.wiiuse_set_ir
wiiuse_set_ir.restype = None
wiiuse_set_ir.argtypes = [POINTER(struct_wiimote_t), c_int]

# wiiuse.h:643
wiiuse_set_ir_vres = _lib.wiiuse_set_ir_vres
wiiuse_set_ir_vres.restype = None
wiiuse_set_ir_vres.argtypes = [POINTER(struct_wiimote_t), c_uint, c_uint]

# wiiuse.h:644
wiiuse_set_ir_position = _lib.wiiuse_set_ir_position
wiiuse_set_ir_position.restype = None
wiiuse_set_ir_position.argtypes = [POINTER(struct_wiimote_t), ir_position_t]

# wiiuse.h:645
wiiuse_set_aspect_ratio = _lib.wiiuse_set_aspect_ratio
wiiuse_set_aspect_ratio.restype = None
wiiuse_set_aspect_ratio.argtypes = [POINTER(struct_wiimote_t), aspect_t]

# wiiuse.h:646
wiiuse_set_ir_sensitivity = _lib.wiiuse_set_ir_sensitivity
wiiuse_set_ir_sensitivity.restype = None
wiiuse_set_ir_sensitivity.argtypes = [POINTER(struct_wiimote_t), c_int]

# wiiuse.h:649
wiiuse_set_nunchuk_orient_threshold = _lib.wiiuse_set_nunchuk_orient_threshold
wiiuse_set_nunchuk_orient_threshold.restype = None
wiiuse_set_nunchuk_orient_threshold.argtypes = [POINTER(struct_wiimote_t), c_float]

# wiiuse.h:650
wiiuse_set_nunchuk_accel_threshold = _lib.wiiuse_set_nunchuk_accel_threshold
wiiuse_set_nunchuk_accel_threshold.restype = None
wiiuse_set_nunchuk_accel_threshold.argtypes = [POINTER(struct_wiimote_t), c_int]


__all__ = ['WIIMOTE_LED_NONE', 'WIIMOTE_LED_1', 'WIIMOTE_LED_2',
'WIIMOTE_LED_3', 'WIIMOTE_LED_4', 'WIIMOTE_BUTTON_TWO', 'WIIMOTE_BUTTON_ONE',
'WIIMOTE_BUTTON_B', 'WIIMOTE_BUTTON_A', 'WIIMOTE_BUTTON_MINUS',
'WIIMOTE_BUTTON_ZACCEL_BIT6', 'WIIMOTE_BUTTON_ZACCEL_BIT7',
'WIIMOTE_BUTTON_HOME', 'WIIMOTE_BUTTON_LEFT', 'WIIMOTE_BUTTON_RIGHT',
'WIIMOTE_BUTTON_DOWN', 'WIIMOTE_BUTTON_UP', 'WIIMOTE_BUTTON_PLUS',
'WIIMOTE_BUTTON_ZACCEL_BIT4', 'WIIMOTE_BUTTON_ZACCEL_BIT5',
'WIIMOTE_BUTTON_UNKNOWN', 'WIIMOTE_BUTTON_ALL', 'NUNCHUK_BUTTON_Z',
'NUNCHUK_BUTTON_C', 'NUNCHUK_BUTTON_ALL', 'CLASSIC_CTRL_BUTTON_UP',
'CLASSIC_CTRL_BUTTON_LEFT', 'CLASSIC_CTRL_BUTTON_ZR', 'CLASSIC_CTRL_BUTTON_X',
'CLASSIC_CTRL_BUTTON_A', 'CLASSIC_CTRL_BUTTON_Y', 'CLASSIC_CTRL_BUTTON_B',
'CLASSIC_CTRL_BUTTON_ZL', 'CLASSIC_CTRL_BUTTON_FULL_R',
'CLASSIC_CTRL_BUTTON_PLUS', 'CLASSIC_CTRL_BUTTON_HOME',
'CLASSIC_CTRL_BUTTON_MINUS', 'CLASSIC_CTRL_BUTTON_FULL_L',
'CLASSIC_CTRL_BUTTON_DOWN', 'CLASSIC_CTRL_BUTTON_RIGHT',
'CLASSIC_CTRL_BUTTON_ALL', 'GUITAR_HERO_3_BUTTON_STRUM_UP',
'GUITAR_HERO_3_BUTTON_YELLOW', 'GUITAR_HERO_3_BUTTON_GREEN',
'GUITAR_HERO_3_BUTTON_BLUE', 'GUITAR_HERO_3_BUTTON_RED',
'GUITAR_HERO_3_BUTTON_ORANGE', 'GUITAR_HERO_3_BUTTON_PLUS',
'GUITAR_HERO_3_BUTTON_MINUS', 'GUITAR_HERO_3_BUTTON_STRUM_DOWN',
'GUITAR_HERO_3_BUTTON_ALL', 'WIIUSE_SMOOTHING', 'WIIUSE_CONTINUOUS',
'WIIUSE_ORIENT_THRESH', 'WIIUSE_INIT_FLAGS', 'WIIUSE_ORIENT_PRECISION',
'EXP_NONE', 'EXP_NUNCHUK', 'EXP_CLASSIC', 'EXP_GUITAR_HERO_3',
'ir_position_t', 'WIIUSE_IR_ABOVE', 'WIIUSE_IR_BELOW', 'MAX_PAYLOAD', 'byte',
'sbyte', 'wiiuse_read_cb', 'vec2b_t', 'vec3b_t', 'vec3f_t', 'orient_t',
'gforce_t', 'accel_t', 'ir_dot_t', 'aspect_t', 'WIIUSE_ASPECT_4_3',
'WIIUSE_ASPECT_16_9', 'ir_t', 'joystick_t', 'nunchuk_t', 'classic_ctrl_t',
'guitar_hero_3_t', 'expunion', 'expansion_t', 'win_bt_stack_t',
'WIIUSE_STACK_UNKNOWN', 'WIIUSE_STACK_MS', 'WIIUSE_STACK_BLUESOLEIL',
'wiimote_state_t', 'WIIUSE_EVENT_TYPE', 'WIIUSE_NONE', 'WIIUSE_EVENT',
'WIIUSE_STATUS', 'WIIUSE_CONNECT', 'WIIUSE_DISCONNECT',
'WIIUSE_UNEXPECTED_DISCONNECT', 'WIIUSE_READ_DATA', 'WIIUSE_NUNCHUK_INSERTED',
'WIIUSE_NUNCHUK_REMOVED', 'WIIUSE_CLASSIC_CTRL_INSERTED',
'WIIUSE_CLASSIC_CTRL_REMOVED', 'WIIUSE_GUITAR_HERO_3_CTRL_INSERTED',
'WIIUSE_GUITAR_HERO_3_CTRL_REMOVED', 'wiimote', 'wiiuse_version',
'wiiuse_init', 'wiiuse_disconnected', 'wiiuse_cleanup', 'wiiuse_rumble',
'wiiuse_toggle_rumble', 'wiiuse_set_leds', 'wiiuse_motion_sensing',
'wiiuse_read_data', 'wiiuse_write_data', 'wiiuse_status', 'wiiuse_get_by_id',
'wiiuse_set_flags', 'wiiuse_set_smooth_alpha', 'wiiuse_set_bluetooth_stack',
'wiiuse_set_orient_threshold', 'wiiuse_resync', 'wiiuse_set_timeout',
'wiiuse_set_accel_threshold', 'wiiuse_find', 'wiiuse_connect',
'wiiuse_disconnect', 'wiiuse_poll', 'wiiuse_set_ir', 'wiiuse_set_ir_vres',
'wiiuse_set_ir_position', 'wiiuse_set_aspect_ratio',
'wiiuse_set_ir_sensitivity', 'wiiuse_set_nunchuk_orient_threshold',
'wiiuse_set_nunchuk_accel_threshold']
