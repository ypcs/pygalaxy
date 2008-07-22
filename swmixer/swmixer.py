"""Advanced Realtime Software Mixer

This module implements an advanced realtime sound mixer suitable for
use in games or other audio applications.  It supports loading sounds
in uncompressed WAV format.  It can mix several sounds together during
playback.  The volume and position of each sound can be finely
controlled.  The mixer can use a separate thread so clients never block
during operations.  Samples can also be looped any number of times.
Looping is accurate down to a single sample, so well designed loops
will play seamlessly.  Also supports sound recording during playback.

Copyright 2008, Nathan Whitehead
Released under the LGPL

"""

import time
import wave
import thread

import numpy
import pyaudio

ginit = False
gstereo = True
gchunksize = 1024
gsamplerate = 22050
gchannels = 1
gsamplewidth = 2
gpyaudio = None
gstream = None
gmicstream = None
gmic = False
gmicdata = None
gmixer_srcs = []
gid = 1
glock = thread.allocate_lock()
ginput_device_index = None
goutput_device_index = None

# Format for srcs:
#   first element is raw data
#   second is current play position in samples
#   third is volume envelope, list of time,vol pairs (time in samples)

# A channel is a "sound event" that is playing
class Channel:
    """Represents one sound source currently playing"""
    def __init__(self, data, pos, env, loops):
        global gid
        self.id = gid
        gid += 1
        self.data = data
        self.pos = pos
        self.env = env
        self.loops = loops
        self.active = True
    def stop(self):
        """Stop the sound playing"""
        glock.acquire()
        gmixer_srcs.remove(self)
        glock.release()
    def pause(self):
        """Pause the sound temporarily"""
        glock.acquire()
        self.active = False
        glock.release()
    def unpause(self):
        """Unpause a previously paused sound"""
        glock.acquire()
        self.active = True
        glock.release()
    def set_volume(self, v, fadetime=0):
        """Set the volume of the sound

        Removes any previously set envelope information.  Also
        overrides any pending fadeins or fadeouts.

        """
        glock.acquire()
        if fadetime == 0:
            self.env = [[0, v]]
        else:
            curv = calc_vol(self.pos, self.env)
            self.env = [[self.pos, curv], [self.pos + fadetime, v]]
        glock.release()
    def get_volume(self):
        """Return current volume of sound"""
        glock.acquire()
        v = calc_vol(self.pos, self.env)
        glock.release()
        return v
    def get_position(self):
        """Return current position of sound in samples"""
        glock.acquire()
        p = self.pos
        glock.release()
        return p
    def set_position(self, p):
        """Set current position of sound in samples"""
        glock.acquire()
        self.pos = p
        glock.release()
    def fadeout(self, time):
        """Schedule a fadeout of this sound in given time"""
        glock.acquire()
        self.set_volume(0.0, fadetime=time)
        glock.release()


def resample(smp, scale=1.0):
    """Resample a sound to be a different length

    Sample must be mono.  May take some time for longer sounds
    sampled at 44100 Hz.

    Keyword arguments:
    scale - scale factor for length of sound (2.0 means double length)

    """
    # f*ing cool, numpy can do this with one command
    # calculate new length of sample
    n = round(len(smp) * scale)
    # use linear interpolation
    # endpoint keyword means than linspace doesn't go all the way to 1.0
    # If it did, there are some off-by-one errors
    # e.g. scale=2.0, [1,2,3] should go to [1,1.5,2,2.5,3,3]
    # but with endpoint=True, we get [1,1.4,1.8,2.2,2.6,3]
    # Both are OK, but since resampling will often involve
    # exact ratios (i.e. for 44100 to 22050 or vice versa)
    # using endpoint=False gets less noise in the resampled sound
    return numpy.interp(
        numpy.linspace(0.0, 1.0, n, endpoint=False), # where to interpret
        numpy.linspace(0.0, 1.0, len(smp), endpoint=False), # known positions
        smp, # known data points
        )

def interleave(left, right):
    """Given two separate arrays, return a new interleaved array

    This function is useful for converting separate left/right audio
    streams into one stereo audio stream.  Input arrays and returned
    array are Numpy arrays.

    See also: uninterleave()

    """
    return numpy.ravel(numpy.vstack((left, right)), order='F')

def uninterleave(data):
    """Given a stereo array, return separate left and right streams

    This function converts one array representing interleaved left and
    right audio streams into separate left and right arrays.  The return
    value is a list of length two.  Input array and output arrays are all
    Numpy arrays.

    See also: interleave()

    """
    return data.reshape(2, len(data)/2, order='FORTRAN')

def stereo_to_mono(left, right):
    """Return mono array from left and right sound stream arrays"""
    return (0.5 * left + 0.5 * right).astype(numpy.int16)


