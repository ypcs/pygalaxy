import sys
import struct

import daemon
import socketipc

# Become server, wait for commands

print "Starting WiiMote driver daemon"

server = socketipc.IPCServer(port=31307)
while True:
    connection = server.accept()
    while True:
        msg = connection.receive()
        print msg
