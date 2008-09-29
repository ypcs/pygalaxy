from __future__ import division

import sys
import math
import random

import pygame
from pygame.locals import *

class Object:
    pass

# Cartesian product
def cartprod(A, B):
    for a in A:
        for b in B:
            yield (a, b)

# cartprod([1,2], ['a', 'b']) generates (1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')
# To get all at once use list(cartprod(a,b))
# To use, say: for x in cartprod(a, b) ...

def add_elem(dct, elem):
    '''Add a key to a dict and set its value to a fresh sequential count'''
    if dct.has_key(elem): return
    n = len(dct)
    dct[elem] = n

def distance(a, b):
    return math.sqrt((a[0] - b[0]) ** 2.0 + (a[1] - b[1]) ** 2.0)

def poly_format(pth_lst, hole_lst=None):
    '''Generate .poly formatted data from a path'''
    if hole_lst is None: hole_lst = []

    def format(lst, fstr):
        tmp = []
        for x in lst:
            tmp.append(fstr % x)
        return ''.join(tmp)

    # Vertices
    # Each path is a list of vertices, closed back to beginning
    vrtx = {}
    # a dict that has points as keys, vertex num as values
    # Any key collisions don't matter, same point
    def add_path_vertices(p):
        for x in p:
            add_elem(vrtx, x)
    for p in pth_lst: add_path_vertices(p)
    for p in hole_lst: add_path_vertices(p)
    res = '%d 2 0 0\n' % len(vrtx)
    lst = [(vrtx[v], v[0], v[1]) for v in vrtx]
    lst.sort()
    res += format(lst, '%d %f %f\n')

    # Segments
    sgmnt = {}
    def add_path_segments(p):
        if len(p) == 0: return
        for i in range(len(p) - 1):
            sg = (vrtx[p[i]], vrtx[p[i+1]])
            add_elem(sgmnt, sg)
        sg = (vrtx[p[-1]], vrtx[p[0]])
        add_elem(sgmnt, sg)
    for p in pth_lst: add_path_segments(p)
    for p in hole_lst: add_path_segments(p)
    res += '%d 0\n' % len(sgmnt)
    lst = [(sgmnt[s], s[0], s[1]) for s in sgmnt]
    lst.sort()
    res += format(lst, '%d %d %d\n')

    # Holes
    holes = {}
    for p in hole_lst:
        # calculate average point in path for center
        x = 0.0
        y = 0.0
        for pnt in p:
            x += pnt[0]
            y += pnt[1]
        if len(p) > 0:
            x /= len(p)
            y /= len(p)
        add_elem(holes, (x, y))
    res += '%d\n' % len(holes)
    lst = [(holes[h], h[0], h[1]) for h in holes]
    lst.sort()
    res += format(lst, '%d %f %f\n')
    return res
    

random.seed(42)
pygame.init()

screen = pygame.display.set_mode((1024, 768))
clk = pygame.time.Clock()
lbutton = False
rbutton = False
mousepath = []
holepath = []
CMINDIST = 20.0

while True:
    clk.tick(20)
    screen.fill((240, 240, 240))
    if len(mousepath) > 1:
        pygame.draw.aalines(screen, (255, 0, 0), not lbutton, mousepath, 1)
    if len(holepath) > 1:
        pygame.draw.aalines(screen, (255, 0, 255), not rbutton, holepath, 1)
    pygame.display.flip()
    for evt in pygame.event.get():
        if evt.type == QUIT:
            sys.exit()
        if evt.type == MOUSEBUTTONDOWN:
            if evt.button == 1:
                mousepath = []
                lbutton = True
            if evt.button == 3:
                holepath = []
                rbutton = True
        if evt.type == MOUSEBUTTONUP:
            if evt.button == 1:
                lbutton = False
                print poly_format([mousepath], [holepath])
            if evt.button == 3:
                rbutton = False
                print poly_format([mousepath], [holepath])
        if evt.type == MOUSEMOTION:
            if lbutton:
                if len(mousepath) < 1 \
                        or distance(evt.pos, mousepath[-1]) > CMINDIST:
                    mousepath.append(evt.pos)
            if rbutton:
                if len(holepath) < 1 \
                        or distance(evt.pos, holepath[-1]) > CMINDIST:
                    holepath.append(evt.pos)
