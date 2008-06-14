# Import pygame so we can use it
import pygame

# Directly import pygame constants, such as key names (e.g. K_LEFT)
# (less typing)
from pygame.locals import *

from engine_util import *
from engine_graphics import *
from engine_sound import *
from engine_behaviors import *
from engine_sprites import *
from engine_events import *
from engine_network import *
from math import *

def start():
    """Start engine and open graphics screen for drawing."""
    # Start pygame, needed before we do anything else with pygame
    pygame.init()
    start_graphics()
    connect_to_joysticks()

# Start clock (used for fps calculations, timed events)
clock = pygame.time.Clock()

# Frames per second, will be constant throughout game
fps = 30.0

# For displaying actual
_debug_fps = 0

# Default background color
background_color = (0, 0, 0)

def set_background_color(c):
    global background_color
    background_color = c

def set_fps(fpsarg):
    global fps
    fps = fpsarg

def limit_fps(fps=fps):
    clock.tick(fps)
    for evt in pygame.event.get():
        if evt.type == QUIT: exit()
        if evt.type == KEYDOWN and evt.key == K_q and ((evt.mod & KMOD_META > 0) or (evt.mod & KMOD_CTRL > 0)):
            exit()

def calibrate_joystick():
    done = False
    while not done:
        draw_background([0, 0, 0])
        ang = get_joystick_direction()
        x, y = 0, 0
        if ang != None:
            x = math.cos(ang / 360.0 * 2 * 3.14159) * 50.0
            y = math.sin(ang / 360.0 * 2 * 3.14159) * 50.0
        c = [255, 255, 255]
        for a in range(0, 360, 90):
            draw_line(c, [400, 300], [
                400 + math.cos(a / 360.0 * 2 * 3.14159) * 80,
                300 + math.sin(a / 360.0 * 2 * 3.14159) * 80])
        draw_rectangle([255, 0, 0], [400 + x - 10, 300 + y - 10, 20, 20])
        for evt in pygame.event.get():
            if evt.type == QUIT: exit()
            if evt.type == KEYDOWN and evt.key == K_q and ((evt.mod & KMOD_META > 0) or (evt.mod & KMOD_CTRL > 0)):
                exit()
            if evt.type == JOYBUTTONDOWN:
                done = True
        flip()

def try_remove(lst, el):
    try:
        lst.remove(el)
    except:
        pass
        
def try_delete(spr):
    try:
        spr.delete()
    except:
        pass

def tick():
    """Update global engine state, advance one frame.

    Call this function once per frame.  This function
    redraws the screen, gets input, moves sprites,
    calls the sprite behavior functions, and animates
    sprites.  Call flip() after every tick().  You may
    draw to the screen after tick() draws all the sprites
    before calling flip().
    """
    global _debug_fps
    clock.tick(fps)
    handle_events()
    update_sprites()
    if background_color:
        draw_background(background_color)
    draw_sprites()
    #flip()
    _debug_fps += 1
    if _debug_fps > 50: #every 50 frames
        if SHOW_FPS: print clock.get_fps(), "FPS"
        _debug_fps = 0

# Export symbols
#__all__ = ['screen', 'tick', 'blit']
