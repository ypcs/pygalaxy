"""Graphics operations on the screen.

This is for drawing one frame.  For moving objects and animation,
use sprites.
"""

import pygame
import engine_util
import math
import Image, ImageSequence
import tempfile

screen = None

def start_graphics():
    global screen
    if engine_util.DEFAULT_FULLSCREEN:
        pygame.display.set_mode((engine_util.WIDTH, engine_util.HEIGHT), pygame.FULLSCREEN)
        engine_util.wait(2.0) # give some time for graphics card to resync with monitor
    else:
        pygame.display.set_mode((engine_util.WIDTH, engine_util.HEIGHT))
    screen = pygame.display.get_surface()
    pygame.mouse.set_visible(False)

def switch_to_fullscreen():
    """Switch display to fullscreen.

    Anything on display is erased and must be redrawn.
    On Macs, fullscreen is slightly jerkier than windowed mode.
    """
    global screen
    pygame.display.set_mode((engine_util.WIDTH, engine_util.HEIGHT), pygame.FULLSCREEN)
    #| HWSURFACE | DOUBLEBUF)
    screen = pygame.display.get_surface()
    engine_util.wait(2.0)

def flip():
    """Copy all drawing operations from memory to physical display.

    All drawing operations work on a buffer.  To see the results of
    drawing, use flip() to copy the buffer to the display.

    If you want you can do a flip() after every drawing operation
    to see the results of each operation.  Or, you can do one final
    call to flip() after all the drawing operations are done.
    """
    pygame.display.flip()

def load_image(filename, colorkey=None):
    """Load an image from a file and return it.

    If a colorkey color is specified, that color will be rendered as 
    transparent.  Only one transparent color is allowed per image.
    """
    res = pygame.image.load(filename).convert()
    res.set_colorkey(colorkey)
    return res

def load_images(filenames, colorkey=None):
    """Load a list of images from a list of filenames and return them.

    If a colorkey color is given, it applies to all the loaded images.
    """
    return [load_image(f, colorkey) for f in filenames]

def load_animated_gif(filename, colorkey=None):
    """Load a list of animation frames from a GIF file.
    
    If colorkey is not given, transparency of GIF is used.
    """
    # We have to work around a palette bug, after image 1, palette gets deleted
    img = Image.open(filename)
    try:
        transparency = img.info['transparency']
    except:
        transparency = None
    lut = img.resize((256, 1))
    lut.putdata(range(256))
    lut = lut.convert("RGB").getdata()
    pal = []
    for i in range(256): pal.extend(lut[i])
    res = []
    frame = img
    if transparency:
        if colorkey == None:
            colorkey = [253, 1, 254]
            pal[transparency * 3 : transparency * 3 + 3] = [253, 1, 254]
    for frame in ImageSequence.Iterator(img):
        frame.putpalette(pal)
        tmp = tempfile.mktemp() + ".png"
        frame.save(tmp)
        pygameimg = pygame.image.load(tmp).convert()
        if colorkey:
            pygameimg.set_colorkey(colorkey)
        else:
            if transparency:
                pygameimg.set_colorkey(pal[transparency * 3 : transparency * 3 + 3])
        res.append(pygameimg)
    return res
    
def subsection(surf, rect):
    """Return an extracted subsection of an image.

    Image must be an image value as returned from load_image, 
    not a filename.  The region to extract is given as a
    rectangle, (x, y, w, h).  If the original image had a transparent
    color, the same color will be transparent in the subsection.
    """
    res = pygame.Surface((rect[2], rect[3]))
    ck = surf.get_colorkey()
    surf.set_colorkey(None)
    res.blit(surf, (0, 0), rect)
    res.set_colorkey(ck)
    surf.set_colorkey(ck)
    return res

def subsections(surf, rects):
    """Return a list of extracted subsections from a single image.

    Rects is a list of rectangles to extract from the given image.
    The image must be an image value as returned from load_image, 
    not a filename.  If the original image had a transparent color,
    all the extracted subsections will have the same transparent
    color.
    """
    return [subsection(surf, r) for r in rects]

def blit(surf, where, ang=0):
    """Copy an image onto the screen.

    The location to draw the image is a coordinate pair, (x, y).
    Remember that all graphics operations operate on a buffer
    and must be followed by flip() to make them actually appear.
    Angle may be specified by ang, measured in degrees to rotate
    counterclockwise (negative angles are clockwise).
    """
    if ang == 0:
        screen.blit(surf, where)
    else:
        newsurf = pygame.transform.rotate(surf, ang)
        ox = newsurf.get_width() - surf.get_width()
        oy = newsurf.get_height() - surf.get_height()
        screen.blit(newsurf, [where[0] - ox / 2, where[1] - oy / 2])

def draw_background(c):
    """Draw the background underneath all layers.

    The base background appears underneath all the layers and
    is set to a solid color c.
    """
    screen.fill(c)

def fill_screen(color=(0, 0, 0)):
    """Fill the screen with a color (black by default)."""
    screen.fill(color)

def draw_rectangle(color, rect, width=0):
    """Draw a rectangle on the screen.

    If width is 0, fill the rectangle with color.
    If width > 0, rectangle lines are of the given color
    and rectangle is hollow.
    """
    pygame.draw.rect(screen, color, rect, width)

def draw_polygon(color, pointlist, width=0):
    """Draw a polygon on the screen.

    A polygon is a connected series of points.  If width is zero,
    fill the polygon with given color.  Otherwise draw lines
    connecting points in the given width with the given color and
    do not fill.
    """
    pygame.draw.polygon(screen, color, pointlist, width)

