"""
Sprites, animations, and default sprite behaviors.
"""

import math
import engine_util
import engine_graphics
from engine_behaviors import *
import sets
import pygame

_layers = []

def get_layers():
    """Return list of all layers (including invisible ones)."""
    # Don't use the global variable _layers.  If you use the 
    # global variable layers directly, it will not be kept 
    # up to date as you add and remove layers.
    # (Some weird issue with global variables across modules).
    return _layers

def update_sprites():
    """Update all sprites."""
    for lyr in _layers:
        if lyr.animated:
            lyr._update_sprites()

def draw_sprites():
    """Draw all sprites."""
    for lyr in _layers:
        if lyr.visible:
            lyr._draw_sprites()

def _intersecting_interval(i1, i2):
    """Given two intervals, determine if they overlap or not.

    Intervals are given as pairs of numbers on the real number line.
    Intervals are assumed to be closed on the left and 
    open on the right.  This means [1, 5] intersects with [4, 6],
    but [1, 5] does not intersect [5, 8].
    """
    if i2[0] + i2[1] < i1[0]: return False
    if i1[0] + i1[1] < i2[0]: return False
    return True


def _intersecting_rect(rect1, rect2):
    """Given two rectangles, determine if they overlap at all.

    If one rectangle is entirely contained in the other, they
    overlap.  Rectangles are closed on the left and top, and
    open on the right and bottom.  So [1, 1, 3, 3] intersects
    [2, 2, 4, 4], but [1, 1, 3, 3] does not intersect [3, 2, 4, 4].

    This function works by decomposing the 2D problem into 2 1D
    problems (intervals).  Rectangles overlap if their x intervals
    overlap AND their y intervals overlap.  Divide and conquer!
    """
    return (_intersecting_interval([rect1[0], rect1[2]], [rect2[0], rect2[2]])
            and _intersecting_interval([rect1[1], rect1[3]], [rect2[1], rect2[3]]))

def _intersecting_lines(l0, l1):
    x0, y0, x1, y1 = l0
    x2, y2, x3, y3 = l1
    denom = float((y3 - y2) * (x1 - x0) - (x3 - x2) * (y1 - y0))
    if denom == 0: return False
    num1 = (x3 - x2) * (y0 - y2) - (y3 - y2) * (x0 - x2)
    num2 = (x1 - x0) * (y0 - y2) - (y1 - y0) * (x0 - x2)
    ua = num1 / denom
    ub = num2 / denom
    return (0 <= ua < 1) and (0 <= ub < 1)

def _sort_layers():
    """Sort global layers based on depths."""
    global _layers
    dlayers = [(-l.depth, l) for l in _layers]
    dlayers.sort()
    _layers = [l[1] for l in dlayers]


