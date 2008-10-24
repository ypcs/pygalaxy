import random
import time
import sys
import math

import pyglet
from pyglet.media.drivers.openal import lib_openal as al
from pyglet.media.drivers.openal import lib_alc as alc

## Sound Functions

def pitch_from_midinum(m):
    '''Return pitch in Hz of midi note number

    Midi note numbers go from 0-127, middle C is 60.  Given a note number
    this function computes the frequency.  The return value is a floating
    point number.

    '''
    # formula from wikipedia on "pitch"
    if m is None: return None
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))

class Sound:
    def __init__(self, filename, streaming=False, recorded_pitch=None):
        self.snd = pyglet.resource.media(filename, streaming=streaming)
        self.recorded_pitch = recorded_pitch
    def play(self, loops=None, volume=1.0, pitch=1.0):
        '''Play the sound immediately
    
        Loops can be None for no looping,
        -1 for infinite looping, or a number for
        how many times to play the sound.
        
        Returns Player object for controlling sound during playback.

        '''
        if loops is None and volume == 1.0 and pitch == 1.0:
            self.snd.play()
        player = pyglet.media.Player()
        player.queue(self.snd)
        player.volume = volume
        player.pitch = pitch
        if loops == -1:
            player.eos_action = player.EOS_LOOP
        if loops is not None and loops > 0:
            for i in range(loops): player.queue(self.snd)
        player.play()
        return player
    def play_note(self, midi_pitch=60.0, loops=None, volume=1.0):
        '''Play a single note using this sound
        
        A note is a recorded sound sample of a single note that is speeded
        up or slowed down to make it the right pitch.  Returns player that
        can be used to control playback of the note (or discarded).
        
        Arguments:
          midi_pitch - which note to play, as a midinum 0-127 
          (can be floating point)
          loops - how many times to loop sound
          volume - volume to play sound at

        '''
        if self.recorded_pitch is None:
            self.recorded_pitch = 60.0 # assume sound is middle C
        pitch = pitch_from_midinum(midi_pitch) / pitch_from_midinum(self.recorded_pitch)
        return self.play(loops=loops, volume=volume, pitch=pitch)
    def __repr__(self):
        return 'abc'
        

## 2D transforms

class Transform:
    '''A 2D affine transformation plus alpha
    
    alpha - 0 is transparent, 1 is opaque
    smooth - True for linear interpolated pixels

    '''
    def __init__(self, translate=None, scale=None, rotate=None, alpha=1.0, smooth=True):
        if translate is None: self.translatef = [0.0, 0.0] 
        else: self.translatef = translate
        if scale is None: self.scalef = 1.0
        else: self.scalef = scale
        if rotate is None: self.rotatef = 0.0
        else: self.rotatef = rotate
        self.alpha = alpha
        self.smooth = smooth
    def translate(self, x, y):
        self.translatef[0] += x
        self.translatef[1] += y
    def scale(self, s):
        self.scalef *= s
    def rotate(self, ang):
        self.rotatef += ang
    def alpha_fade(self, fact):
        self.alpha *= fact # fade to transparent
        if self.alpha > 1.0: self.alpha = 1.0


class TextureEnableBindTransformGroup(pyglet.graphics.Group):
    '''A graphical group for drawing particular texture
    
    target - texture.target for a particular texture
    id - texture.id for some texture
    '''
    def __init__(self, target, id, transform, depth, parent=None):
        pyglet.graphics.Group.__init__(self, parent=parent)
