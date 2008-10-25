import sys
import struct
import ctypes

import daemon
import socketipc
import rencode

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