class _Bin:
    """A bin keeps track of collections of 2d rectangles.

    You add and remove objects (sprites) from the bin quickly.  You can
    also give a rectangle and get a list of objects in the bin that might
    intersect or be inside your given rectangle.

    The purpose of using the bin is to increase performance of sprite
    drawing and collision detection.  We can just look at objects in the
    same divisions of the bin instead of looking at all objects.

    Games that use the engine should not need to access Bin objects
    directly.
    """
    size = None
    bin_size = None
    bin_dim = None
    bins = None
    extras = None

    def __init__(self, size=[10000, 10000], bin_size=[800, 600]):
        """Create new Bin with given maximum size and bin divisions.

        size - how big to make the bin
        bin_size - how big to make subdivisions of bin

        Objects outside of [0, 0, size[0], size[1]] can be put in
        the bin, it will just get inefficient really fast.

        Making bin_size the same as size means just have one big bin,
        so there will be no speedup.  Making bin_size too small
        means that we have to keep track of too many subdivisions,
        it will slow down the processing.  The ideal size divides
        up the size into a modest grid of subdivisions, where
        each subdivision is a reasonable size.  On my computer the
        optimal value is about 500x500.
        """
        self.resize_layer_bins(size, bin_size)
        self.extras = sets.Set()

    def resize_layer_bins(self, size, bin_size):
        """Reset size and subdivision size."""
        self.size = size
        self.bin_size = bin_size
        self.bin_dim = [self.size[i] / self.bin_size[i] for i in [0, 1]]
        self.bins = [[sets.Set() for i in range(self.bin_dim[1])] for j in range(self.bin_dim[0])]

    def _legal(self, x, y):
        """Determine if coordinate falls within bin at all."""
        if x < 0: return False
        if y < 0: return False
        if x >= self.bin_dim[0]: return False
        if y >= self.bin_dim[1]: return False
        return True

    def _xy_to_bin(self, x, y):
        """Return subdivision of bin containing x, y."""
        bx = int(x / self.bin_size[0])
        by = int(y / self.bin_size[1])
        if self._legal(bx, by):
            return self.bins[bx][by]
        return self.extras

    def add(self, x, y, spr):
        """Add an object to the bin at x, y."""
        self._xy_to_bin(x, y).add(spr)

    def remove(self, x, y, spr):
        """Remove an object from bin at position x, y."""
        self._xy_to_bin(x, y).remove(spr)

    def extract(self, rect):
        """Extract all objects that might be inside rect."""
        bx1 = int(rect[0] / self.bin_size[0])
        by1 = int(rect[1] / self.bin_size[1])
        bx2 = int((rect[0] + rect[2]) / self.bin_size[0])
        by2 = int((rect[1] + rect[3]) / self.bin_size[1])
        res = sets.Set(self.extras)
        for x in range(bx1, bx2 + 1):
            for y in range(by1, by2 + 1):
                if self._legal(x, y):
                    res = res.union(self.bins[x][y])
        return res


class Layer:
    """A layer is a virtual collection of sprites.

    Layers can be independently scrolled around.  For example,
    a layer can be a fixed background image, then another layer
    a platform world that scrolls with the action, then another
    layer is a fixed score display.  Sprites can collide with
    sprites from any layer.

    Layers speed up sprite processing by using bins.  The layer
    is divided into bins in a rectangular pattern.  Each bin contains
    a set of sprites.  To draw sprites, first the layer determines
    which bins appear on the screen.  Of those bins, all the sprites
    are drawn (some may actually be off screen, that's ok they will
    be clipped).

    There is a distinction between physical bounding boxes and logical
    bounding boxes.  For drawing on the screen we need to use physical
    bounding boxes; for determining collisions we use logical bounding
    boxes.
    """
    def __init__(self, depth = 0, offset = [0, 0], visible = True, animated = True, size = [10000, 10000], bin_size = [480, 480], slop = 50):
        """Create a new empty layer.

        depth - bigger is lower on screen, drawn underneath other layers
        offset - x and y offset for view into layer
                 [10, 0] means upper left corner of screen is at [10, 0] on layer
        visible - set to True to display layer, False to hide layer
        animated - True if sprites must be animated on this layer
           (set to False for background tile layers to speed up drawing)
        size - how big the layer is (can be larger than screen)
        bin_size - how to subdivide layer for faster performance
        slop - how far off screen to look for sprites to draw
    
        All the parameters are optional.  If you only have one layer, you
        probably don't need to set any parameters.  If you have several layers,
        you should at least set depth for each layer so they appear in the
        right order.

        animated, size, bin_size, and slop are all performance related.
        Start changing these to get faster screen drawing if your game is
        slowing down from too much graphics.  Set animated to False for
        layers that don't have any animated sprites, for example background
        layers.  The size of the layer and bin_size determine how to
        efficiently bin sprites to speed up display.  For maximum speed, set
        size to the correct size of the layer and experiment with bin_size
        settings between [100, 100] and [1000, 1000].  The slop setting
        should be set to the maximum size of sprites that will be appearing
        from offscreen.  If you have large sprites coming from offscreen, you
        may need to increase slop to avoid having them "pop" into view out of
        nowhere.
        """
        global _layers
        self.depth = depth
        self.offset = offset
        self.physical_bin = _Bin(size = size, bin_size = bin_size)
        self.logical_bin = _Bin(size = size, bin_size = bin_size)
        self.elements = sets.Set()
        self.animated = animated
        self.visible = visible
        self.slop = slop
        _layers.append(self)
        _sort_layers()

    def delete(self):
        """Delete this layer and all sprites it contains."""
        global _layers
        list_remove(_layers, self)
        for spr in self.elements:
            del spr
        del self

    def adjust_offset(self, dx, dy):
        """Adjust the viewing offset of this layer by [dx, dy]."""
        offset = [offset[0] + dx, offset[1] + dy]

    def _add(self, spr):
        self.elements.add(spr)
        self._bin_add(spr)

    def _bin_add(self, spr):
        self.physical_bin.add(spr.pos[0], spr.pos[1], spr)
        bbox = spr._get_logical_bbox()
        if bbox:
            self.logical_bin.add(spr.pos[0] + bbox[0], spr.pos[1] + bbox[1], spr)

    def _remove(self, spr):
        self.elements.remove(spr)
        self._bin_remove(spr)

    def _bin_remove(self, spr):
        self.physical_bin.remove(spr.pos[0], spr.pos[1], spr)
        bbox = spr._get_logical_bbox()
        if bbox:
            self.logical_bin.remove(spr.pos[0] + bbox[0], spr.pos[1] + bbox[1], spr)

    def _get_sprites_on_screen(self):
        """Return a set of sprites that might be on-screen."""
        return self.physical_bin.extract(
            [self.offset[0] - self.slop, self.offset[1] - self.slop, engine_util.WIDTH + self.slop, engine_util.HEIGHT + self.slop])

    def _get_possible_collisions(self, rect):
        """Return a set of sprites that might intersect with rect."""
        return self.logical_bin.extract([rect[0] - self.slop, rect[1] - self.slop, rect[2] + self.slop, rect[3] + self.slop])

    def _update_sprites(self):
        for spr in sets.Set(self.elements):
            spr._tick()

    def _draw_sprites(self):
        sprs = self._get_sprites_on_screen()
        sorted_sprites = [x for x in sprs]
        def f(el):
            return el.depth
        sorted_sprites.sort(key=f, reverse=True)
        for spr in sorted_sprites:
            spr._draw()
            if engine_util.DRAW_BBOX:
                spr._draw_bbox()