#        super(TextureEnableBindTransformGroup, self).__init__(parent=parent)
        self.target = target
        self.id = id
        self.transform = transform
        self.depth = depth
    def set_state(self):
        pyglet.gl.glEnable(self.target)
        pyglet.gl.glBindTexture(self.target, self.id)
        blend_mode = pyglet.gl.GL_NEAREST
        if self.transform.smooth: blend_mode = pyglet.gl.GL_LINEAR
        pyglet.gl.glTexParameteri(self.target, 
            pyglet.gl.GL_TEXTURE_MAG_FILTER, blend_mode)
        pyglet.gl.glPushMatrix()
        pyglet.gl.glTranslatef(self.transform.translatef[0], self.transform.translatef[1], 0.0)
        pyglet.gl.glScalef(self.transform.scalef, self.transform.scalef, 1.0)
        pyglet.gl.glRotatef(self.transform.rotatef, 0.0, 0.0, 1.0)
        pyglet.gl.glColor4f(1.0, 1.0, 1.0, self.transform.alpha)
    def unset_state(self):
        pyglet.gl.glDisable(self.target)
        pyglet.gl.glPopMatrix()
        pyglet.gl.glColor4f(1.0, 1.0, 1.0, 1.0) # undo alpha for pyglet drawing
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.texture == other.texture and
                self.transform == other.transform and
                self.depth == other.depth)
    # Comparison for ordering based on depths
    # Higher depths are deeper into screen, drawn first
    def __cmp__(self, other):
        if (self.__class__ is not other.__class__): return 0
        return -cmp(self.depth, other.depth)

def pad_image_edges(img):
    res = pyglet.image.create(img.width + 2, img.height + 2)
    res_tex = res.get_texture()
    res_tex.blit_into(img, 1, 1, 0)
    res_tex.blit_into(img.get_region(0, 0, img.width, 1), 1, 0, 0)
    res_tex.blit_into(img.get_region(0, img.height-1, img.width, 1), 1, img.height + 1, 0)
    res_tex.blit_into(img.get_region(0, 0, 1, img.height), 0, 1, 0)
    res_tex.blit_into(img.get_region(img.width-1, 0, 1, img.height), img.width + 1, 1, 0)
    return res_tex.get_image_data()

class TileSet:
    '''Represents a tileset that is used to draw tiles for a level
    
    One image contains all tiles.  Start extracting tiles from offset,
    all tiles same size, tiles can be separated by sep space.  Origin
    is upper left of image (standard for image editors).
    
    image - Texture
    offset - (x, y)
    size - (w, h)
    sep - (x, y)
    '''
    def __init__(self, image=None, cols=1, rows=1, offset=(0, 0), size=(32, 32), sep=(0, 0)):
        self.image = image
        self.offset = offset
        self.size = size
        self.sep = sep
        self.rows = rows
        self.cols = cols
        self._bin = pyglet.image.atlas.TextureBin()
        self._images = {}
        self._target = None
        self._id = None
        for x in range(cols):
            for y in range(rows):
                tile_img = self.image.get_region(
                    self.offset[0] + (self.size[0] + self.sep[0]) * x,
                    self.image.height - (self.offset[1] + (self.size[1] + self.sep[1]) * y) - self.size[1],
                    self.size[0],
                    self.size[1])
                padded_tile_img = pad_image_edges(tile_img)
                #padded_tile_img = tile_img
                self._images[x, y] = self._bin.add(padded_tile_img)
                self._images[x, y] = self._images[x, y].get_region(1, 1, self.size[0], self.size[1])
                if self._target is None:
                    # We reuse the target and id between all tiles
                    # They are in an atlas, they must all be the same
                    t = self._images[x, y].get_texture()
                    self._target = t.target
                    self._id = t.id
    def lookup(self, x, y):
        return self._images[x, y].tex_coords
    
class Tile:
    '''A single tile
    
    pos - (x, y) pixel based
    n - number of tile
    '''
    def __init__(self, n, pos):
        self.n = n
        self.pos = pos
    
