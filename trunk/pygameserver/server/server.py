#
# Copyright 2008 Nathan Whitehead
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

'''pygameserver

Google App Engine server for AppState module.

'''

import md5
import logging

from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

VERSION = 'Version 0.4'

# How big can one entry in application table be?
SINGLE_SIZE_LIMIT = 32000

def hash(x): return md5.new(x).hexdigest()

class Application(db.Model):
    '''Information about a client application'''
    appid = db.StringProperty(multiline=False)
    admin = db.UserProperty()
    readmode = db.IntegerProperty()
    # 0 = anyone can read
    # 1 = only admin can read
    # 2 = anyone logged in, authorized, can read
    # 3 = anyone logged in, not banned, can read
    writemode = db.IntegerProperty()
    # 0-3, same as readmode but for writing

class AppDataInstance(db.Model):
    appref = db.ReferenceProperty(Application)
    shelfkey = db.StringProperty(multiline=False)
    shelfdata = db.BlobProperty()
    datalen = db.IntegerProperty()
    who = db.UserProperty()

class AuthorizedUser(db.Model):
    appref = db.ReferenceProperty(Application)
    who = db.UserProperty()
    
class BannedUser(db.Model):
    appref = db.ReferenceProperty(Application)
    who = db.UserProperty()

# Functions that benefit from being cached
def lookup_app(appkey):
    data = memcache.get(appkey)
    if data is not None: return data
    try:
        data = db.get(db.Key(appkey))
        if not memcache.add(appkey, data, 60 * 60 ): # 1 hour expire time
            logging.error('memcache add() failed for appkey')
        return data
    except:
        return None
def can_do(appl, mode, who):
    if mode == 0: return True
    if mode == 1: return (who == appl.admin)
    if mode == 2:
        auth = AuthorizedUser.all().filter('appref =', appl).filter('who =', who).get()
        return (auth is not None)
    if mode == 3:
        ban = BannedUser.all().filter('appref =', appl).filter('who =', who).get()
        return (ban is None)
    return False
def can_read(appl, who):
    memcachekey = 'R' + str(appl.key()) + ':' + str(who)
    data = memcache.get(memcachekey)
    if data is not None: return data
    data = can_do(appl, appl.readmode, who)
    if not memcache.add(memcachekey, data, 60 * 10):
        logging.error('memcache add() failed for read perm')
    return data
def can_write(appl, who): 
    memcachekey = 'W' + str(appl.key()) + ':' + str(who)
    data = memcache.get(memcachekey)
    if data is not None: return data
    data = can_do(appl, appl.writemode, who)
    if not memcache.add(memcachekey, data, 60 * 10):
        logging.error('memcache add() failed for write perm')
    return data


# Process requests