_default_layer = Layer(depth=1)
#_default_fixed_layer = Layer(depth=0)

def set_offset(xoff, yoff):
    """Set viewing offset of default layer.

    [0, 0] means no offset, will be same as screen coordinates.
    [100, 0] means shift so we see from [100, 0] to [900, 600].
    Can be negative or real numbers.
    """
    global _default_layer
    _default_layer.offset = [xoff, yoff]

def adjust_offset(dx, dy):
    """Adjust viewing offset of default layer.

    [0, 0] means don't change offset.
    [100, 0] means shift view right 100 pixels.
    Can be negative or real numbers.
    """
    global _default_layer
    _default_layer.offset = [_default_layer.offset[0] + dx,
                             _default_layer.offset[1] + dy]



class Anim:
    """An animation is a sequence of images displayed in succession."""

    def __init__(self, imgs=None, bboxen=None, rate=1.0, repeat=True, dir=0.0, bbox_pushin=0):
        """Create a new animation.

        imgs - list of images in animation
        bboxen - list of bounding boxes for images (optional)
        rate - how many frames of animation per game frame
          0.5 means slow down to half speed
        repeat - should images repeat in a loop (optional)
        dir - which direction of motion is associated with animation (optional)
        bbox_pushin - how much smaller to make bounding boxes than image edge
        (ignored if you give bounding boxes explicitly)

        Bounding boxes are used for collision detection between sprites.  If
        a sprite has None for a bounding box, it can't collide with anything.
        To get no bounding box, you have to put a list of Nones for the bboxen
        argument.  If you put None directly, the bounding boxes will be calculated
        automatically from the image sizes.  Use [None] * len(imgs).
        """
        self.pos = 0
        self.fps_count = 0
        if imgs:
            self.imgs = imgs
        else:
            self.imgs = []
        self.physical_bbox = [[img.get_width(), img.get_height()] for img in self.imgs]
        if bboxen:
            self.logical_bbox = bboxen
        else:
            self.logical_bbox = [[bbox_pushin, bbox_pushin, img.get_width() - 2 * bbox_pushin, img.get_height() - 2 * bbox_pushin] for img in self.imgs]
        self.rate = rate
        self.repeat = repeat
        self.direction = (dir + 360.0) % 360.0
        self.done = False

    def _get_anim_image(self):
        """Return current image of the animation."""
        return self.imgs[self.pos]

    def _get_anim_logical_bbox(self):
        """Return current bounding box of animation."""
        return self.logical_bbox[self.pos]

    def _get_anim_physical_bbox(self):
        """Return current physical bounding box of animation image."""
        return self.physical_bbox[self.pos]

    def _tick(self):
        """Advance animation by one frame.

        Should be called once per game frame.  May not advance
        actual frame of animation if rate is less than 1.
        """
        self.fps_count += 1.0
        while self.fps_count >= 1.0 / self.rate:
            self.fps_count -= 1.0 / self.rate
            self.pos += 1
            if self.pos >= len(self.imgs):
                if self.repeat:
                    self.pos = 0
                else:
                    self.pos = len(self.imgs) - 1
                    self.done = True

    def _rewind(self):
        """Start animation over from beginning."""
        self.pos = 0
        self.fps_count = 0
        self.done = False


