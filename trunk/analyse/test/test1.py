import numpy
import pyaudio
import analyse

# Initialize PyAudio
pyaud = pyaudio.PyAudio()
# Open input stream, 16-bit mono at 44100 Hz
stream = pyaud.open(
    format = pyaudio.paInt16,
    channels = 1,
    rate = 44100,
    input_device_index = 2,
    input = True)

while True:
    rawsamps = stream.read(1024)
    samps = numpy.fromstring(rawsamps, dtype=numpy.int16)
    print analyse.loudness(samps)
