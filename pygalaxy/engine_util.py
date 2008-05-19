"""Utility functions and constants in the game engine.

These constants and functions should generally not be needed to
write games or use the engine.  But they can be tweaked if necessary.
"""
# Import pygame so we can use it
import pygame

try:
    from engine_wiimote import close_wiimote
except:
    def close_wiimote(): pass

# Import some system libraries (needed for exit())
import sys
from random import randint

PI = 3.14159
DEG2RAD = 2.0 * PI / 360.0 # multiply by this to convert degrees to radians

# Graphics mode options
WIDTH = 800
HEIGHT = 600
DEFAULT_FULLSCREEN = False

# Whether to show bounding boxes for debugging
DRAW_BBOX = False
BBOX_COLOR = [0, 255, 0] # yellow

# periodically output frames per second
SHOW_FPS = True

# Which font to use if none specified
DEFAULT_FONT = "/COSMOS/gfx/fonts/Best19/Vera.ttf"

def exit():
    """Exit gracefully.

    Quits pygame so we get out of fullscreen mode
    and close all open windows.
    """
    close_wiimote()
    pygame.quit()
    sys.exit(0)

    
def angle_difference(a1, a2):
    """Calculate the smallest difference between two angles."""
    if a1 == None and a2 == None:
        return 0.0
    if a1 == None or a2 == None:
        return 180.0
    d = abs(a1 - a2)
    if d < 180.0: return d
    return 360.0 - d


def wait(t):
    """Pause t seconds.
    
    The argument can be a floating point number, like 0.001 for 1/1000
    of a second.  If you wait for a long time, you might have trouble
    closing the application.  Use force quit by pressing 
    command-option-escape if that happens.
    """
    pygame.time.wait(int(t * 1000))


def list_remove(lst, el):
    """Remove an element from a list.

    Modifies the original list.  Removes all copies of the element
    in case there are multiple copies.  Does not return an error
    if the element is not found, just leaves the list alone.
    """
    for i in range(len(lst)):
        while i < len(lst) and lst[i] == el:
            lst[i : i + 1] = []

def random_direction(numdirs):
    """Return a random direction out of numdirs equal divisions."""
    return randint(0, numdirs - 1) * (360 / numdirs)

def draw_bbox(d):
    global DRAW_BBOX
    DRAW_BBOX = d
