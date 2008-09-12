'''Distributed Application State

This module allows your Python programs to easily have a persistent
global distributed state.  This state can be used to store things like
number of users, game high scores, message of the day from the author,
etc.

'''

import exceptions
import urllib
import md5
import pickle
import codecs

SERVER = 'localhost:8080'
APPID = 'testapp'
key = None

class UnexpectedError(exceptions.Exception): pass
class NotInitialized(exceptions.Exception): pass
class NoStateSet(exceptions.Exception): pass
class UpdateFailed(exceptions.Exception): pass

# Initialize variables

def init(appid='testapp'):
    '''Initialize connection to Google App Engine

    Before using any other functions you must call init(appid='...')
    with the id of your application.  Your application id must be
    unique and is shared between all instances of your application
    that are running.

    Recommended naming scheme:
    (your name OR your domain name) PLUS application name PLUS version

    So one of my hypothetical application ids is:
    NathanWhitehead+AstroMaxBlaster+0.2

    '''
    global APPID
    APPID = appid
    _get_key()

def _get_key():
    global key
    resp = _communicate('getkey', {'appid' : APPID})
    key = resp[0].strip()
    if key == '':
        raise UnexpectedError


# Utility functions

def hash(x):
    return md5.new(x).hexdigest()

def serialize(x): 
    return pickle.dumps(x)

def unserialize(s):
    return pickle.loads(s)

def _communicate(action, args, method='get'):
    url = 'http://' + SERVER + '/' + action
    if method == 'get':
        url += '?' + urllib.urlencode(args)
        conn = urllib.urlopen(url)
    elif method == 'post':
        conn = urllib.urlopen(url, urllib.urlencode(args))
    else:
        raise Exception
    resp = conn.readlines()
    if len(resp) > 0:
        if resp[0][0:5] == 'ERROR':
            raise Exception
    return resp

# Direct access to persistent global state of application

def get_state():
    '''Retrieve the most current application state

    Will raise NotInitialized if there is no connection to Google App
    Engine.  Will raise NoStateSet if there has not been any calls to
    set_state().  May raise other various exceptions if the connection
    times out, if the server reports a problem, or if the application
    state data gets corrupted.

    The return value will be Python data.

    '''
    if key is None: raise NotInitialized
    resp = _communicate('get', {'key' : key})
    if len(resp) > 0:
        return unserialize("".join(resp))
    raise NoStateSet

def set_state(state):
    '''Set the current application state

    This function accepts any Python data for the state that is not
    too big.  The size of the data when serialized and encoded is
    limited to 100K.

    Note that this function does not care what the previous state
    of the application was.  Other copies of the application may
    have already updated the state by the time you call set_state().
    It is recommended to use update_state() or the state update
    tools rather than this function.

    Will raise NotInitialized if there is no connection to Google App
    Engine.  May raise other various exceptions if the connection
    times out, if the server reports a problem, or if the application
    state data gets corrupted.

    '''
    if key is None: raise NotInitialized
    cnt = serialize(state)
    resp = _communicate('set', {
            'key' : key, 
            'content' : cnt}, 
                        method='post')
    if len(resp) == 0:
        raise UnexpectedError
    if resp[0][:2] == 'OK':
        return
    raise UnexpectedError

def update_state(oldhash, newstate):
    '''Update the current application state

    This function checks that the current state matches the given hash
    value, then updates the state to the new value.  The size of the
    new state data when serialized and encoded is limited to 100K.
    If the hash value you give does not match the hash of the current
    state this function will raise UpdateFailed.

    To calculate the hash of a state s, use: hash(serialize(s))

    Will raise NotInitialized if there is no connection to Google App
    Engine.  May raise other various exceptions if the connection
    times out, if the server reports a problem, or if the application
    state data gets corrupted.

    '''
    if key is None: raise NotInitialized
    resp = _communicate('update', {
            'key' : key, 
            'old' : oldhash, 
            'content' : serialize(newstate)}, 
                        method='post')
    if len(resp) == 0:
        raise UnexpectedError
    if resp[0][:2] == 'OK':
        return
    if resp[0][:4] == 'FAIL':
        raise UpdateFailed
    raise UnexpectedError

if __name__ == '__main__':
    init('NathanWhitehead+testapp+1')
    set_state('booya')
    print get_state()
    set_state('blah32322')
    print get_state()
    update_state(hash(serialize('blah32322')), 'newishstate')
    print get_state()

    import marshal
    f = open('testhash', 'wb')
    h = 'secretkey'
    marshal.dump(h, f)
    for i in range(10):
        for j in range(100000):
            h = hash(h)
            marshal.dump(h, f)
        print i
    f.close()

    import random
    for i in range(10000):
        l = i * 1000
        lst = [random.randint(0, 10000) for j in range(l)]
        set_state(lst)
        print len(get_state()), len(serialize(lst))
