import random
import pyglet
import pygame

pygame.init()

window = pyglet.window.Window(width=1024, height=768)
label = pyglet.text.Label('Hello, world',
                          font_name='Times New Roman',
                          font_size=36,
                          x=window.width//2, y=window.height//2,
                          anchor_x='center', anchor_y='center')
image = pyglet.resource.image('kitten.png')
tiles = pyglet.resource.image('tile_set_ground2.png')

class Transform:
    '''A 2D affine transformation plus alpha
    
    translatef - (x, y)
    scalef - factor
    rotatef - ang (degrees)
    alpha - 0.0 for blank, 1.0 for opaque

    '''
    def __init__(self):
        self.translatef = [0.0, 0.0]
        self.scalef = 1.0
        self.rotatef = 0.0
        self.alpha = 1.0
        self.smooth = True # when zoomed in, interpolate pixels
    def translate(self, x, y):
        self.translatef[0] += x
        self.translatef[1] += y
    def scale(self, s):
        self.scalef *= s
    def rotate(self, ang):
        self.rotatef += ang
    def fade(self, fact):
        self.alpha *= fact # fade to transparent
        if self.alpha > 1.0: self.alpha = 1.0

class TextureEnableGroup(pyglet.graphics.Group):
    '''A graphical group that enables texturing of the given type'''
    def __init__(self, target, parent=None):
        super(TextureEnableGroup, self).__init__(parent=parent)
        self.target = target
    def set_state(self):
        pyglet.gl.glEnable(self.target)
    def unset_state(self):
        pyglet.gl.glDisable(self.target)
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.target == other.target)

class TextureBindGroup(pyglet.graphics.Group):
    '''A graphical group that binds a specific texture'''        
    def __init__(self, texture, smooth=True, parent=None):
        super(TextureBindGroup, self).__init__(parent=parent)
        self.texture = texture
        self.smooth = smooth
    def set_state(self):
        pyglet.gl.glBindTexture(self.texture.target, self.texture.id)
        blend_mode = pyglet.gl.GL_NEAREST
        if self.smooth: blend_mode = pyglet.gl.GL_LINEAR
        pyglet.gl.glTexParameteri(self.texture.target, 
            pyglet.gl.GL_TEXTURE_MAG_FILTER, blend_mode)
    # No unset_state required
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.texture == other.texture and
                self.smooth == other.smooth)

class TransformGroup(pyglet.graphics.Group):
    '''A graphical group that performas a transform'''
    def __init__(self, transform, depth=0, parent=None):
        super(TransformGroup, self).__init__(parent=parent)
        self.transform = transform
    def set_state(self):
        pyglet.gl.glPushMatrix()
        pyglet.gl.glTranslatef(self.transform.translatef[0], self.transform.translatef[1], 0.0)
        pyglet.gl.glScalef(self.transform.scalef, self.transform.scalef, 1.0)
        pyglet.gl.glRotatef(self.transform.rotatef, 0.0, 0.0, 1.0)
        pyglet.gl.glColor4f(1.0, 1.0, 1.0, self.transform.alpha)
    def unset_state(self):
        pyglet.gl.glPopMatrix()
        pyglet.gl.glColor4f(1.0, 1.0, 1.0, 1.0) # undo alpha for pyglet drawing
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.transform == other.transform and
                self.depth == other.depth)
    # Comparison for ordering based on depths
    # Higher depths are deeper into screen, drawn first
    def __cmp__(self, other):
        if (self.__class__ is not other.__class__): return 0
        return -cmp(self.depth, other.depth)

def texture_transform_group(texture, transform, smooth=True, depth=0):
    # Sequence: enable texturing, bind texture, do transform
    teg = TextureEnableGroup(target=texture.target)
    tbg = TextureBindGroup(texture=texture, smooth=smooth, parent=teg)
    ttg = TransformGroup(transform=transform, depth=depth, parent=tbg)
    return ttg