class Sprite:
    """A sprite is any graphical object that persists for more
    than one frame.

    Sprites are composed of animations along with other record-keeping
    data like position, direction, and behavior.
    """
    def __init__(self, pos=[0, 0], direction=0, speed=0, anims=[], behavior=None, auto_direction_track=False, animate_when_stopped=False, depth=0, layer=None, absolute_position=False, rotate_image=False):
        """Create a new sprite.

        pos - position of sprite as (x, y) coordinate
        direction - initial direction as 360 angle
        speed - initial speed of sprite in pixels per second
        anims - list of animations for sprite
        behavior - sprite behavior associated with this sprite
        auto_direction_track - if True, automatically select animation 
            based on direction
        animate_when_stopped - if True, animation continues when speed is 0
        depth - drawing depth, bigger is deeper into screen (can be negative)
        layer - which layer to associate with sprite
        absolute_position - whether to fix sprite in absolute screen coordinates
          and float above relative sprites (e.g. score, player info)
        (only matters when you use set_offset() and don't give layer yourself)
        rotate_image - if True will rotate image to face direction
          assuming unrotated image is facing right

        Position, direction, and speed can be floating point.

        The behavior is a function that takes the sprite as the argument,
        then does something.  The behavior can move the sprite, delete it,
        create new sprites, make the game state change, etc..
        """
        self.pos = pos
        self.oldpos = pos[:]
        self.speed = speed
        self.anims = anims
        self.anim_seq = 0
        self.behavior = behavior
        self.auto_direction_track = auto_direction_track
        self.animate_when_stopped = animate_when_stopped
        self.set_direction(direction)
        if layer == None:
            if absolute_position:
                layer = _default_fixed_layer
            else:
                layer = _default_layer
        self.parent = layer
        self.depth = depth
        self.type = None
        self.physical_bbox = self._get_physical_bbox()
        self.logical_bbox = self._get_logical_bbox()
        self.rotate_image = rotate_image
        self.parent._add(self)

    def sync_with_bin(self):
        if self.pos != self.oldpos:
            newpos = self.pos
            self.pos = self.oldpos
            self.parent._bin_remove(self)
            self.pos = newpos
            self.parent._bin_add(self)
            self.oldpos = self.pos[:]

    def delete(self):
        """Delete the sprite."""
        self.sync_with_bin()
        if self.parent != None:
            self.parent._remove(self)
        del self

    def _get_anim(self):
        """Return current animation."""
        if self.anim_seq < len(self.anims):
            return self.anims[self.anim_seq]
        return None

    def set_behavior(self, b):
        """Set the sprite behavior.
    
        Argument b must be a SpriteBehavior object.
        """
        self.behavior = b

    def add_behavior(self, b):
        """Add an additional sprite behavior to this sprite."""
        old_b = self.behavior
        if old_b == None:
            self.behavior = b
        else:
            self.behavior = DoList([old_b, b])

    def set_direction(self, d):
        """Set direction of this sprite.

        If auto_direction_track is turned on, this also might
        change the animation of the sprite.
        """
        self.direction = (d + 360.0) % 360.0
        if self.auto_direction_track:
            # find closest associated direction in animations
            bestd = 0
            score = 361
            for i in range(len(self.anims)):
                a = self.anims[i]
                df = engine_util.angle_difference(d, a.direction)
                if df < score:
                    score = df
                    bestd = i
            self.anim_seq = bestd

    def set_pos(self, pos):
        """Update position of sprite."""
        self.pos = pos
        self.sync_with_bin()

    def set_direction_unit(self, d):
        """Set the direction of the sprite to d and set the speed to 1.

        If d is None, the direction will not be changed and speed
        will be set to 0.  This function is useful in combination
        with get_joystick_direction() and get_wii_direction().
        """
        if d != None:
            self.set_direction(d)
            self.speed = 1
        if d == None:
            self.speed = 0

    def is_anim_done(self):
        return self._get_anim().done
            
    def set_anim_frame(self, n):
        """Set the sprite animation frame for the current animation.
        """
        self._get_anim().pos = n
        self._get_anim().done = False

    def set_anim_seq(self, n):
        """Set the sprite on a given animation sequence.

        n is the position of the animation in the list originally
        given when the sprite was created (starts at 0).
        If sprite is already in this animation sequence, do not restart.
        """
        if self.anim_seq == n: return
        self.start_anim_seq(n)

    def start_anim_seq(self, n):
        """Start the sprite on a given animation sequence.

        n is the position of the animation in the list originally
        given when the sprite was created (starts at 0).
        """
        self.anim_seq = n
        self.anims[n]._rewind()

    def _get_image(self):
        a = self._get_anim()
        if a: return a._get_anim_image()
        return None

    def _get_logical_bbox(self):
        a = self._get_anim()
        if a: return a._get_anim_logical_bbox()
        return None

    def _get_physical_bbox(self):
        a = self._get_anim()
        if a: return a._get_anim_physical_bbox()
        return None

    def _tick(self):
        """Do internal actions for sprite.

        Includes movement, animation updating, binning updating,
        running sprite behavior.
        """
        dx = math.cos(self.direction * engine_util.DEG2RAD) * self.speed
        dy = math.sin(self.direction * engine_util.DEG2RAD) * self.speed
        newpos = [self.pos[0] + dx, self.pos[1] + dy]
        if (not (newpos == self.oldpos)) or (self.animate_when_stopped):
            self._get_anim()._tick()
            self.physical_bbox = self._get_physical_bbox()
            self.logical_bbox = self._get_logical_bbox()
            self.pos = newpos
        f = self.behavior
        if f != None:
            f._do(self)
        self.sync_with_bin()

    def is_colliding(self, other):
        if self.logical_bbox == None: return False
        if other.logical_bbox == None: return False
        bb1 = self.logical_bbox
        rect1 = [self.pos[0] + bb1[0] - self.parent.offset[0], 
                 self.pos[1] + bb1[1] - self.parent.offset[1], 
                 bb1[2], bb1[3]]
        bb2 = other.logical_bbox
        rect2 = [other.pos[0] + bb2[0] - other.parent.offset[0],
                 other.pos[1] + bb2[1] - other.parent.offset[1],
                 bb2[2], bb2[3]]
        # Now compare screen versions of rectangles
        return _intersecting_rect(rect1, rect2)

    def line_collide(self, l):
        bbox = self.logical_bbox[:]
        bbox[0] += self.pos[0]
        bbox[1] += self.pos[1]
        if _intersecting_lines([bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1]], l):
            return 1
        if _intersecting_lines([bbox[0], bbox[1] + bbox[3], bbox[0] + bbox[2], bbox[1] + bbox[3]], l):
            return 2
        if _intersecting_lines([bbox[0], bbox[1], bbox[0], bbox[1] + bbox[3]], l):
            return 3
        if _intersecting_lines([bbox[0] + bbox[2], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]], l):
            return 4
        return None
    
    def point_inside(self, p):
        bbox = self.logical_bbox[:]
        bbox[0] += self.pos[0]
        bbox[1] += self.pos[1]
        return bbox[0] <= p[0] < bbox[0] + bbox[2] and bbox[1] <= p[1] < bbox[1] + bbox[3]

    def reflect(self, angle):
        self.direction = (2 * angle - self.direction) % 360

    def get_collisions(self):
        """Return set of sprites that are in collision with sprite."""
        cols = sets.Set()
        if self.logical_bbox == None: return cols
        for lyr in _layers:
        #for lyr in [self.parent]:
            if lyr.visible:
                # Calculate all bounding boxes in screen coordinates
                # so we can compare them sanely
                bb1 = self.logical_bbox
                rect1 = [self.pos[0] + bb1[0] - self.parent.offset[0], 
                         self.pos[1] + bb1[1] - self.parent.offset[1], 
                         bb1[2], bb1[3]]
                # Calculate this screen rectangle on the lyr layer by adding offset
                srct = [rect1[0] + lyr.offset[0], 
                        rect1[1] + lyr.offset[1],
                        rect1[2], rect1[3]]
                sprs = lyr._get_possible_collisions(srct)
                # Now we have a short list of candidates
                for spr in sprs:
                    if spr != self:
                        bb2 = spr.logical_bbox
                        # Make sure it has bounding box
                        if bb2:
                            rect2 = [spr.pos[0] + bb2[0] - lyr.offset[0],
                                     spr.pos[1] + bb2[1] - lyr.offset[1],
                                     bb2[2], bb2[3]]
                            # Now compare screen versions of rectangles
                            if _intersecting_rect(rect1, rect2):
                                cols.add(spr)
        return cols

    def _draw(self):
        sx = int(self.pos[0] - self.parent.offset[0])
        sy = int(self.pos[1] - self.parent.offset[1])
        bbox = self._get_physical_bbox()
        if bbox == None: return
        if sx < engine_util.WIDTH:
            if sy < engine_util.HEIGHT:
                if sx + bbox[0] >= 0:
                    if sy + bbox[1] >= 0:
                        if self.rotate_image:
                            engine_graphics.blit(self._get_image(), (sx, sy), ang=-self.direction)
                        else:
                            engine_graphics.screen.blit(self._get_image(), (sx, sy))

    def _draw_bbox(self):
        sx = int(self.pos[0] - self.parent.offset[0])
        sy = int(self.pos[1] - self.parent.offset[1])
        bbox = self._get_logical_bbox()
        if bbox:
            pygame.draw.rect(engine_graphics.screen, engine_util.BBOX_COLOR, (bbox[0] + sx, bbox[1] + sy, bbox[2], bbox[3]), 1)


