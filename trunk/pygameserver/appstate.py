'''Distributed Application Shared State

This module allows your Python programs to easily have a persistent
global distributed shared state.  This state can be used to store
things like number of users, game high scores, message of the day from
the author, etc.  The state has an interface like a dictionary with
some additional synchronization functionality and some restrictions.
This module connects to a server on the Google App Engine to store and
manage data.

'''

import exceptions
import urllib
import md5
import pickle

#SERVER = 'localhost:8080' # for the dev server
SERVER = 'pygameserver.appspot.com'

class UnexpectedError(exceptions.Exception): pass
class UpdateFailedError(exceptions.Exception): pass


# Utility functions

def hash(x):
    return md5.new(x).hexdigest()

def serialize(x): 
    return pickle.dumps(x)

def unserialize(s):
    return pickle.loads(s)

def length_data(x):
    return len(serialize(x))

def hash_value(x):
    return hash(serialize(x))

def _communicate(action, args, method='get'):
    url = 'http://' + SERVER + '/' + action
    if method == 'get':
        url += '?' + urllib.urlencode(args)
        conn = urllib.urlopen(url)
    elif method == 'post':
        conn = urllib.urlopen(url, urllib.urlencode(args))
    else:
        raise Exception
    return conn.readlines()


# Main class

class DistributedState():
    '''Distributed Persistent Data Store'''
    def __init__(self, appid=None):
        '''Create new distributed state object

        Each application must have a unique id.  Your appid is shared
        between all instances of your application that are running.

        Recommended naming scheme for appids:
        (your name OR your domain name) PLUS application name

        So one of my hypothetical application ids is:
        NathanWhitehead+AstroMaxBlaster
        
        '''
        self.appid = appid

    # Direct access to persistent global state of application

    def __getitem__(self, key):
        '''Retrieve the most current value for the given key

        Will raise KeyError if there has not been any calls to
        __setitem__().  May raise other various exceptions if the
        connection times out, if the server reports a problem, or if
        the application data gets corrupted.
        
        The return value will be Python data.

        '''
        resp = _communicate('get', {'appid' : self.appid, 'key' : key})
        if len(resp) > 0:
            if resp[0][:5] == 'ERROR':
                raise KeyError
            return unserialize("".join(resp))
        raise UnexpectedError

    def keys(self):
        '''Get list of all keys in the state

        May raise various exceptions if the connection times out, if
        the server reports a problem, or if the application data gets
        corrupted.

        '''
        resp = _communicate('keys', {'appid' : self.appid})
        if len(resp) > 0:
            if resp[0][:5] == 'ERROR':
                raise KeyError
            return unserialize(''.join(resp))
        raise UnexpectedError

    def __setitem__(self, key, value):
        '''Set the value for a given key
        
        This function accepts any Python data for the value that is not
        too big.  The size of the data when serialized and encoded is
        limited to 100K.
        
        Note that this function does not care what the previous state
        of the application was.  Other copies of the application may
        have already updated the value by the time you call set().  It
        is recommended to use update() rather than this function.
        
        May raise various exceptions if the connection times out, if
        the server reports a problem, or if the application state data
        gets corrupted.

        '''
        cnt = serialize(value)
        resp = _communicate('set', {
                'appid' : self.appid,
                'key' : key, 
                'content' : cnt}, 
                            method='post')
        if len(resp) == 0:
            raise UnexpectedError
        if resp[0][:2] == 'OK':
            return
        raise UnexpectedError

    def __delitem__(self, key):
        '''Delete the value for a given key
        
        May raise various exceptions if the connection times out, if
        the server reports a problem, or if the application state data
        gets corrupted.

        '''
        resp = _communicate('del', {
                'appid' : self.appid,
                'key' : key, },
                            method='post')
        if len(resp) == 0:
            raise UnexpectedError
        if resp[0][:2] == 'OK':
            return
        raise UnexpectedError

    # Synchronized access functions

    def update(self, key, oldhash, value):
        '''Update the value associated with a given key

        This function checks that the current value matches the given
        hash value, then updates the value associated with the key.
        The size of the new value when serialized and encoded is
        limited to 100K.  If the hash value you give does not match
        the hash of the current value, this function will raise
        UpdateFailedError.
        
        To calculate the hash of a value v, use: hash(serialize(v))
        (or hash_value(v))
        
        May raise various exceptions if the connection times out, if
        the server reports a problem, or if the application state data
        gets corrupted.

        '''
        resp = _communicate('update', {
                'appid' : self.appid,
                'key' : key, 
                'old' : oldhash, 
                'content' : serialize(value)}, 
                            method='post')
        if len(resp) == 0:
            raise UnexpectedError
        if resp[0][:2] == 'OK':
            return
        if resp[0][:4] == 'FAIL':
            raise UpdateFailedError
        raise UnexpectedError

    def apply_op(self, key, func, create=False, defaultvalue=None):
        '''Apply a function to the value stored at a key

        The function func must take one argument and return one
        argument.  The state will be updated to reflect applying the
        function to the value stored at the given key.  The function
        may be called more than once if the value is being changed
        by other instances of the application.  To make debugging
        easier, try to limit side effects in the function.

        If the key has no value, and create is false, will raise
        a KeyError exception.  If create is true, the function
        will apply to the given defaultvalue.

        This function attempts to guarantee that even if many
        instances are simultaneously attempting to update the same
        value in the state, all the functions will be applied in some
        order.  For example, if the value is a list and the operation
        is inserting an element into the list, using this method will
        guarantee that all elements will be inserted.

        This function cannot guarantee that two instances will not
        simultaneously create a new value.  If you need absolute
        consistency in this case, create default values in the state
        before distributing multiple instances of the application.

        '''
        try:
            old = self[key]
            new = func(old)
            oldhash = hash_value(old)
            self.update(key, hash_value(old), new)
        except UpdateFailedError:
            self.apply_op(key, func, create=create, defaultvalue=defaultvalue)
        except KeyError:
            if create:
                self[key] = func(defaultvalue)
            else:
                raise KeyError
        

if __name__ == '__main__':
    shlf = DistributedState('NathanWhitehead+testapp+1')
    shlf['blah'] = 'foobar'
    print shlf['blah']
    shlf['testing'] = [1,2,3,'hello\nto you']
    print shlf['testing']
    shlf[1] = 3
    print shlf[1]
    shlf[1] += 2
    print shlf[1]
    shlf['message'] = 'secret'
    shlf.update('message', hash_value('secret'), 'public')
    print shlf['message']
    try:
        shlf.update('message', hash_value('secret'), 'public2')
    except:
        print "update failed, as it should"
    print shlf['message']
    del shlf['message']
    try:
        print shlf['message']
    except:
        print "message does not exist, as it should"
    shlf['thisisakey'] = None
    keys = shlf.keys()
    print keys
    print shlf[keys[2]]
