import pyfluidsynth as fl
import time
import pyaudio

pa = pyaudio.PyAudio()
strm = pa.open(
    format = pyaudio.paInt16,
    channels = 2, 
    rate = 44100, 
    output = True)

s = []

fl.init()

# Initial silence is 1 second
s.append(fl.write_s16(44100 * 1))

sf = fl.sfload("example.sf2")
fl.program_select(0, sf, 0, 0)

fl.noteon(0, 60, 30)
fl.noteon(0, 67, 30)
fl.noteon(0, 76, 30)

# Chord is held for 2 seconds
s.append(fl.write_s16(44100 * 2))

fl.noteoff(0, 60)
fl.noteoff(0, 67)
fl.noteoff(0, 76)

# Decay of chord is held for 1 second
s.append(fl.write_s16(44100 * 1))

fl.stop()

samps = ''.join(s)

print len(samps)
strm.write(samps)