class TextureTransformGroup(pyglet.graphics.Group):
    def __init__(self, texture, transform=None, smooth=True, depth=0):
        pyglet.graphics.Group.__init__(self)
        self.texture = texture
        self.transform = transform
        self.smooth = smooth
        self.depth = depth
    def set_state(self):
        pyglet.gl.glEnable(self.texture.target)
        pyglet.gl.glBindTexture(self.texture.target, self.texture.id)
        if self.transform is not None:
            pyglet.gl.glColor4f(1.0, 1.0, 1.0, self.transform.alpha)
            pyglet.gl.glPushMatrix()
            pyglet.gl.glTranslatef(self.transform.translatef[0], self.transform.translatef[1], 0.0)
            pyglet.gl.glScalef(self.transform.scalef, self.transform.scalef, 1.0)
            pyglet.gl.glRotatef(self.transform.rotatef, 0.0, 0.0, 1.0)
        blend_mode = pyglet.gl.GL_NEAREST
        if self.smooth: blend_mode = pyglet.gl.GL_LINEAR
        pyglet.gl.glTexParameteri(self.texture.target, 
            pyglet.gl.GL_TEXTURE_MAG_FILTER, blend_mode)
    def unset_state(self):
        if self.transform is not None:
            pyglet.gl.glPopMatrix()
        pyglet.gl.glDisable(self.texture.target)
    # Equality allows efficient concatenation of same textures
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.texture == other.__class__)
    # Comparison for ordering based on depths
    def __cmp__(self, other):
        if (self.__class__ is not other.__class__): return 0
        return -cmp(self.depth, other.depth)

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
    def __init__(self):
        self.image = None
        self.offset = (0, 0)
        self.size = (32, 32)
        self.sep = (0, 0)
    def lookup(self, n):
        yi = n // 1000
        xi = n % 1000
        x = self.offset[0] + (self.size[0] + self.sep[0]) * xi
        y = self.offset[1] + (self.size[1] + self.sep[1]) * yi
        return (x, self.image.height - y)
    
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
    def __init__(self):
        self.tileset = None
        self.tiles = []
        self.transform = Transform()
        self.depth = 50 # somewhat deep
        self._group = None
        self._vertex_list = None
        return
    def generate(self, batch=None):
        '''Add drawing commands to given batch operation
        
        If they were already added, modify existing ones to reflect 
        updated data.

        '''
        self._group = texture_transform_group(
            texture=self.tileset.image,
            transform=self.transform,
            smooth=False,
            depth=self.depth)
        v = []
        t = []
        sx, sy = self.tileset.size
        for tile in self.tiles:
            x, y = tile.pos
            tx, ty = self.tileset.lookup(tile.n)
            v.extend((x, y, x, y + sy, x + sx, y + sy, x + sx, y))
            t.extend((tx, ty, tx, ty - sy, tx + sx, ty - sy, tx + sx, ty))
        if self._vertex_list is None:
            self._vertex_list = batch.add(
                4 * len(self.tiles), pyglet.gl.GL_QUADS, self._group,
                ('v2f', v), ('t2f', t))
        else:
            self._vertex_list.resize(4 * len(self.tiles))
            self._vertex_list.vertices = v
            self._vertex_list.tex_coords = t
            

class Background:
    '''Represents a layer of level background that is a single image
    
    image
    transform - offset, scale, rotation, alpha
    '''
    def __init__(self):
        self.transform = Transform()
        self.depth = 99 # deep
        self._group = None
        self._vertex_list = None
        return
    def generate(self, batch=None):
        '''Add drawing commands to given batch operation
        
        If they were already added, modify existing ones to reflect 
        updated data.

        '''
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
                ('v2f/static', v), ('t2f/static', t))
        else:
            self._vertex_list.vertices = v
            self._vertex_list.tex_coords = t
            
class Room:
    '''Represents a single room (i.e. level) of a game
    
    '''
    def __init__(self):
        self.backgrounds = []
        self.layers = []
        self.transform = Transform()
    def generate(self, batch=None):
        for bg in self.backgrounds:
            bg.generate(batch=batch)
        for l in self.layers:
            l.generate(batch=batch)
    
bg = Background()
bg.image = pyglet.resource.image('kitten.png')
bg.transform.scale(10.0)

ts = TileSet()
ts.image = pyglet.resource.image('tile_set_ground2.png')
ts.offset = (0, 0)
ts.size = (32, 32)
ts.sep = (2, 2)

tl = TileLayer()
tl.tileset = ts
tl.transform = Transform()
#tl.transform.rotate(45.0)
tl.transform.translate(300.0, 50.0)
tl.transform.scale(1.0)
tl.transform.alpha = 0.8
tl.tiles = []
for x in range(20):
    for y in range(20):
        if random.randint(0, 100) < 50:
            tl.tiles.append(Tile(random.choice([0, 1, 5, 4000]), (x * 32, y * 32)))

rm = Room()
rm.backgrounds = [bg]
rm.layers = [tl]
batch = pyglet.graphics.Batch()
rm.generate(batch)

x = 5

clk = pygame.time.Clock()

#window.set_fullscreen(True)
window.set_vsync(False)

fps_display = pyglet.clock.ClockDisplay()

@window.event
def on_draw():
    global x
    window.clear()
    pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
    pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
    pyglet.gl.glMatrixMode(pyglet.gl.GL_PROJECTION)
    pyglet.gl.glLoadIdentity()
    pyglet.gl.glOrtho(0.0, 1024.0, 768.0, 0.0, -1.0, 1.0)
    pyglet.gl.glMatrixMode(pyglet.gl.GL_MODELVIEW)

    pyglet.gl.glLoadIdentity()
    batch.draw()
    
    pyglet.gl.glLoadIdentity()
    pyglet.gl.glScalef(1.0, -1.0, 1.0)
    pyglet.gl.glTranslatef(0.0, -768.0, 0.0)
    label.draw()
    fps_display.draw()

def update(dt):
    global x
    x += 2.0
    tl.transform.scale(1.001)
#    tl.transform.translate(2.0, 0.0)
#    tl.transform.rotate(0.1)
#    tl.transform.scale_around(2.0, 300.0, 50.0)
#    tl.transform.fade(0.99)
    if x > 30:
        tl.tiles[:1] = []
        tl.generate()
        x = 0
    clk.tick()


pyglet.clock.schedule_interval(update, 1.0/60.0)

pyglet.app.run()

