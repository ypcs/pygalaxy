import sys
import struct
import ctypes

import daemon
import socketipc
import rencode
import wiiuse

wm = wiiuse.wiiuse_init(1)
print wm
fnd = wiiuse.wiiuse_find(wm, 1, 5)
print fnd
cn = wiiuse.wiiuse_connect(wm, 1)
print cn

sys.exit()

_wiiuse = None

if sys.platform[:3] == 'win':
    _wiiuse = ctypes.cdll.wiiuse
elif sys.platform == 'linux2':
    _wiiuse = ctypes.cdll.LoadLibrary('libwiiuse.so')
elif sys.platform == 'darwin':
    _wiiuse = ctypes.cdll.LoadLibrary('libwiiuse.so')

print _wiiuse

_wm = _wiiuse.wiiuse_init(1)
print _wm

found = _wiiuse.wiiuse_find(_wm, 1, 5)
print found


# Become server, wait for commands

def respond(cmd, data):
    if cmd == 'HELLO':
        return 'HELLOTOYOU'
    return 'UNKNOWN'

def start():
    print "Starting WiiMote driver daemon"

    server = socketipc.IPCServer(port=31307)

    while True:
        connection = server.accept()
        try:
            while True:
                msg = rencode.loads(connection.receive())
                cmd = msg[0]
                data = msg[1:]
                print 'command = ', cmd
                resp = respond(cmd, data)
                print 'response = ', resp
                connection.send(rencode.dumps(resp))
        except RuntimeError, e:
            # They closed the connection, keep going
            pass

if __name__ == '__main__':
    start()
