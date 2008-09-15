#
# Copyright 2008 Nathan Whitehead
# Copyright 2007 Google Inc.
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

'''Python Remote Procedure Calls

A hack to support making calls to a server.  Supports one command and
up to 4 arguments.  Most notable feature: supports loggin in via
Google accounts.  Data sent and received can be 8-bit.

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
import marshal


### Extracted and hacked up from appcfg.py of Google App Engine SDK

def GetUserAgent():
    python_version = ".".join(str(i) for i in sys.version_info)
    return 'AppState-Python/%s' % python_version

class ClientLoginError(urllib2.HTTPError):
  """Raised to indicate there was an error authenticating with ClientLogin."""

  def __init__(self, url, code, msg, headers, args):
    urllib2.HTTPError.__init__(self, url, code, msg, headers, None)
    self.args = args
    self.reason = args["Error"]

class AbstractRpcServer(object):
  """Provides a common interface for a simple RPC server."""

  def __init__(self, host):
    """Creates a new HttpRpcServer.

    Args:
      host: The host to send requests to.
    """
    self.host = host
    self.authenticated = False

    self.extra_headers = {
      "User-agent": GetUserAgent()
    }
    self.cookie_jar = cookielib.MozillaCookieJar()
    self.opener = self._GetOpener()
    logging.info("Server: %s", self.host)

  def _GetOpener(self):
    """Returns an OpenerDirector for making HTTP requests.

    Returns:
      A urllib2.OpenerDirector object.
    """
    raise NotImplemented()

  def _CreateRequest(self, url, data=None):
    """Creates a new urllib request."""
    logging.debug("Creating request for: '%s' with payload:\n%s", url, data)
    req = urllib2.Request(url, data=data)
    for key, value in self.extra_headers.iteritems():
      req.add_header(key, value)
    return req

  def _GetAuthToken(self, email, password):
    """Uses ClientLogin to authenticate the user, returning an auth token.

    Args:
      email:    The user's email address
      password: The user's password

    Raises:
      ClientLoginError: If there was an error authenticating with ClientLogin.
      HTTPError: If there was some other form of HTTP error.

    Returns:
      The authentication token returned by ClientLogin.
    """
    req = self._CreateRequest(
        url="https://www.google.com/accounts/ClientLogin",
        data=urllib.urlencode({
            "Email": email,
            "Passwd": password,
            "service": "ah",
            "source": "Python-test",
            "accountType": "HOSTED_OR_GOOGLE"
        })
    )
    try:
      response = self.opener.open(req)
      response_body = response.read()
      response_dict = dict(x.split("=")
                           for x in response_body.split("\n") if x)
      return response_dict["Auth"]
    except urllib2.HTTPError, e:
      if e.code == 403:
        body = e.read()
        response_dict = dict(x.split("=", 1) for x in body.split("\n") if x)
        raise ClientLoginError(req.get_full_url(), e.code, e.msg,
                               e.headers, response_dict)
      else:
        raise

  def _GetAuthCookie(self, auth_token):
    """Fetches authentication cookies for an authentication token.

    Args:
      auth_token: The authentication token returned by ClientLogin.

    Raises:
      HTTPError: If there was an error fetching the authentication cookies.
    """
    continue_location = "http://localhost/"
    args = {"continue": continue_location, "auth": auth_token}
    req = self._CreateRequest("http://%s/_ah/login?%s" %
                              (self.host, urllib.urlencode(args)))
    try:
      response = self.opener.open(req)
    except urllib2.HTTPError, e:
      response = e
    if (response.code != 302 or
        response.info()["location"] != continue_location):
      raise urllib2.HTTPError(req.get_full_url(), response.code, response.msg,
                              response.headers, response.fp)
    self.authenticated = True

  def _Authenticate(self, email, password):
    """Authenticates the user.

    The authentication process works as follows:
     1) We get a username and password from the user
     2) We use ClientLogin to obtain an AUTH token for the user
        (see http://code.google.com/apis/accounts/AuthForInstalledApps.html).
     3) We pass the auth token to /_ah/login on the server to obtain an
        authentication cookie. If login was successful, it tries to redirect
        us to the URL we provided.

    If we attempt to access the upload API without first obtaining an
    authentication cookie, it returns a 401 response and directs us to
    authenticate ourselves with ClientLogin.

https://www.google.com/accounts/DisplayUnlockCaptcha
and verify you are a human.  Then try again.
    """
    auth_token = self._GetAuthToken(email, password)
    self._GetAuthCookie(auth_token)
    return

  def Send(self, request_path, args={}, payload="",
           content_type="application/octet-stream",
           timeout=None):
    """Sends an RPC and returns the response.

    Args:
      request_path: The path to send the request to, eg /api/appversion/create.
      args: CGI keyword arguments, as a dict
      payload: The body of the request, or None to send an empty request.
      content_type: The Content-Type header to use.
      timeout: timeout in seconds; default None i.e. no timeout.
        (Note: for large requests on OS X, the timeout doesn't work right.)

    Returns:
      The response body, as a string.
    """
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
      tries = 0
      while True:
        tries += 1
        url = "http://%s%s?%s" % (self.host, request_path,
                                  urllib.urlencode(args))
        req = self._CreateRequest(url=url, data=payload)
        req.add_header("Content-Type", content_type)
        #req.add_header("X-appcfg-api-version", "1")
        try:
          f = self.opener.open(req)
          response = f.read()
          f.close()
          return response
        except urllib2.HTTPError, e:
          if tries > 3:
            raise
          elif e.code == 401:
            self._Authenticate()
          elif e.code >= 500 and e.code < 600:
            continue
          else:
            raise
    finally:
      socket.setdefaulttimeout(old_timeout)


class HttpRpcServer(AbstractRpcServer):
  """Provides a simplified RPC-style interface for HTTP requests."""

  def _GetOpener(self):
    """Returns an OpenerDirector that supports cookies and ignores redirects.

    Returns:
      A urllib2.OpenerDirector object.
    """
    opener = urllib2.OpenerDirector()
    opener.add_handler(urllib2.ProxyHandler())
    opener.add_handler(urllib2.UnknownHandler())
    opener.add_handler(urllib2.HTTPHandler())
    opener.add_handler(urllib2.HTTPDefaultErrorHandler())
    opener.add_handler(urllib2.HTTPSHandler())
    opener.add_handler(urllib2.HTTPErrorProcessor())

    opener.add_handler(urllib2.HTTPCookieProcessor(self.cookie_jar))
    return opener

### End extraction

class DataCorruptionError(Exception): pass

class PRPC():
    def __init__(self, hostname, command='/prpc'):
        self.hostname = hostname
        self.command = command
        self.server = HttpRpcServer(hostname)
    def login(self, email, password):
        self.server._Authenticate(email, password)
    def send(self, cmd, arg1=None, arg2=None, arg3=None, arg4=None):
        args = {'cmd':cmd}
        if arg1 is not None: args['arg1'] = arg1
        if arg2 is not None: args['arg2'] = arg2
        if arg3 is not None: args['arg3'] = arg3
        if arg4 is not None: args['arg4'] = arg4
        return self.server.Send(self.command, 
                                content_type='application/x-www-form-urlencoded; charset=utf-8',
                                payload = urllib.urlencode(args))
