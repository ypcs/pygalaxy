"""
Socket Inter-Process Communication module
Copyright 2008, Nathan Whitehead
Released under the LGPL

Use this module to communicate between processes over a predetermined
port on the local computer.  Messages will be delivered in a FIFO fashion.
Communication is by a client-server model.  One process is the server
that runs and waits for connections.  The other process is the client.

Client does this:

client = socketipc.IPCClient(port=10000)
client.send("Hello to the server")

Server does this:

server = socketipc.IPCServer(port=10000)
connection = server.accept() # wait for client to connect
msg = connection.receive()

TIPS
You, the user of this module, must figure out who is saying what.  In
other words, don't have the client and server confused about who should
be sending the next message.  Have a protocol.

The server must start first, then do an accept() to wait for the client.
The client cannot wait for the server to start.

The server can handle multiple connections at once, just do an accept()
whenever you want to allow a new connection from a client.  You must
have a protocol to determine when a client connects and who talks when.
accept() blocks until a connection is made.  There are no provisions
for using select() to wait until someone says something.

When interfacing with other languages:
Messages are delimited by length.  First 4 bytes are the length of the
message to follow, followed by the message.
"""

import socket
import struct

default_socket_port = 15008

def sock_send(sock, msg):
    totalsent = 0
    while totalsent < len(msg):
        sent = sock.send(msg[totalsent:])
        if sent == 0:
            raise RuntimeError, "socket connection broken"
        totalsent += sent

def sock_receive(sock, l):
    msg = ''
    while len(msg) < l:
        chunk = sock.recv(l - len(msg))
        if chunk == '':
            raise RuntimeError, "socket connection broken"
        msg += chunk
    return msg

def msg_send(sock, msg):
    sock_send(sock, struct.pack('I', len(msg)))
    sock_send(sock, msg)

def msg_receive(sock):
    ln = struct.unpack('I', sock_receive(sock, struct.calcsize('I')))
    return sock_receive(sock, ln[0])

class IPCClient:
    '''Simple inter-process communication (IPC) client'''
    def __init__(self, port=default_socket_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('localhost', port))
    def send(self, msg): msg_send(self.sock, msg)
    def receive(self): return msg_receive(self.sock)

class IPCServerClient:
    '''Represents a client socket connection within a server'''
    def __init__(self, sock):
        self.sock = sock
    def send(self, msg): msg_send(self.sock, msg)
    def receive(self): return msg_receive(self.sock)

class IPCServer:
    '''Simple inter-process communication (IPC) client'''
    def __init__(self, port=default_socket_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('localhost', port))
        self.sock.listen(5)
    def accept(self):
        (clientsocket, address) = self.sock.accept()
        return IPCServerClient(clientsocket)
