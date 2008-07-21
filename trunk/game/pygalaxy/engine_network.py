import sys
import select
import socket
import pickle

host = None
port = 50001
sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sck.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
frame = 0
our_id = 0
num_players = 0
clients = []

# start_multiplayer(number_players=2)  we are server, wait for two players total including us
# server is always #0
# start_multiplayer(server='192.168.0.1', id=1)  we are client, give server name
# we are number #1 out of 2
def multiplayer_start(server=None, number_players=2, id=0):
    global our_id
    global num_players
    global host
    global sck
    num_players = number_players
    if server == None:
        our_id = 0
        # We are server, start listening for connections
        sck.bind(('', port))
        sck.listen(number_players * 2)
    else:
        our_id = id
        host = server
        sck.connect((host, port))

# format for packets is client number, frame number, data
# (pickled)
# response is pickled [frame, [data1, data2, ...]]
def multiplayer_tick(data):
    global frame
    global inputs
    global clients
    if our_id == 0:
        # SERVER
        frame_data = [None for i in range(num_players)]
        frame_data[0] = data
        num_responded = 0
        while num_responded < num_players - 1:
            inputready, outputready, exceptready = select.select([sck] + clients,[],[])
            for s in inputready:
                if s == sck:
                    client, address = sck.accept()
                    clients.append(client)
                else:
                    cdatastr = s.recv(1024)
                    cdata = pickle.loads(cdatastr)
                    #print our_id, 'recv', cdata
                    assert frame == cdata[1]
                    frame_data[cdata[0]] = cdata[2]
                    num_responded += 1
        # Now respond with full list of data for all clients
        resdatastr = pickle.dumps([frame, frame_data])
        for c in clients:
            c.send(resdatastr)
            #print our_id, 'send', [frame, frame_data]
        frame += 1
        return frame_data
    else:
        # CLIENT
        datastr = pickle.dumps([our_id, frame, data])
        sck.send(datastr)
        #print our_id, 'send', [our_id, frame, data]
        resdatastr = sck.recv(1024)
        resdata = pickle.loads(resdatastr)
        #print our_id, 'recv', resdata
        assert frame == resdata[0]
        frame += 1
        return resdata[1]
