from distutils.core import setup

setup(name='pyGalaxy',
      version='0.1.0',
      description='Game library for quickly creating innovative 2D games using python and pygame',
      author='Nathan Whitehead',
      author_email='nwhitehe@deadpixelpress.com',
      url='http://code.google.com/p/pygalaxy',
      license='LGPL',
      packages=['pygalaxy'],
      provides=['pygalaxy'],
      requires=['pygame'],
      long_description="""
This is a PyGame game library designed to make programming simple 2D 
games easier.  It works with keyboard, joystick, mouse, and Wii 
controllers connected on bluetooth.  It has drawing primitives, animated 
sprites, collision detection, music, sound effects, particle systems, 
artificial intelligence and more!
"""
      )
