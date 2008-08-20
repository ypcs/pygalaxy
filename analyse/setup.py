from distutils.core import setup, Extension

setup(name = "SoundAnalyse",
      version = "1.0",
      py_modules = ['analyse'],
      ext_modules = [Extension("analyseffi", ["analyseffi.c"])],
      )
