import sys
import random
import socket
import struct
import time

BIND_REQUEST = '\x00\x01'
CHANGE_REQUEST = '\x00\x03'
CHANGE_REQUEST_FULL = CHANGE_REQUEST + '\x00\x04\x00\x00\x00\x06'
CHANGE_REQUEST_IP = CHANGE_REQUEST + '\x00\x04\x00\x00\x00\x04'

MAPPED_ADDRESS = 1
SOURCE_ADDRESS = 4
CHANGED_ADDRESS = 5

PORT = 9350


def GenTranID():
    '''Generate 16 byte random transaction ID bytestring'''
    r = ''
    for i in range(16): 
        r += struct.pack('!B', random.randint(0, 255))
    return r

def parse_tlv(d):
    (t, l) = struct.unpack('!HH', d[0:4])
    v = d[4:4 + l]
    return (t, l, v)

def make_dotted_address(a):
    addr = struct.unpack('!4B', a)
    return '.'.join([str(x) for x in addr])

def parse_resp(d):
    '''Parse STUN response data'''
    (type, l) = struct.unpack('!HH', d[:4])
    tid = d[4:20]
    v = d[20:]
    res = {'type':type, 'id':tid}
    while len(v) > 0:
        (t, l2, v2) = parse_tlv(v)
        # Try to interpret value
        if t in [MAPPED_ADDRESS, SOURCE_ADDRESS, CHANGED_ADDRESS]:
            v2 = {'port':struct.unpack('!H', v2[2:4])[0],
                  'address':make_dotted_address(v2[4:8])}
        res[t] = v2
        v = v[4 + l2:]
    return res

def stun_req(sock, host, port, payload):
    tranID = GenTranID()
    data = BIND_REQUEST + struct.pack('!H', len(payload)) + tranID + payload
    print data.encode('hex')
    sock.sendto(data, (host, port))
    buf, addr = sock.recvfrom(2048)
    return parse_resp(buf)

socket.setdefaulttimeout(60.0)
osock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
isock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
if sys.argv[1] == 'stun':
    server = 'stunserver.org'
    osock.bind(('', PORT))
    st = stun_req(osock, server, 3478, '')
    changedIP = st[5]['address']
    changedPort = st[5]['port']
    print st[1]['address'], st[1]['port']
    sys.exit()
if sys.argv[1] == 'stun2':
    server = 'stunserver.org'
    osock.bind(('', PORT))
    st = stun_req(osock, server, 3478, CHANGE_REQUEST_FULL)
    print st[1]['address'], st[1]['port']
    sys.exit()
if sys.argv[1] == 'stun3':
    server = 'stunserver.org'
    osock.bind(('', PORT))
    st = stun_req(osock, server, 3478, '')
    changedIP = st[5]['address']
    changedPort = st[5]['port']
    print st[1]['address'], st[1]['port']
    osock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    st = stun_req(osock, changedIP, changedPort, '')
    print st[1]['address'], st[1]['port']
    sys.exit()
if sys.argv[1] == 'stun4':
    server = 'stunserver.org'
    osock.bind(('', PORT))
    st = stun_req(osock, server, 3478, '')
    changedIP = st[5]['address']
    changedPort = st[5]['port']
    print st[1]['address'], st[1]['port']
    osock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    st = stun_req(osock, server, 3478, CHANGE_REQUEST_IP)
    print st[1]['address'], st[1]['port']
    sys.exit()
if sys.argv[1] == 'stun_wait':
    server = 'stunserver.org'
    osock.bind(('', PORT))
    st = stun_req(osock, server, 3478, '')
    print st[1]['address'], st[1]['port']
    while True:
        data, addr = osock.recvfrom(1024)
        print 'Data from %s:%d = %s' % (addr[0], addr[1], data.encode('hex'))
        osock.sendto('response', addr)
        print 'Sent response'
    sys.exit()
if sys.argv[1] == 'stun_punch_wait':
    server = 'stunserver.org'
    osock.bind(('', PORT))
    st = stun_req(osock, server, 3478, '')
    print st[1]['address'], st[1]['port']
    host = (sys.argv[2], int(sys.argv[3]))
    print 'Punching ', host
    osock.sendto('punch', host)
    print 'Waiting'
    while True:
        data, addr = osock.recvfrom(1024)
        print 'Data from %s:%d = %s' % (addr[0], addr[1], data.encode('hex'))
        osock.sendto('response', addr)
        print 'Sent response'
    sys.exit()
if sys.argv[1] == 'server':
    isock.bind(('', PORT))
    if len(sys.argv) > 2:
        isock.sendto('punch', (sys.argv[2], int(sys.argv[3])))
    while True:
        data, addr = isock.recvfrom(1024)
        print 'Data from %s:%d = %s' % (addr[0], addr[1], data.encode('hex'))
        isock.sendto('response', addr)
        print 'Sent response'
    sys.exit()
if sys.argv[1] == 'client':
    host = (sys.argv[2], int(sys.argv[3]))
    msg = 'hellomsg'
    osock.sendto(msg, host)
    print 'Data sent'
    data, addr = osock.recvfrom(1024)
    print 'Response from %s:%d = %s' % (addr[0], addr[1], data.encode('hex'))
    sys.exit()



# Sleep for a few seconds to allow user to switch windows
time.sleep(float(sys.argv[1]))
# Now send out two probes to address given in command line
host = (sys.argv[2], int(sys.argv[3]))
print host
UDPSock.sendto('response1', host)
UDPSock.sendto('response2', host)
print 'sent probes, waiting for reply'
# Bind ourselves to correct port number
# This is meaningless except for NAT-less
UDPSock.bind(('localhost', PORT))
data, addr = UDPSock.recvfrom(1024)
print 'Got: ', data.encode('hex')
