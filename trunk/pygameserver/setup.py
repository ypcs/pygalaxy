from distutils.core import setup, Extension

setup(name = "AppState",
      author = "Nathan Whitehead",
      author_email = "nwhitehe@gmail.com",
      version = "0.1.0",
      url = "http://code.google.com/p/pygalaxy/",
      py_modules = ['appstate'],
      description = "Distributed application state via a Google App Engine server",
      long_description = '''
This module allows your Python programs to easily have a persistent
global distributed state.  This state can be used to store things like
number of users, game high scores, message of the day from the author,
etc.
''',
      )
