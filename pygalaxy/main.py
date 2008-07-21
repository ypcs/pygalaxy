# Import pygame so we can use it
import pygame

# Directly import pygame constants, such as key names (e.g. K_LEFT)
# (less typing)
#from pygame.locals import *

import pygalaxy_util
import graphics
#import sprite
#import event

def init(width=pygalaxy_util.WIDTH, height=pygalaxy_util.HEIGHT, fullscreen=pygalaxy_util.DEFAULT_FULLSCREEN):
    """
    Start engine and set up a window for graphics drawing.

    This function must be called before any graphics can be drawn.
    Pygame only allows one window open at a time.  If this function
    is called more than once, it will resize the existing window.

    Keyword arguments:
    width -- width of window in pixels
    height -- height of window in pixels
    fullscreen -- if True will turn on fullscreen mode

    """
    # Start pygame, needed before we do anything else with pygame
    pygame.init()
    graphics.setup_graphics(width=width, height=height, fullscreen=fullscreen)
    #connect_to_joysticks()

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
    #event.handle_events()
    #sprite.update_sprites()
    if background_color:
        graphics.draw_background(background_color)
    #sprite.draw_sprites()
    #flip()
    _debug_fps += 1
    if _debug_fps > 50: #every 50 frames
        if SHOW_FPS: print clock.get_fps(), "FPS"
        _debug_fps = 0

# Export symbols
#__all__ = ['screen', 'tick', 'blit']