def draw_line(color, start, end, width=1):
    """Draw a line with the given color and width.

    Lines with width = 1 are antialiased, otherwise they are drawn
    normally.
    """
    if width == 1:
        pygame.draw.aaline(screen, color, start, end, 1)
    else:
        pygame.draw.line(screen, color, start, end, width)

def draw_thick_line(c, p1, p2, width=20):
    # figure out angle between points, add 90 degrees
    if p1 == p2: return
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0]) + 3.14159 / 2.0
    dx = math.cos(ang) * width / 2.0
    dy = math.sin(ang) * width / 2.0
    draw_polygon(c, [
        [p1[0] - dx, p1[1] - dy], 
        [p1[0] + dx, p1[1] + dy],
        [p2[0] + dx, p2[1] + dy],
        [p2[0] - dx, p2[1] - dy]
    ])


def draw_lines(color, point_list, closed=False, width=1):
    """Draw a sequence of connected lines.

    point_list - a list of coordinates for the lines
    closed - whether to draw line from last coord back to first
    width - if 1, lines will be antialiased, otherwise not
    """
    if width == 1:
        pygame.draw.aalines(screen, color, closed, point_list, 1)
    else:
        pygame.draw.lines(screen, color, closed, point_list, width)

def _linear(p0, p1, t):
    return (1.0 - t) * p0 + t * p1

def _quadbez(p0, p1, p2, t):
    return (1.0 - t) ** 2 * p0 + 2.0 * t * (1.0 - t) * p1 + t ** 2 * p2

def _catmull(p0, p1, p2, p3, t):
    return 0.5 * (2.0 * p1 + 
                  (-p0 + p2) * t + 
                  (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * (t ** 2) +
                  (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * (t ** 3))

def _floatrange(start, end, num):
    return [start + (end - start) * (t * 1.0 / num) for t in range(num + 1)]

def linear_path(pointlist, smoothness=20, loop=False):
    """Expand control points into a connected path between the points.

    smoothness - how many extra points to add between original control
      points
    loop - whether to go from last control point back to first

    If used as a sprite path, the speed of the sprite will be constant
    between any adjacent control points.  The total time between
    any adjacent points will always be the same, so sprites will
    move faster when points are spaced farther apart.
    """
    l = pointlist[:]
    if loop:
        l.append(pointlist[0])
    rng = _floatrange(0.0, 1.0, smoothness)
    res = []
    for i in range(len(l) - 1):
        coords = [[_linear(l[i][0], l[i + 1][0], t),
                   _linear(l[i][1], l[i + 1][1], t)]
                  for t in rng]
        res.extend(coords)
    return res

 
def smooth_path(pointlist, smoothness=20, loop=False):
    """Expand control points into a smooth path between the points.

    smoothness - this is an expansion factor, how many points to add
      between any two original points in the list
    loop - whether the path represents a loop

    If loop is true, the path will go from the first point all
    the way to the last point, then keep going back to the first
    point in a smooth way.  If loop is false, the path will just
    smoothly go from the first to the last point.

    If used as a sprite path, the speed of the sprite will not
    be constant, but will look reasonable.  The path slows down
    to go around corners, then speeds up on straightaways.
    The total time it takes to go between any two adjacent control
    points will be the same.  Control points placed farther apart
    will thus have faster motion.  More control points spaced
    close together will have slower motion.

    The resulting path will always go through all the control points.
    """
    if len(pointlist) < 2:
        raise KeyError
    if loop:
        l = [pointlist[-1]]
    else:
        l = [pointlist[0]]
    l.extend(pointlist)
    if loop:
        l.append(pointlist[0])
        l.append(pointlist[1])
    else:
        l.append(pointlist[-1])
    # loop=False
    # l is the same as pointlist with first and last elements duplicated
    # loop=True
    # l starts with point n, then points 1--n, then point 1
    rng = _floatrange(0.0, 1.0, smoothness)
    res = []
    for i in range(len(l) - 3):
        coords = [[_catmull(l[i][0], l[i + 1][0], l[i + 2][0], l[i + 3][0], t),
                   _catmull(l[i][1], l[i + 1][1], l[i + 2][1], l[i + 3][1], t)]
                  for t in rng]
        res.extend(coords)
    return res

# Cache loaded fonts at different sizes
_fonts = {}

def _get_font(font_filename, size):
    try:
        return _fonts[(font_filename, size)]
    except KeyError:
        fnt = pygame.font.Font(font_filename, size)
        _fonts[(font_filename, size)] = fnt
        return fnt

def render_text(txt, font_filename=engine_util.DEFAULT_FONT, size=32, color=(0, 0, 0)):
    fnt = _get_font(font_filename, size)
    """Render a single line of text into an image for blitting."""
    return fnt.render(txt, 1, color)

def _subwrap(txt, fnt, wid):
    """Given list of words, return pair of txt and list of remaining words,
    where txt is words that go up to wid but not past it."""
    res = ''
    while len(txt) > 0 and fnt.size(res)[0] + fnt.size(txt[0])[0] < wid:
        res += txt[0] + ' '
        txt = txt[1:]
    return res, txt

def _wrap(txt, fnt, wid):
    """Given list of words, return list of strings for lines (up to wid wide)."""
    res = []
    while len(txt) > 0:
        r, newtxt = _subwrap(txt, fnt, wid)
        res.append(r)
        if txt == newtxt: break
        txt = newtxt
    return res

def draw_text(txt, pos=(0,0), font_filename=engine_util.DEFAULT_FONT, size=32, color=(0, 0, 0), maxwidth=800):
    fnt = _get_font(font_filename, size)
    newtxt = txt.split('\n')
    for s in newtxt:
        for l in _wrap(s.split(' '), fnt, maxwidth):
            img = render_text(l, font_filename, size, color)
            blit(img, pos)
            pos[1] += fnt.get_linesize()