class TileLayer:
    '''Represents a layer of tiles for the level background
    
    tileset - TileSet  (all tiles in layer from same set)
    transform - offset, scale, rotation, alpha
    tiles - list of Tiles in layer
    depth - global graphical depth for stacking
    '''
    def __init__(self, tileset=None, tiles=None, transform=None, depth=50):
        self.tileset = tileset
        if tiles is None: self.tiles = []
        else: self.tiles = tiles
        if transform is None: self.transform = Transform(smooth=False)
        else: self.transform = transform
        self.depth = depth
        self._group = None
        self._vertex_list = None
    def generate(self, batch=None):
        '''Add drawing commands to given batch operation
        
        If they were already added, modify existing ones to reflect 
        updated data.

        '''
        self._group = TextureEnableBindTransformGroup(
            target=self.tileset._target,
            id=self.tileset._id,
            transform=self.transform,
            depth=self.depth)
        v = []
        t = []
        sx, sy = self.tileset.size
        for tile in self.tiles:
            x, y = tile.pos
            #tx, ty = self.tileset.lookup(tile.n)
            #v.extend((x, y, x, y + sy, x + sx, y + sy, x + sx, y))
            v.extend((x, y, 0, x + sx, y, 0, x + sx, y + sy, 0, x, y + sy, 0))
            #t.extend((tx, ty, tx, ty - sy, tx + sx, ty - sy, tx + sx, ty))
            t.extend(self.tileset.lookup(tile.n % 1000, tile.n / 1000))
        if self._vertex_list is None:
            self._vertex_list = batch.add(
                4 * len(self.tiles), pyglet.gl.GL_QUADS, self._group,
                ('v3f', v), ('t3f', t))
        else:
            self._vertex_list.resize(4 * len(self.tiles))
            self._vertex_list.vertices = v
            self._vertex_list.tex_coords = t