def Process(cmd, arg1, arg2, arg3, arg4):
    '''Process PythonRemoteProcedureCall request'''
    user = users.get_current_user()

    if cmd == 'version':
        return VERSION

    if cmd == 'registerapp':
        appid = arg1
        # Make sure logged in
        if user is None:
            return '!!!!!must be logged in'
        # Check if appid is already in use
        prevapp = Application.all().filter('appid =', appid).get()
        if prevapp is not None:
            return '!!!!!appid in use'
        app = Application()
        app.appid = arg1
        app.admin = user
        app.readmode = int(arg2)
        app.writemode = int(arg3)
        app.put()
        return 'OK'

    if cmd == 'deleteapp':
        appkey = arg1
        # Make sure logged in
        if user is None:
            return '!!!!!must be logged in'
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if user != appl.admin:
            return '!!!!!you must be admin'
        appl.delete()
        return 'OK'

    if cmd == 'getapp':
        appid = arg1
        # Retrieve key of application
        app = Application.all().filter('appid =', appid).get()
        if app is None:
            return '!!!!!appid not found'
        return str(app.key())

    if cmd == 'authorize':
        appkey = arg1
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if user != appl.admin:
            return '!!!!!you must be admin'
        auser = users.User(arg2)
        if auser is None:
            # Currently this doesn't happen, invalid emails
            # create ghost User objects
            return '!!!!!user email not found'
        prevauth = AuthorizedUser.all().filter('appref =', appl).filter('who =', auser).get()
        if prevauth is not None:
            return '!!!!!already authorized'
        authuser = AuthorizedUser(appref=appl, who=auser)
        authuser.put()
        # Clear permissions cache
        memcache.delete('R' + str(appl.key()) + ':' + str(auser))
        memcache.delete('W' + str(appl.key()) + ':' + str(auser))
        return 'OK'

    if cmd == 'unauthorize':
        appkey = arg1
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if user != appl.admin:
            return '!!!!!you must be admin'
        auser = users.User(arg2)
        if auser is None:
            # Currently this doesn't happen, invalid emails
            # create ghost User objects
            return '!!!!!user email not found'
        prevauth = AuthorizedUser.all().filter('appref =', appl).filter('who =', auser).get()
        if prevauth is None:
            return '!!!!!not already authorized'
        prevauth.delete()
        # Clear permissions cache
        memcache.delete('R' + str(appl.key()) + ':' + str(auser))
        memcache.delete('W' + str(appl.key()) + ':' + str(auser))
        return 'OK'

    if cmd == 'ban':
        appkey = arg1
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if user != appl.admin:
            return '!!!!!you must be admin'
        auser = users.User(arg2)
        if auser is None:
            # Currently this doesn't happen, invalid emails
            # create ghost User objects
            return '!!!!!user email not found'
        prevban = BannedUser.all().filter('appref =', appl).filter('who =', auser).get()
        if prevban is not None:
            return '!!!!!already banned'
        banuser = BannedUser(appref=appl, who=auser)
        banuser.put()
        # Clear permissions cache
        memcache.delete('R' + str(appl.key()) + ':' + str(auser))
        memcache.delete('W' + str(appl.key()) + ':' + str(auser))
        return 'OK'

    if cmd == 'unban':
        appkey = arg1
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if user != appl.admin:
            return '!!!!!you must be admin'
        auser = users.User(arg2)
        if auser is None:
            # Currently this doesn't happen, invalid emails
            # create ghost User objects
            return '!!!!!user email not found'
        prevban = BannedUser.all().filter('appref =', appl).filter('who =', auser).get()
        if prevban is None:
            return '!!!!!not banned'
        prevban.delete()
        # Clear permissions cache
        memcache.delete('R' + str(appl.key()) + ':' + str(auser))
        memcache.delete('W' + str(appl.key()) + ':' + str(auser))
        return 'OK'

    if cmd == 'get':
        appkey = arg1
        shelfkey = arg2
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if not can_read(appl, user):
            return '!!!!!no permission to read'
        # First check the cache
        memcachekey = 'K' + str(appl.key()) + ':' + shelfkey
        data = memcache.get(memcachekey)
        if data is not None: return data
        # Not in cache, do a query
        appinst = AppDataInstance.all().filter('appref =', appl).filter('shelfkey =', shelfkey).get()
        if appinst is None:
            return '!!!!!keyerror'
        else: data = appinst.shelfdata
        if not memcache.add(memcachekey, data, 60 * 60):
            logging.error('error adding memcache in get()')
        return data

    if cmd == 'getifchanged':
        appkey = arg1
        shelfkey = arg2
        oldhash = arg3
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if not can_read(appl, user):
            return '!!!!!no permission to read'
        # First check the cache
        memcachekey = 'K' + str(appl.key()) + ':' + shelfkey
        data = memcache.get(memcachekey)
        if data is not None:
            if oldhash == hash(data):
                return '!!!!!hash match'
            return data
        # Not in cache, do a query
        appinst = AppDataInstance.all().filter('appref =', appl).filter('shelfkey =', shelfkey).get()
        if appinst is None:
            return '!!!!!keyerror'
        else: data = appinst.shelfdata
        if not memcache.add(memcachekey, data, 60 * 60):
            logging.error('error adding memcache in get()')
        if oldhash == hash(data):
            return '!!!!!hash match'
        return data

    if cmd == 'set':
        appkey = arg1
        shelfkey = arg2
        shelfdata = arg3
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if not can_write(appl, user):
            return '!!!!!no permission to write'
        if len(shelfdata) > SINGLE_SIZE_LIMIT:
            return '!!!!!too big'
        appinst = AppDataInstance.all().filter('appref =', appl).filter('shelfkey =', shelfkey).get()
        if appinst is None:
            appinst = AppDataInstance()
            appinst.appref = appl
            appinst.shelfkey = shelfkey
        appinst.shelfdata = shelfdata
        appinst.datalen = len(shelfdata)
        appinst.who = user
        appinst.put()
        memcachekey = 'K' + str(appl.key()) + ':' + shelfkey
        memcache.delete(memcachekey)
        return 'OK'

    if cmd == 'del':
        appkey = arg1
        shelfkey = arg2
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if not can_write(appl, user):
            return '!!!!!no permission to write'
        appinst = AppDataInstance.all().filter('appref =', appl).filter('shelfkey =', shelfkey).get()
        if appinst is None:
            return '!!!!!keyerror'
        appinst.delete()
        memcachekey = 'K' + str(appl.key()) + ':' + shelfkey
        memcache.delete(memcachekey)
        return 'OK'

    if cmd == 'update':
        appkey = arg1
        shelfkey = arg2
        oldhash = arg3
        shelfdata = arg4
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if not can_write(appl, user):
            return '!!!!!no permission to write'
        if len(shelfdata) > SINGLE_SIZE_LIMIT:
            return '!!!!!too big'
        appinst = AppDataInstance.all().filter('appref =', appl).filter('shelfkey =', shelfkey).get()
        if appinst is None:
            return '!!!!!no value'
        if oldhash != hash(appinst.shelfdata):
            return '!!!!!hash mismatch'
        appinst.shelfdata = shelfdata
        appinst.datalen = len(shelfdata)
        appinst.who = user
        appinst.put()
        memcachekey = 'K' + str(appl.key()) + ':' + shelfkey
        memcache.delete(memcachekey)
        return 'OK'

    if cmd == 'memcache':
        stats =  memcache.get_stats()
        return '%d hits\n%d misses\n' % (stats['hits'], stats['misses'])

    if cmd == 'email':
        appkey = arg1
        addr = arg2
        subj = arg3
        body = arg4
        appl = lookup_app(appkey)
        if appl is None:
            return '!!!!!appkey not found'
        if not user:
            return '!!!!!you must be logged in'
        if not mail.is_email_valid(addr):
            return '!!!!!invalid address'
        mail.send_mail(user.email(), addr, subj, body)
        return 'OK'

    return '!!!!!unknown command'

class Prpc(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        self.response.out.write('ERROR\nMust use POST method\n')
    def post(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        cmd = self.request.get('cmd')
        arg1 = self.request.get('arg1')
        arg2 = self.request.get('arg2')
        arg3 = self.request.get('arg3')
        arg4 = self.request.get('arg4')
        #try:
        resp = Process(cmd, arg1, arg2, arg3, arg4)
        #except:
        #    self.response.out.write('!!!!!process')
        #    return
        self.response.out.write(resp)

class Version(webapp.RequestHandler):
    def get(self):
        self.response.out.write(VERSION + '<br>\n')
    def post(self):
        self.response.out.write(VERSION + '<br>\n')

application = webapp.WSGIApplication([
        ('/prpc', Prpc),
        ('/version', Version),
        ], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
