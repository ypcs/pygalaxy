import pyfluidsynth as fl
import time

fl.init()
fl.start()

sf = fl.sfload("example.sf2")
fl.program_select(0, sf, 0, 0)

fl.noteon(0, 60, 30)
fl.noteon(0, 67, 30)
fl.noteon(0, 76, 30)

time.sleep(1.0)

fl.noteoff(0, 60)
fl.noteoff(0, 67)
fl.noteoff(0, 76)

time.sleep(1.0)

fl.stop()
