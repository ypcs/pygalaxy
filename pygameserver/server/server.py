import md5
import pickle

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

class AppDataInstance(db.Model):
    appid = db.StringProperty(multiline=False)
    shelfkey = db.StringProperty(multiline=False)
    shelfdata = db.TextProperty()

def getinst(appid, key, create=True):
    results = AppDataInstance.all()
    results.filter('appid =', appid)
    results.filter('shelfkey =', key)
    list_results = []
    for result in results:
        list_results.append(result)
    if len(list_results) == 0:
        if create:
            inst = AppDataInstance()
            inst.appid = appid
            inst.shelfkey = key
            inst.shelfdata = ''
            inst.put()
            return inst
        raise KeyError
    if len(list_results) == 1:
        return list_results[0]
    raise KeyError

class GetState(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        appid = self.request.get('appid')
        if appid == '':
            self.response.out.write('ERROR\nMust specify appid')
            return
        key = self.request.get('key')
        if key == '':
            self.response.out.write('ERROR\nMust specify key')
            return
        try:
            inst = getinst(appid, key, create=False)
            self.response.out.write(inst.shelfdata)
            return
        except KeyError:
            self.response.out.write('ERROR\n')
            self.response.out.write('Wrong number of keys found for this application %s:%s\n' % (appid, key))
            return

class KeysState(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        appid = self.request.get('appid')
        if appid == '':
            self.response.out.write('ERROR\nMust specify appid')
            return
        results = AppDataInstance.all()
        results.filter('appid =', appid)
        keys = []
        for result in results:
            if result.shelfkey is not None:
                keys.append(result.shelfkey)
        self.response.out.write(pickle.dumps(keys))

class SetState(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        self.response.out.write('ERROR\nMust use POST method\n')
    def post(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        appid = self.request.get('appid')
        if appid == '':
            self.response.out.write('ERROR\nMust specify appid')
            return
        key = self.request.get('key')
        if key == '':
            self.response.out.write('ERROR\nMust specify key')
            return
        content = self.request.get('content')
        if len(content) > 100000:
            self.response.out.write('ERROR\nState too long')
            return
        try:
            inst = getinst(appid, key, create=True)
            inst.shelfdata = content
            inst.put()
            self.response.out.write('OK\n')
        except KeyError:
            self.response.out.write('ERROR\n')
            self.response.out.write('Wrong number of keys found for this application %s:%s\n' % (appid, key))
            return

class DelState(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        self.response.out.write('ERROR\nMust use POST method\n')
    def post(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        appid = self.request.get('appid')
        if appid == '':
            self.response.out.write('ERROR\nMust specify appid')
            return
        key = self.request.get('key')
        if key == '':
            self.response.out.write('ERROR\nMust specify key')
            return
        try:
            inst = getinst(appid, key, create=False)
            inst.delete()
            self.response.out.write('OK\n')
        except KeyError:
            self.response.out.write('ERROR\n')
            self.response.out.write('Wrong number of keys found for this application %s:%s\n' % (appid, key))
            return

class UpdateState(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        self.response.out.write('ERROR\nMust use POST method\n')
    def post(self):
        self.response.headers['Content-Type'] = 'text/plain' 
        appid = self.request.get('appid')
        if appid == '':
            self.response.out.write('ERROR\nMust specify appid')
            return
        key = self.request.get('key')
        if key == '':
            self.response.out.write('ERROR\nMust specify key')
            return
        oldhash = self.request.get('old')
        if oldhash == '':
            self.response.out.write('ERROR\nMust specify oldhash')
            return
        content = self.request.get('content')
        if len(content) > 100000:
            self.response.out.write('ERROR\nState too long')
            return
        inst = getinst(appid, key)
        # Calculate MD5 hash of old state
        oldstatehash = md5.new(inst.shelfdata).hexdigest()
        # Compare to hash we got
        if oldhash != oldstatehash:
            self.response.out.write('FAIL\nState does not match digest given')
            return
        inst.shelfdata = content
        inst.put()
        self.response.out.write('OK\n')

class Login(webapp.RequestHandler):
    def get(self):
        self.response.out.write('Biotch\n')
        self.response.out.write('<html><body><a href="%s">login</a></body></html>' % users.create_login_url('/'))

application = webapp.WSGIApplication([
        ('/get', GetState),
        ('/keys', KeysState),
        ('/set', SetState),
        ('/del', DelState),
        ('/update', UpdateState),
        ('/login', Login),
        ], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
