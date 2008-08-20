from distutils.core import setup, Extension

setup(name = "SoundAnalyse",
      version = "0.1.0",
      py_modules = ['analyse'],
      ext_modules = [Extension("analyseffi", ["analyseffi.c"])],
      )
