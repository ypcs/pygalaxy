"""A sprite behavior controls what happens to sprites on each tick.

Sprite behaviors are simple actions and ways of combining
behaviors into more complicated actions.  To do really
fancy things, you can create behaviors with your own
functions using DoFunc().
"""

import engine_util

class SpriteBehavior:
    """The default sprite behavior is to do nothing."""
    def __init__(self):
        """Create the sprite behavior."""
        pass
    def _do(self, spr):
        pass


class DoNothing(SpriteBehavior):
    """A sprite behavior that does nothing.
    
    Useful as an argument for other more complicated behaviors.
    """
    def _do(self, spr):
        pass


class DeleteSprite(SpriteBehavior):
    """Delete the sprite."""
    def _do(self, spr):
        spr.delete()


class DoFunc(SpriteBehavior):
    """Perform an arbitrary function as a behavior."""
    def __init__(self, func):
        """Create a sprite behavior that calls the given function."""
        self.func = func
    def _do(self, spr):
        self.func()


class RandomDirectionChanges(SpriteBehavior):
    """Randomly change directions sometimes."""
    def __init__(self, often=100, numdirs=8):
        """Create a sprite behavior that makes random direction changes.
        
        'often' controls how long to wait between direction changes,
        higher is longer, duration is randomized.
        'numdirs' indicates how many possible directions there
        are.  If numdirs = 4, then the choices are up, down, left, right.
        If numdirs = 8, there are also the diagonals.  Higher numbers
        give more choices.
        """
        self.often = often
        self.numdirs = numdirs
    def _do(self, spr):
        if engine_util.randint(1, self.often) == 1:
            spr.set_direction(engine_util.random_direction(self.numdirs))


class RandomTurns(SpriteBehavior):
    """Randomly turn sprite sometimes."""
    def __init__(self, often=100, numdirs=8, maxnum=2):
        """Create a sprite behavior that randomly turns sometimes.
        
        'often' controls how long to wait between turns, higher
        is longer, duration is randomly chosen.  
        'numdirs' indicates how many possible directions there
        are.  If numdirs = 4, then the choices are up, down, left, right.
        If numdirs = 8, there are also the diagonals.  Higher numbers
        give more choices.
        'maxnum' is the maximum turn left or right.
        
        If numdirs = 4 and maxnum = 1, then the sprite can go from
        up to right or left, or from right to up or down, etc..
        If numdirs = 360 and maxnum = 20, then the sprite can turn
        from -20 degrees to +20 degrees from its current direction.
        """
        self.often = often
        self.numdirs = numdirs
        self.maxnum = maxnum
    def _do(self, spr):
        if engine_util.randint(1, self.often) == 1:
            spr.set_direction(spr.direction + randint(-self.maxnum, self.maxnum) * (360 / self.numdirs))


class RandomLoops(SpriteBehavior):
    """Randomly turn sprite sometimes."""
    def __init__(self, often=100, angle=5):
        """Create a sprite behavior that loops in circles, randomly changing sometimes.

        'often' controls how long to wait between direction changes, higher
        is longer, duration is randomly chosen.  
        'angle' determines how tight the loops are
        """
        self.often = often
        self.angle = angle
    def _do(self, spr):
        if not hasattr(spr, 'turn_direction'):
            spr.turn_direction = (engine_util.randint(0, 1) * 2 - 1) * self.angle
        spr.set_direction(spr.direction + spr.turn_direction)
        if engine_util.randint(1, self.often) == 1:
            spr.turn_direction = -spr.turn_direction

class KeepOnscreen(SpriteBehavior):
    """When it moves offscreen, wrap around or push it back."""
    def __init__(self, wrap=True):
        self.wrap = wrap
    def _do(self, spr):
        o = spr.parent.offset
        bb = spr._get_physical_bbox()
        if bb:
            w, h = bb[0] / 2, bb[1] / 2
        else:
            w, h = 0, 0
        if self.wrap:
            if spr.pos[0] < o[0] - w: spr.pos[0] += 800
            if spr.pos[0] > o[0] + 800: spr.pos[0] -= 800
            if spr.pos[1] < o[1] - h: spr.pos[1] += 600
            if spr.pos[1] > o[1] + 600: spr.pos[1] -= 600
        else:
            if spr.pos[0] < o[0]: spr.pos[0] = o[0]
            if spr.pos[0] > o[0] + 800 - w: spr.pos[0] = o[0] + 800 - w
            if spr.pos[1] < o[1]: spr.pos[1] = o[1] - h
            if spr.pos[1] > o[1] + 600 - h: spr.pos[1] = o[1] + 600 - h


class WhenOffscreen(SpriteBehavior):
    """Do a sprite behavior when sprite is offscreen."""
    def __init__(self, behavior, distance=0):
        """Do a sprite behavior when sprite is offscreen.
        
        'behavior' is the behavior to do when offscreen.
        'distance' is how far offscreen the sprite must go before
        the behavior is triggered.
        """
        self.behavior = behavior
        self.distance = distance
    def _do(self, spr):
        o = spr.parent.offset
        if spr.pos[0] < o[0] - self.distance or spr.pos[1] < o[1] - self.distance or spr.pos[0] >= o[0] + engine_util.WIDTH + self.distance or spr.pos[1] >= o[1] + engine_util.HEIGHT + self.distance:
            self.behavior._do(spr)


class WhenCollide(SpriteBehavior):
    """Do sprite behavior when sprite collides with anything."""
    def __init__(self, behavior):
        """Do sprite behavior when sprite collides with anything.
        
        'behavior' is the behavior to do when offscreen.
        """
        self.behavior = behavior
    def _do(self, spr):
        cols = spr.get_collisions()
        if len(cols) > 0:
            self.behavior._do(spr)


class DoList(SpriteBehavior):
    """Do a list of sprite behaviors, one after the other."""
    def __init__(self, behaviors):
        """Create a sprite behavior that does a list of sprite behaviors.

        Behaviors are done in sequence, one after the other."""
        self.behaviors = behaviors
    def _do(self, spr):
        for b in self.behaviors:
            b._do(spr)