class SimpleSprite(Sprite):
    """A simple sprite just has one image instead of animations.

    Simple sprites don't generally move or change (e.g. a background tile).
    To move you must update the position manually with set_pos().
    To animate you must update the image with set_image().
    SimpleSprites do not have sprite behaviors.
    """
    def __init__(self, img=None, pos=(0, 0), bbox=-1, depth=0, layer=None, absolute_position=False, rotate_image=False):
        self.pos = pos
        self.img = img
        if img:
            self.physical_bbox = [img.get_width(), img.get_height()]
        else:
            self.physical_bbox = None
        if bbox == -1:
            if img:
                self.logical_bbox = [0, 0, img.get_width(), img.get_height()]
            else:
                self.logical_bbox = None
        else:
            self.logical_bbox = bbox
        if layer == None:
            if absolute_position:
                layer = _default_fixed_layer
            else:
                layer = _default_layer
        self.parent = layer
        self.depth = depth
        self.rotate_image = rotate_image
        self.oldpos = pos[:]
        layer._add(self)

    def set_image(self, img):
        """Set image for the sprite."""
        self.sync_with_bin()
        self.parent._bin_remove(self)
        self.img = img
        if img:
            self.physical_bbox = [img.get_width(), img.get_height()]
            self.logical_bbox = [0, 0, img.get_width(), img.get_height()]
        else:
            self.physical_bbox = None
            self.logical_bbox = None
        self.parent._bin_add(self)

    def _get_image(self):
        return self.img

    def set_bbox(self, bbox):
        """Set bounding box for the sprite."""
        self.logical_bbox = bbox

    def _get_logical_bbox(self):
        return self.logical_bbox

    def _get_physical_bbox(self):
        return self.physical_bbox

    def _tick(self):
        pass