class Sound:
    """Represents a playable sound"""

    def __init__(self, filename=None, data=None):
        """Create new sound from a WAV file or explicit sample data"""
        assert(ginit == True)
        if filename is not None:
            wf = wave.open(filename, 'rb')
            #assert(wf.getsampwidth() == 2)
            nc = wf.getnchannels()
            self.framerate = wf.getframerate()
            fr = wf.getframerate()
            # read data
            data = []
            r = ' '
            while r != '':
                r = wf.readframes(4096)
                data.append(r)
            if wf.getsampwidth() == 2:
                self.data = numpy.fromstring(''.join(data), dtype=numpy.int16)
            if wf.getsampwidth() == 4: 
                self.data = numpy.fromstring(''.join(data), dtype=numpy.int32)
                self.data = self.data / 65536.0
            if wf.getsampwidth() == 1:
                self.data = numpy.fromstring(''.join(data), dtype=numpy.uint8)
                self.data = self.data * 256.0
            wf.close()
            if fr != gsamplerate:
                scale = gsamplerate * 1.0 / fr
                if nc == 1:
                    self.data = resample(self.data, scale)
                if nc == 2:
                    # for stereo resample independently
                    left, right = uninterleave(self.data)
                    nleft = resample(left, scale)
                    nright = resample(right, scale)
                    self.data = interleave(nleft, nright)
            if nc != gchannels:
                # oops, stereo-ness differs
                # convert to match init parameters
                if nc == 1:
                    # came in mono, need stereo
                    self.data = interleave(self.data, self.data)
                if nc == 2:
                    # came in stereo, need mono
                    # first make it a 2d array
                    left, right = uninterleave(self.data)
                    self.data = stereo_to_mono(left, right)
            return
        if data is not None:
            self.data = data
            return
        assert False

    def play(self, volume=1.0, offset=0, fadein=0, envelope=None, loops=0):
        """Play the sound

        Keyword arguments:
        volume - volume to play sound at
        offset - sample to start playback
        fadein - number of samples to slowly fade in volume
        envelope - a list of [offset, volume] pairs defining
                   a linear volume envelope
        loops - how many times to play the sound (-1 is infinite)

        """
        if envelope != None:
            env = envelope
        else:
            if volume == 1.0 and fadein == 0:
                env = []
            else:
                if fadein == 0:
                    env = [[0, volume]]
                else:
                    env = [[offset, 0.0], [offset + fadein, volume]]
        sndevent = Channel(self.data, offset, env, loops)
        glock.acquire()
        gmixer_srcs.append(sndevent)
        glock.release()
        return sndevent

    def scale(self, vol):
        """Scale a sound sample

        vol is 0.0 to 1.0, amount to scale by
        """
        self.data = (self.data * vol).astype(numpy.int16)

    def resample(self, scale):
         """Resample a sound

         scale = 1.0 means original sound
         scale = 0.5 is half as long (up an octave)
         scale = 2.0 is twice as long (down an octave)
         
         """
         self.data = resample(self.data, scale)

def calc_vol(t, env):
    """Calculate volume at time t given envelope env

    envelope is a list of [time, volume] points
    time is measured in samples
    envelope should be sorted by time

    """
    #Find location of last envelope point before t
    if len(env) == 0: return 1.0
    if len(env) == 1:
        return env[0][1]
    n = 0
    while n < len(env) and env[n][0] < t:
        n += 1
    if n == 0:
        # in this case first point is already too far
        # envelope hasn't started, just use first volume
        return env[0][1]
    if n == len(env):
        # in this case, all points are before, envelope is over
        # use last volume
        return env[-1][1]
        
    # now n holds point that is later than t
    # n - 1 is point before t
    f = float(t - env[n - 1][0]) / (env[n][0] - env[n - 1][0])
    # f is 0.0--1.0, is how far along line t has moved from
    #  point n - 1 to point n
    # volume is linear interpolation between points
    return env[n - 1][1] * (1.0 - f) + env[n][1] * f

def microphone_on():
    """Turn on microphone

    Schedule audio input during main mixer tick.

    """
    global gstream, gmicstream, gmic
    glock.acquire()
    if gmicstream is not None:
        gmicstream.close()
    if gstream is not None:
        gstream.close()
    gmicstream = gpyaudio.open(
        format = pyaudio.paInt16,
        channels = gchannels,
        rate = gsamplerate,
        input_device_index = ginput_device_index,
        input = True)
    gstream = gpyaudio.open(
        format = pyaudio.paInt16,
        channels = gchannels,
        rate = gsamplerate,
        output_device_index = goutput_device_index,
        output = True)
    gmic = True
    glock.release()

def microphone_off():
    """Turn off microphone"""
    global gstream, gmicstream, gmic
    glock.acquire()
    if gmicstream is not None:
        gmicstream.close()
    if gstream is not None:
        gstream.close()
    gstream = gpyaudio.open(
        format = pyaudio.paInt16,
        channels = gchannels,
        rate = gsamplerate,
        output_device_index = goutput_device_index,
        output = True)
    gmic = False
    glock.release()

