import random
import math

class Particle:
    """Particles represent single points/sparks/splotches of color.
    
    Have following fields: pos, old_pos, vel, col, size, age
    """

def _RGB_of_HSV(h, s, v):
    if h < 0: h = 0
    if h > 360: h = 360
    if s < 0: s = 0
    if s > 1: s = 1
    if v < 0: v = 0
    if v > 1: v = 1
    if s == 0:
        return (v, v, v)
    h /= 60
    i = int(h) # color sector, 0 to 5
    f = h - i # position within sector
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    return (v, p, q)
def RGB_of_HSV(hsv):
    """Convert HSV to RGB.
    
    H is 0 - 360 (choose color)
    S is 0 - 1 (choose between monochrome, full color)
    V is 0 - 1 (choose how light or dark)
    
    Returns RGB in 0 - 255
    """
    cols = _RGB_of_HSV(hsv[0], hsv[1], hsv[2])
    return [int(c * 255.0) for c in cols]

class Emitter:
    """Emits particles according to predetermined parameters.
    
    Has one method, emit.
    """
    pass

class Spew(Emitter):
    def __init__(self, 
        pos=[0, 0], 
        maxnum=250, maxage=50, 
        source_distance=0.0, 
        size=1.0, size_variance=0.2, size_fade=0.9,
        kind='spark',
        rate=1.0, rate_variance=1.0, 
        speed=10.0, speed_variance=2.0, 
        gravity=0.0,
        color=[0, 1, 1], color_variance=[0, 0, 0], color_fade=[1, 1, 0.9]):
        self.pos = pos
        self.maxage = maxage
        self.maxnum = maxnum
        self.particles = []
        self.size = size
        self.size_variance = size_variance
        self.size_fade = (0.5) ** (1.0 / size_fade)
        self.kind = kind
        self.source_distance = source_distance
        self.rate = rate
        self.rate_variance = rate_variance
        self.speed = speed
        self.speed_variance = speed_variance
        self.gravity = gravity
        self.color = color
        self.color_variance = color_variance
        self.color_fade = [1] + [(0.5) ** (1.0 / x) for x in color_fade]
    def emit_one(self):
        sprk = Particle()
        x = random.gauss(self.pos[0], self.source_distance)
        y = random.gauss(self.pos[1], self.source_distance)
        sprk.pos = [x, y]
        sprk.old_pos = [x, y]
        sprk.size = random.gauss(self.size, self.size_variance)
        v = random.gauss(self.speed, self.speed_variance)
        a = random.randint(0, 999) / 1000.0 * 2.0 * 3.14159
        sprk.vel = [math.cos(a) * v, math.sin(a) * v]
        sprk.hsv_col = [random.gauss(self.color[i], self.color_variance[i]) for i in range(3)]
        sprk.col = RGB_of_HSV(sprk.hsv_col)
        sprk.age = 0
        return sprk
    def emit(self):
        num = int(random.gauss(self.rate, self.rate_variance))
        if num <= 0: return []
        return [self.emit_one() for i in range(num)]
    def tick(self):
        for p in self.particles:
            if self.kind == 'thick':
                draw_thick_line(p.col, p.old_pos, p.pos, width=p.size)
            if self.kind == 'thin':
                draw_line(p.col, p.old_pos, p.pos)
            if self.kind == 'point':
                draw_rectangle(p.col, [p.pos[0], p.pos[1], p.size, p.size])
            newpos = [p.pos[i] + p.vel[i] for i in range(2)]
            p.old_pos = p.pos
            p.pos = newpos
            p.vel = [p.vel[i] + self.gravity[i] for i in range(2)]
            p.age += 1
            p.hsv_col = [p.hsv_col[i] * self.color_fade[i] for i in range(3)]
            p.col = RGB_of_HSV(p.hsv_col)
            p.size *= self.size_fade
        for p in self.particles[:]:
            if p.age > self.maxage:
                self.particles.remove(p)
        newp = self.emit()
        self.particles.extend(newp)
        if len(self.particles) > self.maxnum:
            self.particles = self.particles[-self.maxnum:]

from engine_main import *
start()
set_fps(40.0)
switch_to_fullscreen()
spwer = Spew(
    pos=[400,300], 
    kind='point', 
    rate=5.0,
    size=5.0, size_variance=0.0, size_fade=10,
    speed=5.00, speed_variance=2.0, 
    gravity=[0, 0.5],
    color = [20, 1, 1],
    color_variance = [8, 0, 0],
    color_fade=[30,10])
def __test__():
    f = 0
    while True:
        f += 1
        tick()
        spwer.pos=[400 + cos(f / 30.0) * 200.0, 200]
        spwer.tick()
        flip()

__test__()

