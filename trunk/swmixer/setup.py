from distutils.core import setup, Extension

setup(name = "SWMixer",
      author = "Nathan Whitehead",
      author_email = "nwhitehe@gmail.com",
      version = "0.1.2",
      url = "http://code.google.com/p/pygalaxy/",
      py_modules = ['swmixer'],
      description = "An advanced software mixer for sound playback and recording",
      long_description = '''
This module implements a realtime sound mixer suitable for use in
games or other audio applications.  It supports loading sounds in
uncompressed WAV format.  It can mix several sounds together during
playback.  The volume and position of each sound can be finely
controlled.  Samples can also be looped any number of times.  Looping
is accurate down to a single sample, so well designed loops will play
seamlessly without clicks or pops.  In addition, the mixer supports
audio input during playback (if supported in pyaudio with your sound
card).''',
      )