def get_microphone():
    """Return raw data from microphone as Numpy array

    Default format will be 16-bit signed mono.  Format will match
    audio playback.  You must call tick() every frame to update the
    results from this function.

    """
    glock.acquire()
    d = gmicdata
    glock.release()
    return numpy.fromstring(gmicdata, dtype=numpy.int16)
    
def tick(extra=None):
    """Main loop of mixer, mix and do audio IO.

    Audio sources are mixed by addition and then clipped.  Too many
    loud sources will cause distortion.

    extra is for extra sound data to mix into output
      must be in numpy array of correct length
      
    """
    global ginit
    global gmixer_srcs
    if not ginit:
        return
    sz = gchunksize * gchannels
    b = numpy.zeros(sz, numpy.float)
    rmlist = []
    glock.acquire()
    for sndevt in gmixer_srcs:
        if sndevt.active:
            pos = sndevt.pos
            z = sndevt.data[pos:pos + sz]
            sndevt.pos += sz
            if len(z) < sz:
                # oops, sample data didn't cover buffer
                if sndevt.loops != 0:
                    # loop around
                    sndevt.loops -= 1
                    sndevt.pos = sz - len(z)
                    v = calc_vol(pos, sndevt.env)
                    sndevt.env = [[0, v]]
                    z = numpy.append(z, sndevt.data[:sz - len(z)])
                else:
                    # nothing to loop, just append zeroes
                    z = numpy.append(z, numpy.zeros(sz - len(z), numpy.int16))
                    # and stop the sample, it's done
                    rmlist.append(sndevt)
            if pos + sz == len(sndevt.data):
                # this case loops without needing any appending
                if sndevt.loops != 0:
                    sndevt.loops -= 1
                    sndevt.pos = 0
                    v = calc_vol(pos, sndevt.env)
                    sndevt.env = [[0, v]]
                else:
                    rmlist.append(sndevt)
            v = calc_vol(pos, sndevt.env)
            b += z * v
    if extra is not None:
        b += extra
    b = b.clip(-32767.0, 32767.0)
    for e in rmlist:
        gmixer_srcs.remove(e)
    global gmicdata
    if gmic:
        gmicdata = gmicstream.read(sz)
    glock.release()
    odata = (b.astype(numpy.int16)).tostring()
    gstream.write(odata, sz)

def init(samplerate=22050, chunksize=1024, stereo=True, microphone=False, input_device_index=None, output_device_index=None):
    """Initialize mixer

    Must be called before any sounds can be played or loaded.

    Keyword arguments:
    samplerate - samplerate to use for playback (default 22050)
    chunksize - size of playback chunks
      smaller is more responsive but perhaps stutters
      larger is more buffered, less stuttery but less responsive
      Can be any size, does not need to be a power of two. (default 1024)
    stereo - whether to play back in stereo
    microphone - whether to enable microphone recording
    
    """
    global gstereo, gchunksize, gsamplerate, gchannels, gsamplewidth
    global ginit
    assert (10000 < samplerate <= 48000)
    gsamplerate = samplerate
    gchunksize = chunksize
    assert (stereo in [True, False])
    gstereo = stereo
    if stereo:
        gchannels = 2
    else:
        gchannels = 1
    gsamplewidth = 2
    global gpyaudio, gstream
    gpyaudio = pyaudio.PyAudio()
    # It's important to open Input, then Output (not sure why)
    # Other direction gives very annoying sound errors (1/2 rate?)
    global ginput_device_index, goutput_device_index
    ginput_device_index = input_device_index
    goutput_device_index = output_device_index
    if microphone:
        global gmicstream, gmic
        gmicstream = gpyaudio.open(
            format = pyaudio.paInt16,
            channels = gchannels,
            rate = gsamplerate,
            input_device_index = input_device_index,
            input = True)
        gmic = True
    gstream = gpyaudio.open(
        format = pyaudio.paInt16,
        channels = gchannels,
        rate = gsamplerate,
        output_device_index = output_device_index,
        output = True)
    ginit = True

def start():
    """Start separate mixing thread"""
    def f():
        while True:
            tick()
            time.sleep(0.001)
    thread.start_new_thread(f, ())

def quit():
    """Stop all playback and terminate mixer"""
    global ginit
    ginit = False
    if gstream is not None:
        gstream.close()
    if gmicstream is not None:
        gmicstream.close()
    gpyaudio.terminate()

def set_chunksize(size=1024):
    """Set the audio chunk size for each frame of audio output

    This function is useful for setting the framerate when audio output
    is synchronized with video.
    """
    global gchunksize
    glock.acquire()
    gchunksize = size
    glock.release()
