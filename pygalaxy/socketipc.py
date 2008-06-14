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
