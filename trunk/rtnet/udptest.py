import sys
import random
import socket
import binascii

BindRequest = '0001'

def GenTranID():
    a =''
    for i in xrange(32):
        a+=random.choice('0123456789ABCDEF')
    #return binascii.a2b_hex(a)
    return a

def round(host, port, payload):
    UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tranID = GenTranID()
    data = BindRequest + ('%#04d' % len(payload)) + tranID + payload
    print data
    bindata = binascii.a2b_hex(data)
    print len(bindata)
    UDPSock.sendto(bindata, (host, port))
    buf, addr = UDPSock.recvfrom(2048)
    print buf, addr

UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
if sys.argv[1] == 'server':
    UDPSock.bind(('localhost', 50000))
    data, addr = UDPSock.recvfrom(1024)
    print binascii.b2a_hex(data), addr
if sys.argv[1] == 'client':
    round('stunserver.org', 3478, '')


