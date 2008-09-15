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
import urllib2
import cookielib
import socket
import logging
import md5
import sys
import os
import rencode

import prpc

class SizeError(Exception): pass
class DataUnchangedError(Exception): pass
class DuplicateError(Exception): pass
class PermissionError(Exception): pass
class UnjoinedError(Exception): pass
class LoginError(Exception): pass
class AppIdError(Exception): pass
class UpdateFailedError(Exception): pass
class UnexpectedError(Exception): pass

ANY = 0
ADMIN_ONLY = 1
AUTHORIZED_ONLY = 2
UNBANNED_ONLY = 3


# Utility functions

def hash(x):
    return md5.new(x).hexdigest()

def serialize(x): 
    return rencode.dumps(x)

def unserialize(s):
    return rencode.loads(s)

def length_data(x):
    return len(serialize(x))

def hash_value(x):
    return hash(serialize(x))

# Main class

class DistributedState():
    '''Distributed Persistent Data Store'''
    def __init__(self, server='pygameserver.appspot.com'):
        '''Create new connection to server

        This function establishes a connection to Google App Engine.
        Server will normally be pygameserver.appspot.com
        
        '''
        self.appid = None
        self.appkey = None
        self.serv = prpc.PRPC(hostname=server)
        self.joined = False

    def join(self, appid = None):
        '''Join an existing application

        Establishes connection to the pygame application distributed
        state using application id (appid).  Will raise AppIdError if
        the appid does not exist.

        '''
        if appid is not None: self.appid = appid
        self.appkey = self.serv.send('getapp', self.appid)
        if self.appkey[:10] == '!!!!!appid': raise AppIdError
        if self.appkey[:5] == '!!!!!': raise UnexpectedError
        self.joined = True

    # Administrative functions

    def version(self):
        '''Get version string returned by server'''
        resp = self.serv.send('version')
        if resp[:5] == '!!!!!': raise UnexpectedError
        return resp

    def login(self, email, password):
        '''Login to Google account

        Calling this function logs into a Google account with the
        given email and password.  Will raise LoginError if there is a
        problem.  Check the 'reasons' field of the exception to see
        why the login was denied if there was an exception raised.

        Your account must already exist and be in good standing. To
        create new accounts or manage problems with your existing
        account, go to:
        
        https://www.google.com/accounts/Login

        If you have been locked out of your account for attempting to
        login too quickly with incorrect passwords, unlock the account
        by going to:
        
        https://www.google.com/accounts/DisplayUnlockCaptcha

        '''
        try:
            self.serv.login(email, password)
        except prpc.ClientLoginError, e:
            e2 = LoginError()
            e2.reason = e.reason
            raise e2

    def new_app(self, appid, readmode=ANY, writemode=ANY):
        '''Register a new application

        You must be logged in.  Your account will be the admin
        account for the application.  After creating the app,
        joins it.

        Each application must have a unique id.  Your appid is shared
        between all instances of your application that are running.

        Recommended naming scheme for appids:
        (your name OR your domain name) PLUS application name

        So one of my hypothetical application ids is:
        NathanWhitehead+AstroMaxBlaster

        The readmode and writemode arguments indicate how permissions
        work.  They can be the following values:

        ANY - means anyone can do the operation, even if not logged in

        ADMIN_ONLY - only the admin can do the operation

        AUTHORIZED_ONLY - only users that have been explicitly
        authorized can do the operation

        UNBANNED_ONLY - any logged in user that has not been banned
        can do the operation

        For example, setting readmode=ANY and writemode=ADMIN_ONLY
        means that anyone can read the application state, but only the
        admin can make any changes.  You cannot change readmode or
        writemode once the application has been registered.  Only the
        admin can authorize users or ban them.

        Will raise PermissionError if you are not logged in.  Will raise
        DuplicateError if the application id is already used.

        '''
        self.appid = appid
        resp = self.serv.send('registerapp', appid, readmode, writemode)
        if resp[:9] == '!!!!!must': raise PermissionError
        if resp[:10] == '!!!!!appid': raise DuplicateError
        if resp[:5] == '!!!!!': raise UnexpectedError
        print resp
        self.join()

    def delete_app(self):
        '''Delete the application

        You must be logged in and have joined the application.  Your
        account muse be the admin account for the application.  Cannot
        be undone.

        Will raise PermissionError if you are not logged in and the
        application admin.  Will raise UnjoinedError if you have not
        joined the application.

        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('deleteapp', self.appkey)
        if resp[:8] == '!!!!!you': raise PermissionError
        if resp[:9] == '!!!!!muse': raise PermissionError
        if resp[:5] == '!!!!!': raise UnexpectedError
        self.appkey = None
        self.appid = None
        self.joined = False

    def authorize(self, email):
        '''Authorize a user
        
        You must be logged in as administrator and have joined the
        application.  Note that in some read and write modes,
        authorizing users has no effect.

        Raises UnjoinedError if you haven't joined an application
        state.  Raises DuplicateError if the email has already been
        authorized.  Raises PermissionError if you are not logged in
        as admin.
        
        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('authorize', self.appkey, email)
        if resp[:12] == '!!!!!already': raise DuplicateError
        if resp[:8] == '!!!!!you': raise PermissionError
        if resp[:5] == '!!!!!': raise UnexpectedError
        
    def unauthorize(self, email):
        '''Unauthorize a user
        
        You must be logged in as administrator and have joined the
        application.  Note that in some read and write modes,
        authorizing users has no effect.

        Raises UnjoinedError if you haven't joined an application
        state.  Raises DuplicateError if the email is not authorized.
        Raises PermissionError if you are not logged in as admin.
        
        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('unauthorize', self.appkey, email)
        if resp[:8] == '!!!!!not': raise DuplicateError
        if resp[:8] == '!!!!!you': raise PermissionError
        if resp[:5] == '!!!!!': raise UnexpectedError
        
    def ban(self, email):
        '''Ban a user
        
        You must be logged in as administrator and have joined the
        application.  Note that in some read and write modes,
        banning users has no effect.

        Raises UnjoinedError if you haven't joined an application
        state.  Raises DuplicateError if the email has already been
        banned.  Raises PermissionError if you are not logged in as
        admin.
        
        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('ban', self.appkey, email)
        if resp[:12] == '!!!!!already': raise DuplicateError
        if resp[:8] == '!!!!!you': raise PermissionError
        if resp[:5] == '!!!!!': raise UnexpectedError

    def unban(self, email):
        '''Unban a user
        
        You must be logged in as administrator and have joined the
        application.  Note that in some read and write modes,
        banning users has no effect.

        Raises UnjoinedError if you haven't joined an application
        state.  Raises DuplicateError if the email is not banned.
        Raises PermissionError if you are not logged in as admin.
        
        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('unban', self.appkey, email)
        print resp
        if resp[:8] == '!!!!!not': raise DuplicateError
        if resp[:8] == '!!!!!you': raise PermissionError
        if resp[:5] == '!!!!!': raise UnexpectedError

    # Direct access to persistent global state of application

    def __getitem__(self, key):
        '''Retrieve the most current value for the given key

        Will raise KeyError if there have not been any calls setting
        the value of the key.  Will raise PermissionError if you do
        not have permission to read the key value.  May raise other
        various exceptions if the connection times out, if the server
        reports a problem, or if the application data gets corrupted.
        
        The return value will be Python data.

        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('get', self.appkey, key)
        if resp[:7] == '!!!!!no': raise PermissionError
        if resp[:8] == '!!!!!key': raise KeyError
        if resp[:5] == '!!!!!': raise UnexpectedError
        return unserialize(resp)
        

    def get_if_changed(self, key, oldhash):
        '''Retrieve the value for the given key if it has changed

        You pass a key and the hash value that you already know about,
        and the server will either send you the most current value
        that has a different hash, or raise DataUnchangedError if
        there are no changes to report.

        Will raise KeyError if there have not been any calls setting
        the value of the key.  Will raise PermissionError if you do
        not have permission to read the key value.  May raise other
        various exceptions if the connection times out, if the server
        reports a problem, or if the application data gets corrupted.
        
        The return value will be Python data.

        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('getifchanged', self.appkey, key, oldhash)
        if resp[:7] == '!!!!!no': raise PermissionError
        if resp[:8] == '!!!!!key': raise KeyError
        if resp[:9] == '!!!!!hash': raise DataUnchangedError
        if resp[:5] == '!!!!!': raise UnexpectedError
        return unserialize(resp)

    def __setitem__(self, key, value):
        '''Set the value for a given key
        
        This function accepts any Python data for the value that is not
        too big.  The size of the data when serialized and encoded is
        limited to 20K.
        
        Note that this function does not care what the previous state
        of the application was.  Other copies of the application may
        have already updated the value by the time you call set().  It
        is recommended to use update() rather than this function.
        
        Will raise UnjoinedError if you have not joined the
        application.  Will raise PermissionError if you do not have
        permission to write to the state.  Will raise SizeError if the
        value is too big.  May raise various exceptions if the
        connection times out, if the server reports a problem, or if
        the application state data gets corrupted.

        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('set', self.appkey, key, serialize(value))
        if resp[:7] == '!!!!!no': raise PermissionError
        if resp[:8] == '!!!!!too': raise SizeError
        if resp[:5] == '!!!!!': raise UnexpectedError

    def __delitem__(self, key):
        '''Delete the value for a given key

        Will raise PermissionError if you do not have permission to
        write to the state.  Will raise KeyError if the key has no
        value to delete.
        
        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('del', self.appkey, key)
        if resp[:7] == '!!!!!no': raise PermissionError
        if resp[:8] == '!!!!!key': raise KeyError
        if resp[:5] == '!!!!!': raise UnexpectedError

    # Synchronized access functions

    def update(self, key, oldhash, value):
        '''Update the value associated with a given key

        This function checks that the current value matches the given
        hash value, then updates the value associated with the key.
        The size of the new value when serialized and encoded is
        limited to 20K.  If the hash value you give does not match
        the hash of the current value, this function will raise
        UpdateFailedError.
        
        To calculate the hash of a value v, use: hash_value(v)

        '''
        if not self.joined: raise UnjoinedError
        resp = self.serv.send('update', self.appkey, key, oldhash, serialize(value))
        if resp[:12] == '!!!!!no perm': raise PermissionError
        if resp[:8] == '!!!!!too': raise SizeError
        if resp[:11] == '!!!!!no val': raise KeyError
        if resp[:9] == '!!!!!hash': raise UpdateFailedError
        if resp[:5] == '!!!!!': raise UnexpectedError

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




        
#SERVER = 'localhost:8080'
SERVER = 'pygameserver.appspot.com'


if __name__ == '__main__':
    shlf = DistributedState()
    print shlf.version()

    shlf.login('nwhitehe@gmail.com', 'aribc45')
    shlf.new_app('NathanWhitehead+testapp+2', ANY, ANY)
#    shlf.join('NathanWhitehead+testapp+1')
    shlf['blah'] = 'foobar'
    print shlf['blah']
    shlf['testing'] = [1,2,3,'hello\nto you']
    print shlf['testing']
    try:
        x = shlf.get_if_changed('testing', hash_value([1,2,3,'hello\nto you']))
        print 'ERROR ', x
    except DataUnchangedError:
        print 'Data unchanged, as it should be'
    shlf[1] = 3
    print shlf[1]
    shlf[1] += 2
    print shlf[1]
    shlf['message'] = 'secret'
    print shlf['message']
    shlf.update('message', hash_value('secret'), 'public')

    print shlf['message']
    try:
        shlf.update('message', hash_value('secret'), 'public2')
    except UpdateFailedError:
        print "update failed, as it should"
    print shlf['message']

    del shlf['message']

    try:
        print shlf['message']
    except KeyError:
        print 'get failed, as it should'

    shlf.delete_app()
    sys.exit()
