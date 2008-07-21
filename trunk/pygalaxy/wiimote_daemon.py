import sys
import struct
import pickle

import socketipc
import daemon

print "Starting WiiMote connection daemon"

server = socketipc.IPCServer(port=15008)
while True:
    connection = server.accept()
    while True:
        msg = connection.receive()
        print msg
