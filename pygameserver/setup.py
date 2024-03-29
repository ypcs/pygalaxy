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

from distutils.core import setup, Extension

setup(name = "AppState",
      author = "Nathan Whitehead",
      author_email = "nwhitehe@gmail.com",
      version = "0.1",
      license = "LGPL",
      url = "http://code.google.com/p/pygalaxy/",
      py_modules = ['appstate', 'rencode', 'prpc'],
      description = "Distributed application state via a Google App Engine server",
      long_description = '''
This module allows your Python programs to easily have a persistent
global distributed shared state.  This state can be used to store
things like number of users, game high scores, message of the day from
the author, etc.  The state has an interface like a dictionary with
some additional synchronization functionality and some restrictions.
This module connects to a server on the Google App Engine to store and
manage data.  It uses a simple security model based on Google
accounts.
''',
      )