class Background:
    '''Represents a layer of level background that is a single image
    
    image
    transform - offset, scale, rotation, alpha
    tiled - tile infinitely every direction
    '''
    def __init__(self, image=None, transform=None, depth=99, tiled=False):
        self.image = image
        if transform is None: self.transform = Transform(smooth=True)
        else: self.transform = transform
        self.depth = depth
        self.tiled = tiled
        self._group = None
        self._vertex_list = None
    def generate(self, batch=None, world_coords=None):
        '''Add drawing commands to given batch operation
        
        If they were already added, modify existing ones to reflect 
        updated data.
        
        If background is tiled, must pass woord_coords so it knows
        where to draw copies of itself.
        '''
        self._texture = self.image.get_texture()
        self._group = TextureEnableBindTransformGroup(
            target=self._texture.target,
            id=self._texture.id,
            transform=self.transform,
            depth=self.depth)
        if not self.tiled:
            v = (0, 0, 0, self.image.width, 0, 0, self.image.width, self.image.height, 0, 0, self.image.height, 0)
            t = self._texture.tex_coords
            # v3f is float*float for vertices
            # t3f is float*float for texture coordinate
            # /static means assume doesn't change very often
            # (performance benefit, can be stored directly in video ram)
            if self._vertex_list is None:
                self._vertex_list = batch.add(4, pyglet.gl.GL_QUADS, self._group,
                    ('v3f/static', v), ('t3f/static', t))
            else:
                self._vertex_list.vertices = v
                self._vertex_list.tex_coords = t
        else:
            # Tiled case
            # Strategy: take world coords, untransform into object coords
            # Get rect that contains all coords
            # Calculate which tiles need to be drawn from that
            pnts = expand_rect(world_coords)
            pnts2 = [apply_invert_transform_point(self.transform, p) for p in pnts]
            bnd = biggest_rect(pnts2)
            mini = int(bnd[0] // self.image.width)
            maxi = int((bnd[0] + bnd[2]) // self.image.width + 1)
            minj = int(bnd[1] // self.image.height)
            maxj = int((bnd[1] + bnd[3]) // self.image.height + 1)
            n = (maxi - mini) * (maxj - minj)
            v = []
            t = []
            for i in range(mini, maxi):
                for j in range(minj, maxj):
                    x = i * self.image.width
                    y = j * self.image.height
                    v.extend([
                        x, y, 0, 
                        x + self.image.width, y, 0, 
                        x + self.image.width, y + self.image.height, 0, 
                        x, y + self.image.height, 0])
                    t.extend(self._texture.tex_coords)
            if self._vertex_list is None:
                self._vertex_list = batch.add(4 * n, pyglet.gl.GL_QUADS, self._group,
                    ('v3f/dynamic', v), ('t3f/dynamic', t))
            else:
                self._vertex_list.resize(4 * n)
                self._vertex_list.vertices = v
                self._vertex_list.tex_coords = t

def apply_transform_point(t, (x, y)):
    '''Apply a transform to a point (excluding alpha)'''
    # Order matters here: translate, scale, rotate
    a = t.rotatef / 360.0 * 2.0 * 3.14159
    x, y = math.cos(a) * x - math.sin(a) * y, math.sin(a) * x + math.cos(a) * y
    x, y = x * t.scalef, y * t.scalef
    x, y = x + t.translatef[0], y + t.translatef[1]
    return (x, y)

def apply_invert_transform_point(t, (x, y)):
    '''Apply the inverse of a transform to a point (excluding alpha)'''
    # Order matters here: translate, scale, rotate
    a = t.rotatef / 360.0 * 2.0 * 3.14159
    x, y = x - t.translatef[0], y - t.translatef[1]
    x, y = x / t.scalef, y / t.scalef
    x, y = math.cos(-a) * x - math.sin(-a) * y, math.sin(-a) * x + math.cos(-a) * y
    return (x, y)

#class Sprite:
    #'''Represents a single sprite, an animated graphical object
    
    #Note: sprites cannot draw themselves, they just hold image and
    #animation data.
    
    #Sprites have:
      #image - sprite sheet for animation
      #offset size sep num - how to extract subimages
      #anchor - relative to offset, where is image center
      #fps - speed of display
      #fps_mode - either 'absolute' or 'relative'
                 #means relative to speed of sprite's movement 
                 #(e.g. 0.5 = 1 frame per 2 pixels)
    #'''
    #def __init__(self):
        #self.image = None
        #self.offset = [0, 0]
        #self.size = [32, 32]
        #self.sep = [32, 0]
        #self.num = 1
        #self.anchor = [16, 16]
        #self.fps_mode = 'absolute'
        #self.fps = 24
        #self._frames = None
    #def generate_frames(self):
        #self._frames = [
           #[self.offset[0] + self.sep[0] * i, 
            #self.offset[1] + self.sep[1] * i, 
            #self.offset[0] + self.sep[0] * i + self.size[0], 
            #self.offset[1] + self.sep[1] * i + self.size[1]] 
            #for i in range(self.num)]
    #def get_frame(self, n):
        #if self._frames is None: self.generate_frames()
        #return self._frames[n]
    #def get_aabb(self, n):
        #return (0, 0, self.size[0], self.size[1])

# Bounding regions are either: circles OR axis aligned boxes
# (0, radius)
# (1, [left offset, bottom offset, right offset, top offset])

class GameObject:
    '''General game object (not a particular instance)
    
    Includes connection to sprite(s), bounding boxes, functions associated
    with game object.
    '''
    def __init__(self, sprite=None, bound=None, depth=0, speed=0, direction=0):
        self.sprite = sprite
        self.bound = bound
        self.depth = depth
        # speed and direction are just for initially created objects
        self.speed = speed
        self.direction = direction

class GameObjectInstance:
    '''An instance of a game object
    
    Must be created with parent that is general game object.
    '''
    def __init__(self, parent=None, pos=None, speed=0, direction=0):
        self.parent = parent
        self.pos = pos
        self.speed = speed
        self.direction = direction
        self._group = None
        self._texture = None
        self._vertex_list = None
        self._animated = False
        self._frame_index = 0

    def __del__(self):
        try:
            if self._vertex_list is not None:
                self._vertex_list.delete()
        except:
            pass

    def delete(self):
        '''Force immediate removal of the sprite from video memory.

        This is often necessary when using batches, as the Python garbage
        collector will not necessarily call the finalizer as soon as the
        sprite is garbage.
        '''
        if self._animated:
            clock.unschedule(self._animate)
        self._vertex_list.delete()
        self._vertex_list = None
        self._texture = None
        # Easy way to break circular reference, speeds up GC
        self._group = None

    def _animate(self, dt):
        self._frame_index += 1
        if self._frame_index >= len(self._animation.frames):
            self._frame_index = 0
            self.dispatch_event('on_animation_end')
            if self._vertex_list is None:
                return # Deleted in event handler.

        frame = self._animation.frames[self._frame_index]
        self._set_texture(frame.image.get_texture())

        if frame.duration is not None:
            duration = frame.duration - (self._next_dt - dt)
            duration = min(max(0, duration), frame.duration)
            clock.schedule_once(self._animate, duration)
            self._next_dt = duration
        else:
            self.dispatch_event('on_animation_end')

    def _create_vertex_list(self, batch=None):
        self._group = texture_transform_group(
            texture=self.image,
            transform=self.transform,
            smooth=True,
            depth=self.depth)
        v = (0, 0, 0, self.image.height, self.image.width, self.image.height, self.image.width, 0)
        t = (0, self.image.height, 0, 0, self.image.width, 0, self.image.width, self.image.height)
        # v2f is float*float for vertices
        # t2f is float*float for texture coordinate
        # /static means assume doesn't change very often
        # (performance benefit, can be stored directly in video ram)
        if self._vertex_list is None:
            self._vertex_list = batch.add(4, pyglet.gl.GL_QUADS, self._group,
                ('v2f/dynamic', v), ('t2f/dynamic', t))
        else:
            self._vertex_list.vertices = v
            self._vertex_list.tex_coords = t

class Viewport:
    '''A view into the game world on the physical screen
    '''
    def __init__(self, screen_pos=(0, 0), screen_size=(1024, 768), world_pos=(0, 0), world_size=(1024, 768)):
        '''
        screen_pos - where to draw the view in physical screen coordinates
        screen_size - size of view on physical screen
        world_pos - origin of world area to see in viewport
        world_size - size of world area to see in viewport
        
        If you make the screen_pos = (0, ) and screen_size = (1024, 768),
        you will fill the whole game window.  If you make the world_size
        smaller, the view will zoom in -- less of the world will fill
        the entire window.
        
        To do split screen, divide up the physical screen into regions
        and create a viewport for each physical region.  Then choose the
        world_pos and world_size to map to each region.

        '''
        self.screen_pos = screen_pos
        self.screen_size = screen_size
        self.world_pos = world_pos
        self.world_size = world_size

def biggest_rect(lst):
    '''Calculate largest rectangle containing a list of points
    
    Input is list of (x, y)
    Output is (x, y, w, h)
    '''
    l = lst[0][0]
    r = l
    d = lst[0][1]
    u = d
    for (x, y) in lst:
        if x < l: l = x
        if x > r: r = x
        if y < d: d = y
        if y > u: u = y
    return (l, d, r - l, u - d)

def expand_rect((x, y, w, h)):
    '''Expand rectangle into 4 points'''
    return [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
    
def biggest_world_rect(lst):
    '''Calculate largest rectangle containing a list of rects
    
    Input is list of (x, y, w, h)
    Output is (x, y, w, h)
    '''
    l = []
    for r in lst:
        l.extend(expand_rect(r))
    return biggest_rect(l)
    
class Room:
    '''Represents a single room (i.e. level) of a game
    
    '''
    def __init__(self, backgrounds=None, layers=None, transform=None, views=None):
        if backgrounds is None: self.backgrounds = []
        else: self.backgrounds = backgrounds
        if layers is None: self.layers = []
        else: self.layers = layers
        if transform is None: self.transform = Transform()
        else: self.transform = transform
        if views is None: self.views = [Viewport()]
        else: self.views = views
        self._batch = None
    def generate(self, batch=None):
        wc = biggest_world_rect([
            (v.world_pos[0], v.world_pos[1], v.world_size[0], v.world_size[1]) 
            for v in self.views])
        for bg in self.backgrounds:
            bg.generate(batch=batch, world_coords=wc)
        for l in self.layers:
            l.generate(batch=batch)
    def draw(self):
        if self._batch is None:
            self._batch = pyglet.graphics.Batch()
        self.generate(batch=self._batch)
        for v in self.views:
            pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
            pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
            pyglet.gl.glMatrixMode(pyglet.gl.GL_PROJECTION)
            pyglet.gl.glLoadIdentity()
            pyglet.gl.glOrtho(
                v.world_pos[0], v.world_pos[0] + v.world_size[0], 
                v.world_pos[1], v.world_pos[1] + v.world_size[1], -1.0, 1.0)
            pyglet.gl.glViewport(
                v.screen_pos[0], v.screen_pos[1],
                v.screen_size[0], v.screen_size[1])
            pyglet.gl.glMatrixMode(pyglet.gl.GL_MODELVIEW)
            pyglet.gl.glLoadIdentity()
            pyglet.gl.glClearColor(0.0, 0.0, 0.0, 0.0)
            pyglet.gl.glClear(pyglet.gl.GL_COLOR_BUFFER_BIT)
            self._batch.draw()

class Transition:
    def __init__(self, from_image=None, to_image=None, duration=1.0, rate=1.0/60.0):
        self.from_image = from_image
        self.to_image = to_image
        self.duration = duration
        self.rate = rate
        self.t = 0.0
        self.u = 0.0
        self.done = False
    def start(self, dt=0.0):
        pyglet.clock.schedule_interval(self.update, self.rate)
    def draw(self):
        pass
    def update(self, dt):
        self.t += dt
        self.u = self.t / self.duration
        if self.t > self.duration:
            self.done = True
            pyglet.clock.unschedule(self.update)

class FadeTransition(Transition):
    def __init__(self, *args, **kwargs):
        Transition.__init__(self, *args, **kwargs)
    def draw(self):
        # Draw destination image at 100% opaque
        if self.to_image is not None:
            pyglet.gl.glColor4f(1.0, 1.0, 1.0, 1.0)
            self.to_image.blit(0, 0)
        # Then draw transparent source image over top
        if self.from_image is not None:
            pyglet.gl.glColor4f(1.0, 1.0, 1.0, 1.0 - self.u)
            self.from_image.blit(0, 0)

class SlideOffTransition(Transition):
    def __init__(self, direction=(1, 0), *args, **kwargs):
        Transition.__init__(self, *args, **kwargs)
        self.direction = direction
    def draw(self):
        if self.to_image is not None:
            self.to_image.blit(0, 0)
        if self.from_image is not None:
            self.from_image.blit(self.u * 1024.0 * self.direction[0], self.u * 1024.0 * self.direction[1])

class SlideOnTransition(Transition):
    def __init__(self, direction=(1, 0), *args, **kwargs):
        Transition.__init__(self, *args, **kwargs)
        self.direction = direction
    def draw(self):
        if self.from_image is not None:
            self.from_image.blit(0, 0)
        if self.to_image is not None:
            self.to_image.blit(
                (1.0 - self.u) * 1024.0 * self.direction[0] * -1, 
                (1.0 - self.u) * 1024.0 * self.direction[1] * -1)


window = pyglet.window.Window(width=1024, height=768)

fbo = pyglet.gl.GLuint()
pyglet.gl.glGenFramebuffersEXT(1, fbo)



#bg = Background(image=pyglet.resource.image('test/kitten.png'), transform=Transform(scale=10.0))

ts = TileSet(image=pyglet.image.load('test/tile_set_ground2.png'), 
    cols=8, rows=2, offset=(0, 0), size = (32, 32), sep = (2, 2))
#ts = TileSet(image=pyglet.resource.image('test/tile_set_ground2.png'), 
#    cols=8, rows=12, offset=(0, 0), size = (32, 32), sep = (2, 2))

tl = TileLayer(tileset=ts, transform=Transform(translate=(300.0, 50.0), alpha=0.8, smooth=True), tiles=[])
for x in range(20):
    for y in range(20):
        if random.randint(0, 100) < 50:
            tl.tiles.append(Tile(random.choice([0, 1, 5, 1003]), (x * 32, y * 32)))

bg = Background(image=pyglet.image.load('test/kitten.png'), transform=Transform(scale=2.0), tiled=True)
bg2 = Background(image=pyglet.image.load('test/walk2.png'), transform=Transform(scale=5.0))

rm = Room(backgrounds=[bg], layers=[tl])
rm2 = Room(backgrounds=[bg2], layers=[])

#class SpriteSheet(pyglet.image.ImageGrid):
#    def __init__(self, image, num=1, offset=(0, 0), size=(48, 48), sep=0):
#        super(SpriteSheet, self).__init__(image, 1, num, 
#            item_width=size[0], item_height=size[1],
#            row_padding=0, column_padding=sep)

def sprite_sheet(image, num=1, offset=(0, 0), size=(48, 48), sep=0):
    return pyglet.image.TextureGrid(
        pyglet.image.ImageGrid(image, 1, num, 
          item_width=size[0], item_height=size[1],
          row_padding=0, column_padding=sep))

im = pyglet.resource.image('test/male_outline.png')
#im = pyglet.image.load('test/male
imgs = sprite_sheet(im, 7, (0, 539), (48, 48), 0)

sp = pyglet.sprite.Sprite(im)
sp.y = 100

x = 5

#window.set_fullscreen(True)
window.set_vsync(False)
window.set_fullscreen(True)

fps_display = pyglet.clock.ClockDisplay()

# Set up initial OpenGL state
# Enable alpha blending with normal blend mode
pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
# Modelview is for transforming model, not viewport
pyglet.gl.glMatrixMode(pyglet.gl.GL_MODELVIEW)
pyglet.gl.glLoadIdentity()

buf_manager = pyglet.image.get_buffer_manager()


tran = FadeTransition(duration=2.0, rate=1.0/500.0)
#tran = SlideOnTransition(direction=(1, 0), duration=2.0, rate=1.0/500.0)

def blah(dt):
    #window.dispatch_event('on_draw')
    window.invalid=True
    
pyglet.clock.schedule_interval(blah, 1.0/1000.0)

pyglet.clock.schedule_once(tran.start, 3.0)

@window.event
def on_draw():
    rm.draw()
    fps_display.draw()
    return
#    window.invalid=False
    global tran
    if tran.from_image is None:
        rm.draw()
        tran.from_image = buf_manager.get_color_buffer().get_texture()
    if tran.to_image is None:
        rm2.draw()
        tran.to_image = buf_manager.get_color_buffer().get_texture()
    window.clear()
 #   pyglet.gl.glBlendFunc(pyglet.gl.GL_ONE, pyglet.gl.GL_ZERO)
    tran.draw()
 #   pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
    fps_display.draw()
    #sp.draw()

def update(dt):
#    window.invalid=True
    global x
    x += 2.0
    rm.transform.rotate(0.1)
#    bg.transform.rotate(0.1)
#    tl.transform.scale(1.001)
#    tl.transform.translate(2.0, 0.0)
#    tl.transform.rotate(0.1)
#    tl.transform.scale_around(2.0, 300.0, 50.0)
#    tl.transform.fade(0.99)
#    if x > 30:
#        tl.tiles[:1] = []
#        rm.generate()
#        x = 0

snd = Sound('test/ah.wav')


@window.event
def on_key_release(k, mod):
    if k == pyglet.window.key.ENTER:
        snd.play_note(62.0)
#        play_song(ahwav, [(60, 1.0), (62, 1.0), (63, 1.0)])

#pyglet.clock.schedule_interval(recorder.tick, 1.0/60.0)
pyglet.clock.schedule_interval(update, 1.0/30.0)

pyglet.app.run()

