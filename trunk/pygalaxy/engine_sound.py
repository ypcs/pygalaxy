"""Sound effects and music playback.
"""

import pygame


def load_sound(filename):
    """Load a sound from a file and return it.

    Note that all sounds must be at the global sample rate,
    22050 samples per second, or they will sound distorted.
    Use audacity to examine sound files and resample to the
    correct rate if necessary.
    """
    return pygame.mixer.Sound(filename)


def play_sound(snd, vol = None):
    """Play a sound with optional volume.
    
    Volume is 0.0 to 1.0.
    """
    chan = snd.play()
    if (vol != None) and (chan != None):
        chan.set_volume(vol)


def play_music(filename, loops = 0):
    """Start playing music from a file.
    
    Any previously playing music is stopped.  Optional argument
    loops indicates how many times to loop, -1 = keep looping forever,
    0 = play once, 1 = play once then repeat once, etc.
    """
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play(loops)

