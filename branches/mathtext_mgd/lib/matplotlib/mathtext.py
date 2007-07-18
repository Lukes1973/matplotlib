r"""

OVERVIEW

  mathtext is a module for parsing TeX expressions and drawing them
  into a matplotlib.ft2font image buffer.  You can draw from this
  buffer into your backend.

  A large set of the TeX symbols are provided (see below).
  Subscripting and superscripting are supported, as well as the
  over/under style of subscripting with \sum, \int, etc.

  The module uses pyparsing to parse the TeX expression, an so can
  handle fairly complex TeX expressions Eg, the following renders
  correctly

  s = r'$\cal{R}\prod_{i=\alpha\cal{B}}^\infty a_i\rm{sin}(2 \pi f x_i)$'

  The fonts \cal, \rm, \it, and \tt are allowed.

  The following accents are provided: \hat, \breve, \grave, \bar,
  \acute, \tilde, \vec, \dot, \ddot.  All of them have the same
  syntax, eg to make an overbar you do \bar{o} or to make an o umlaut
  you do \ddot{o}.  The shortcuts are also provided, eg: \"o \'e \`e
  \~n \.x \^y

  The spacing elements \ , \/ and \hspace{num} are provided.  \/
  inserts a small space, and \hspace{num} inserts a fraction of the
  current fontsize.  Eg, if num=0.5 and the fontsize is 12.0,
  hspace{0.5} inserts 6 points of space



  If you find TeX expressions that don't parse or render properly,
  please email me, but please check KNOWN ISSUES below first.

REQUIREMENTS

  mathtext requires matplotlib.ft2font.  Set BUILD_FT2FONT=True in
  setup.py.  See BACKENDS below for a summary of availability by
  backend.

LICENSING:

  The computer modern fonts this package uses are part of the BaKoMa
  fonts, which are (now) free for commercial and noncommercial use and
  redistribution; see license/LICENSE_BAKOMA in the matplotlib src
  distribution for redistribution requirements.

USAGE:

  See http://matplotlib.sourceforge.net/tutorial.html#mathtext for a
  tutorial introduction.

  Any text element (xlabel, ylabel, title, text, etc) can use TeX
  markup, as in

    xlabel(r'$\Delta_i$')
           ^
        use raw strings

  The $ symbols must be the first and last symbols in the string.  Eg,
  you cannot do

    r'My label $x_i$'.

  but you can change fonts, as in

    r'$\rm{My label} x_i$'

  to achieve the same effect.

  A large set of the TeX symbols are provided.  Subscripting and
  superscripting are supported, as well as the over/under style of
  subscripting with \sum, \int, etc.


  Allowed TeX symbols:

  \/ \Delta \Downarrow \Gamma \Im \LEFTangle \LEFTbrace \LEFTbracket
  \LEFTparen \Lambda \Leftarrow \Leftbrace \Leftbracket \Leftparen
  \Leftrightarrow \Omega \P \Phi \Pi \Psi \RIGHTangle \RIGHTbrace
  \RIGHTbracket \RIGHTparen \Re \Rightarrow \Rightbrace \Rightbracket
  \Rightparen \S \SQRT \Sigma \Sqrt \Theta \Uparrow \Updownarrow
  \Upsilon \Vert \Xi \aleph \alpha \approx \angstrom \ast \asymp
  \backslash \beta \bigcap \bigcirc \bigcup \bigodot \bigoplus
  \bigotimes \bigtriangledown \bigtriangleup \biguplus \bigvee
  \bigwedge \bot \bullet \cap \cdot \chi \circ \clubsuit \coprod \cup
  \dag \dashv \ddag \delta \diamond \diamondsuit \div \downarrow \ell
  \emptyset \epsilon \equiv \eta \exists \flat \forall \frown \gamma
  \geq \gg \heartsuit \hspace \imath \in \infty \int \iota \jmath
  \kappa \lambda \langle \lbrace \lceil \leftangle \leftarrow
  \leftbrace \leftbracket \leftharpoondown \leftharpoonup \leftparen
  \leftrightarrow \leq \lfloor \ll \mid \mp \mu \nabla \natural
  \nearrow \neg \ni \nu \nwarrow \odot \oint \omega \ominus \oplus
  \oslash \otimes \phi \pi \pm \prec \preceq \prime \prod \propto \psi
  \rangle \rbrace \rceil \rfloor \rho \rightangle \rightarrow
  \rightbrace \rightbracket \rightharpoondown \rightharpoonup
  \rightparen \searrow \sharp \sigma \sim \simeq \slash \smile
  \spadesuit \sqcap \sqcup \sqrt \sqsubseteq \sqsupseteq \subset
  \subseteq \succ \succeq \sum \supset \supseteq \swarrow \tau \theta
  \times \top \triangleleft \triangleright \uparrow \updownarrow
  \uplus \upsilon \varepsilon \varphi \varphi \varrho \varsigma
  \vartheta \vdash \vee \vert \wedge \wp \wr \xi \zeta


BACKENDS

  mathtext currently works with GTK, Agg, GTKAgg, TkAgg and WxAgg and
  PS, though only horizontal and vertical rotations are supported in
  *Agg

  mathtext now embeds the TrueType computer modern fonts into the PS
  file, so what you see on the screen should be what you get on paper.

  Backends which don't support mathtext will just render the TeX
  string as a literal.  Stay tuned.


KNOWN ISSUES:

 - I would also like to add a few more layout commands, like \frac.

STATUS:
  The *Unicode* classes were incomplete when I found them, and have
  not been refactored to support intermingling of regular text and
  math text yet.  They are most likely broken. -- Michael Droettboom, July 2007
 
Author    : John Hunter <jdhunter@ace.bsd.uchicago.edu>
Copyright : John Hunter (2004,2005)
License   : matplotlib license (PSF compatible)

"""
from __future__ import division
import os, sys
from cStringIO import StringIO
from sets import Set

from matplotlib import verbose
from matplotlib.pyparsing import Literal, Word, OneOrMore, ZeroOrMore, \
     Combine, Group, Optional, Forward, NotAny, alphas, nums, alphanums, \
     StringStart, StringEnd, ParseException, FollowedBy, Regex, \
     operatorPrecedence, opAssoc, ParseResults, Or, Suppress, oneOf

from matplotlib.afm import AFM
from matplotlib.cbook import enumerate, iterable, Bunch, get_realpath_and_stat
from matplotlib.ft2font import FT2Font
from matplotlib.font_manager import fontManager, FontProperties
from matplotlib._mathtext_data import latex_to_bakoma, cmkern, \
        latex_to_standard, tex2uni, type12uni, tex2type1, uni2type1
from matplotlib.numerix import absolute
from matplotlib import get_data_path, rcParams

# symbols that have the sub and superscripts over/under
overunder = { r'\sum'    : 1,
              r'\int'    : 1,
              r'\prod'   : 1,
              r'\coprod' : 1,
              }
# a character over another character
charOverChars = {
    # The first 2 entires in the tuple are (font, char, sizescale) for
    # the two symbols under and over.  The third entry is the space
    # between the two symbols in points
    r'\angstrom' : (  ('rm', 'A', 1.0), (None, '\circ', 0.5), 0.0 ),
    }


def font_open(filename):
    ext = filename.rsplit('.',1)[1]
    if ext == 'afm':
        return AFM(str(filename))
    else:
        return FT2Font(str(filename))


def get_unicode_index(symbol):
    """get_unicode_index(symbol) -> integer

Return the integer index (from the Unicode table) of symbol.
symbol can be a single unicode character, a TeX command (i.e. r'\pi'),
or a Type1 symbol name (i.e. 'phi').

"""
    try:# This will succeed if symbol is a single unicode char
        return ord(symbol)
    except TypeError:
        pass
    try:# Is symbol a TeX symbol (i.e. \alpha)
        return tex2uni[symbol.strip("\\")]
    except KeyError:
        pass
    try:# Is symbol a Type1 name (i.e. degree)? If not raise error
        return type12uni[symbol]
    except KeyError:
        message = """'%(symbol)s' is not a valid Unicode character or
TeX/Type1 symbol"""%locals()
        raise ValueError, message


#Not used, but might turn useful
def get_type1_name(symbol):
    """get_type1_name(symbol) -> string

Returns the the Type1 name of symbol.
symbol can be a single unicode character, or a TeX command (i.e. r'\pi').

"""
    try:# This will succeed if symbol is a single unicode char
        return uni2type1[ord(symbol)]
    except TypeError:
        pass
    try:# Is symbol a TeX symbol (i.e. \alpha)
        return tex2type1[symbol.strip("\\")]
    except KeyError:
        pass
    # The symbol is already a Type1 name so return it
    if isinstance(symbol, str):
        return symbol
    else:
        # The user did not suply a valid symbol, show usage
        raise ValueError, get_type1_name.__doc__


class Fonts:
    """
    An abstract base class for fonts that want to render mathtext

    The class must be able to take symbol keys and font file names and
    return the character metrics as well as do the drawing
    """
    
    def get_kern(self, facename, symleft, symright, fontsize, dpi):
        """
        Get the kerning distance for font between symleft and symright.

        facename is one of tt, it, rm, cal or None

        sym is a single symbol(alphanum, punct) or a special symbol
        like \sigma.

        """
        return 0

    def get_metrics(self, facename, sym, fontsize, dpi):
        """
        facename is one of tt, it, rm, cal or None

        sym is a single symbol(alphanum, punct) or a special symbol
        like \sigma.

        fontsize is in points

        Return object has attributes - see
        http://www.freetype.org/freetype2/docs/tutorial/step2.html for
        a pictoral representation of these attributes

          advance
          height
          width
          xmin, xmax, ymin, ymax  - the ink rectangle of the glyph
          """
        raise NotImplementedError('Derived must override')

    def set_canvas_size(self, w, h):
        'Dimension the drawing canvas; may be a noop'
        self.width, self.height = w, h

    def render(self, ox, oy, facename, sym, fontsize, dpi):
        pass

    def get_used_characters(self):
        return {}
    
    
class DummyFonts(Fonts):
    'dummy class for debugging parser'
    def get_metrics(self, font, sym, fontsize, dpi):

        metrics = Bunch(
            advance  = 0,
            height   = 0,
            width    = 0,
            xmin = 0,
            xmax = 0,
            ymin = 0,
            ymax = 0,
            )
        return metrics


class UnicodeFonts(Fonts):
    """An abstract base class for handling Unicode fonts.

Specific terminology:
 * fontface: an FT2Font object, corresponding to a facename
 * facename: a string that defines the (type)face's name - 'rm', 'it' etc.
 * filename: a string that is used for generating a fontface object
 * symbol*: a single Unicode character or a TeX command,
    or to be precise, a TeX symbol command like \alpha (but not \frac) or
    even a Type1/PS name
 * filenamesd: a dict that maps the face's name to the filename:
    filenamesd = { 'cal' : 'fontnamecal.ext',
                  'rm'  : 'fontnamerm.ext',
                  'tt'  : 'fontnamett.ext',
                  'it'  : 'fontnameit.ext',
                  None  : 'fontnamesmth.ext'}
    filenamesd should be declared as a class atribute
 * glyphdict: a dict used for caching of glyph specific data
 * fonts: a dict of facename -> fontface pairs
 * charmaps: a dict of facename -> charmap pairs. Charmap maps character
   codes to glyph indices
 * glyphmaps: a dict of facename -> glyphmap pairs. A glyphmap is an
    inverted charmap
 * output: a string in ['Agg','SVG','PS'], coresponding to the backends
 * index: Fontfile specific index of a glyph.

"""

    # The path to the dir with the fontfiles
    def __init__(self, output='Agg'):
        self.facenames = self.filenamesd.keys()
        # Set the filenames to full path
        for facename in self.filenamesd:
            self.filenamesd[facename] = self.filenamesd[facename]
        if output:
            self.output = output
        # self.glyphdict[key] = facename, metrics, glyph, offset
        self.glyphdict = {}

        self.fonts = dict(
            [ (facename, font_open(self.filenamesd[facename])) for
                    facename in self.facenames])
        # a dict of charcode -> glyphindex pairs
        self.charmaps = dict(
            [ (facename, self.fonts[facename].get_charmap())
                for facename in self.facenames])
        # a dict of glyphindex -> charcode pairs
        self.glyphmaps = {}
        for facename in self.facenames:
            charmap = self.charmaps[facename]
            self.glyphmaps[facename] = dict([(glyphind, charcode)
                for charcode, glyphind in charmap.items()])
        for fontface in self.fonts.values():
            fontface.clear()
        if self.output == 'SVG':
            # a list of "glyphs" we need to render this thing in SVG
            self.svg_glyphs=[]

    def set_canvas_size(self, w, h, pswriter=None):
        'Dimension the drawing canvas; may be a noop'
        # self.width = int(w)
        # self.height = int(h)
        # I don't know why this was different than the PS version
        self.width = w
        self.height = h
        if pswriter:
            self.pswriter = pswriter
        else:
            for fontface in self.fonts.values():
                fontface.set_bitmap_size(int(w), int(h))

    def render(self, ox, oy, facename, symbol, fontsize, dpi):
        filename = self.filenamesd[facename]
        uniindex, metrics, glyph, offset = self._get_info(facename,
                                                    symbol, fontsize, dpi)
        if self.output == 'SVG':
            oy += offset - 512/2048.*10.
            # TO-DO - make a method for it
            # This gets the name of the font.
            familyname = self.fonts[facename].get_sfnt()[(1,0,0,1)]
            thetext = unichr(uniindex)
            thetext.encode('utf-8')
            self.svg_glyphs.append((familyname, fontsize, thetext, ox, oy,
                                                            metrics))
        elif self.output == 'PS':
            # This should be changed to check for math mode or smth.
            #if filename == 'cmex10.ttf':
            #    oy += offset - 512/2048.*10.

            # Get the PS name of a glyph (his unicode integer code)
            # from the font object
            symbolname = self._get_glyph_name(uniindex, facename)
            psfontname = self.fonts[facename].postscript_name
            ps = """/%(psfontname)s findfont
%(fontsize)s scalefont
setfont
%(ox)f %(oy)f moveto
/%(symbolname)s glyphshow
""" % locals()
            self.pswriter.write(ps)
        else: # Agg
            fontface = self.fonts[facename]
            fontface.draw_glyph_to_bitmap(
            int(ox),  int(self.height - oy - metrics.ymax), glyph)

    def get_metrics(self, facename, symbol, fontsize, dpi):
        uniindex, metrics, glyph, offset  = \
                self._get_info(facename, symbol, fontsize, dpi)
        return metrics

    # Methods that must be overridden for fonts that are not unicode aware

    def _get_unicode_index(self, symbol):
        return get_unicode_index(symbol)

    def _get_glyph_name(self, uniindex, facename):
        """get_glyph_name(self, uniindex, facename) -> string

Returns the name of the glyph directly from the font object.

"""
        font = self.fonts[facename]
        glyphindex = self.glyphmaps[facename][uniindex]
        return font.get_glyph_name(glyphindex)

    def _get_info(self, facename, symbol, fontsize, dpi):
        'load the facename, metrics and glyph'
        #print hex(index), symbol, filename, facename
        key = facename, symbol, fontsize, dpi
        tup = self.glyphdict.get(key)
        if tup is not None:
            return tup
        filename = self.filenamesd[facename]
        fontface = self.fonts[facename]
        fontface.set_size(fontsize, dpi)
        head  = fontface.get_sfnt_table('head')
        uniindex = self._get_unicode_index(symbol)
        glyphindex = self.glyphmaps[facename][uniindex]
        glyph = fontface.load_char(uniindex)
        xmin, ymin, xmax, ymax = [val/64.0 for val in glyph.bbox]
        # This is black magic to me (Edin)
        if filename == 'cmex10.ttf':
            if self.output == 'PS':
                offset = -(head['yMin']+512)/head['unitsPerEm']*10.
            else:
                offset =  glyph.height/64.0/2 + 256.0/64.0*dpi/72.0
        else:
            offset = 0.
        metrics = Bunch(
            advance  = glyph.linearHoriAdvance/65536.0,
            height   = glyph.height/64.0,
            width    = glyph.width/64.0,
            xmin = xmin,
            xmax = xmax,
            ymin = ymin+offset,
            ymax = ymax+offset,
            )
        self.glyphdict[key] = uniindex, metrics, glyph, offset
        return self.glyphdict[key]


class MyUnicodeFonts(UnicodeFonts):
    _initialized = False
    def __init__(self):
        if not MyUnicodeFonts._initialized:
            prop = FontProperties()
            prop.set_family('serif')
            self.rmfile = fontManager.findfont(prop)

            prop.set_family('fantasy')
            self.calfile = fontManager.findfont(prop)

            prop.set_family('monospace')
            self.ttfile = fontManager.findfont(prop)

            prop.set_family('serif')
            prop.set_style('italic')
            self.itfile = fontManager.findfont(prop)
            self.filenamesd = { 'rm'  : self.rmfile,
                                'it'  : self.itfile,
                                'cal' : self.calfile,
                                'tt'  : self.ttfile,
                                }
            MyUnicodeFonts._initialized = True


# TO-DO: pretty much everything
class BakomaUnicodeFonts(UnicodeFonts):
    """A class that simulates Unicode support in the BaKoMa fonts"""

    filenamesd = { 'cal' : 'cmsy10.ttf',
                'rm'  : 'cmr10.ttf',
                'tt'  : 'cmtt10.ttf',
                'it'  : 'cmmi10.ttf',
                'bf'  : 'cmb10.ttf',
                'sf'  : 'cmss10.ttf',
                None  : 'cmmi10.ttf',
                }

    # We override the UnicodeFonts methods, that depend on Unicode support
    def _get_unicode_index(self, symbol):
        uniindex = get_unicode_index(symbol)

    # Should be deleted
    def _get_glyph_name(self, uniindex, facename):
        """get_glyph_name(self, uniindex, facename) -> string

Returns the name of the glyph directly from the font object.
Because BaKoma fonts don't support Unicode, 'uniindex' is misleading

"""
        font = self.fonts[facename]
        glyphindex = self.glyphmaps[facename][uniindex]
        return font.get_glyph_name(glyphindex)

    def _get_info(self, facename, symbol, fontsize, dpi):
        'load the facename, metrics and glyph'
        #print hex(index), symbol, filename, facename
        key = facename, symbol, fontsize, dpi
        tup = self.glyphdict.get(key)
        if tup is not None:
            return tup
        filename = self.filenamesd[facename]
        fontface = self.fonts[facename]
        fontface.set_size(fontsize, dpi)
        head  = fontface.get_sfnt_table('head')
        uniindex = self._get_unicode_index(symbol)
        glyphindex = self.glyphmaps[facename][uniindex]
        glyph = fontface.load_char(uniindex)
        xmin, ymin, xmax, ymax = [val/64.0 for val in glyph.bbox]
        # This is black magic to me (Edin)
        if filename == 'cmex10.ttf':
            if self.output == 'PS':
                offset = -(head['yMin']+512)/head['unitsPerEm']*10.
            else:
                offset =  glyph.height/64.0/2 + 256.0/64.0*dpi/72.0
        else:
            offset = 0.
        metrics = Bunch(
            advance  = glyph.linearHoriAdvance/65536.0,
            height   = glyph.height/64.0,
            width    = glyph.width/64.0,
            xmin = xmin,
            xmax = xmax,
            ymin = ymin+offset,
            ymax = ymax+offset,
            )
        self.glyphdict[key] = uniindex, metrics, glyph, offset
        return self.glyphdict[key]


# TO-DO: Implement all methods
class CMUUnicodeFonts(UnicodeFonts):
    """A class representing Computer Modern Unicode Fonts, made by
Andrey V. Panov
panov /at/ canopus. iacp. dvo. ru
They are distributed under the X11 License.

"""


# Old classes

class BakomaFonts(Fonts):
    """
    Use the Bakoma true type fonts for rendering
    """
    # allocate a new set of fonts
    basepath = os.path.join( get_data_path(), 'fonts', 'ttf' )

    fontmap = { 'cal' : 'Cmsy10',
                'rm'  : 'Cmr10',
                'tt'  : 'Cmtt10',
                'it'  : 'Cmmi10',
                'bf'  : 'Cmb10',
                'sf'  : 'Cmss10',
                None  : 'Cmmi10',
                'ex'  : 'Cmex10'
                }

    class CachedFont:
        def __init__(self, font):
            self.font     = font
            self.charmap  = font.get_charmap()
            self.glyphmap = dict(
                [(glyphind, ccode) for ccode, glyphind in self.charmap.items()])
    
    def __init__(self):
        self.glyphd          = {}
        self.fonts           = {}
        self.used_characters = {}

    def _get_font(self, font):
        """Looks up a CachedFont with its charmap and inverse charmap.
        font may be a TeX font name (cal, rm, it etc.), a Computer Modern
        font name (cmtt10, cmr10, etc.) or an FT2Font object."""
        if isinstance(font, str):
            if font not in self.fontmap.values():
                basename = self.fontmap[font]
            else:
                basename = font
        else:
            basename = font.postscript_name

        cached_font = self.fonts.get(basename)
        if cached_font is None:
            if isinstance(font, str):
                font = FT2Font(os.path.join(self.basepath, basename.lower() + ".ttf"))
                basename = font.postscript_name
            cached_font = self.CachedFont(font)
            self.fonts[basename] = cached_font
        return basename, cached_font

    def get_fonts(self):
        return [x.font for x in self.fonts.values()]
        
    def get_metrics(self, font, sym, fontsize, dpi):
        basename, font, metrics, symbol_name, num, glyph, offset = \
                self._get_info(font, sym, fontsize, dpi)
        return metrics

    def _get_offset(self, basename, cached_font, glyph, fontsize, dpi):
        if basename.lower() == 'cmex10':
            return glyph.height/64.0/2 + 256.0/64.0*dpi/72.0
        return 0.
    
    def _get_info (self, font, sym, fontsize, dpi):
        'load the cmfont, metrics and glyph with caching'
        if hasattr(font, 'postscript_name'):
            fontname = font.postscript_name
        else:
            fontname = font
            
        key = fontname, sym, fontsize, dpi
        tup = self.glyphd.get(key)

        if tup is not None: return tup
        
        if font in self.fontmap and latex_to_bakoma.has_key(sym):
            basename, num = latex_to_bakoma[sym]
            basename, cached_font = self._get_font(basename.capitalize())
            symbol_name = cached_font.font.get_glyph_name(num)
            num = cached_font.glyphmap[num]
        elif len(sym) == 1:
            basename, cached_font = self._get_font(font)
            num = ord(sym)
            symbol_name = cached_font.font.get_glyph_name(cached_font.charmap[num])
        else:
            num = 0
            raise ValueError('unrecognized symbol "%s"' % sym)

        font = cached_font.font
        font.set_size(fontsize, dpi)
        glyph = font.load_char(num)

        realpath, stat_key = get_realpath_and_stat(font.fname)
        used_characters = self.used_characters.setdefault(
            stat_key, (realpath, Set()))
        used_characters[1].update(unichr(num))
        
        xmin, ymin, xmax, ymax = [val/64.0 for val in glyph.bbox]
        offset = self._get_offset(basename, cached_font, glyph, fontsize, dpi)
        metrics = Bunch(
            advance  = glyph.linearHoriAdvance/65536.0,
            height   = glyph.height/64.0,
            width    = glyph.width/64.0,
            xmin = xmin,
            xmax = xmax,
            ymin = ymin+offset,
            ymax = ymax+offset,
            )
        
        self.glyphd[key] = basename, font, metrics, symbol_name, num, glyph, offset
        return self.glyphd[key]

    def set_canvas_size(self, w, h):
        'Dimension the drawing canvas; may be a noop'
        self.width = int(w)
        self.height = int(h)
        for cached_font in self.fonts.values():
            cached_font.font.set_bitmap_size(int(w), int(h))

    def render(self, ox, oy, font, sym, fontsize, dpi):
        basename, font, metrics, symbol_name, num, glyph, offset = \
                self._get_info(font, sym, fontsize, dpi)

        font.draw_glyph_to_bitmap(
            int(ox),  int(self.height - oy - metrics.ymax), glyph)

    def _old_get_kern(self, font, symleft, symright, fontsize, dpi):
        """
        Get the kerning distance for font between symleft and symright.

        font is one of tt, it, rm, cal or None

        sym is a single symbol(alphanum, punct) or a special symbol
        like \sigma.

        """
        basename = self.fontmap[font]
        cmfont = self.fonts[basename]
        cmfont.set_size(fontsize, dpi)
        kernd = cmkern[basename]
        key = symleft, symright
        kern = kernd.get(key,0)
        #print basename, symleft, symright, key, kern
        return kern

    def get_used_characters(self):
        return self.used_characters
    
class BakomaPSFonts(BakomaFonts):
    """
    Use the Bakoma postscript fonts for rendering to backend_ps
    """

    def _get_offset(self, basename, cached_font, glyph, fontsize, dpi):
        head = cached_font.font.get_sfnt_table("head")
        if basename.lower() == 'cmex10':
            return -(head['yMin']+512)/head['unitsPerEm']*10.
        return 0.
    
    def set_canvas_size(self, w, h, pswriter):
        'Dimension the drawing canvas; may be a noop'
        self.width  = w
        self.height = h
        self.pswriter = pswriter

    def render(self, ox, oy, font, sym, fontsize, dpi):
        basename, font, metrics, symbol_name, num, glyph, offset = \
                self._get_info(font, sym, fontsize, dpi)
        if basename.lower() == 'cmex10':
            oy += offset - 512/2048.*10.

        ps = """/%(basename)s findfont
%(fontsize)s scalefont
setfont
%(ox)f %(oy)f moveto
/%(symbol_name)s glyphshow
""" % locals()
        self.pswriter.write(ps)

class BakomaPDFFonts(BakomaPSFonts):
    """Hack of BakomaPSFonts for PDF support."""

    def render(self, ox, oy, font, sym, fontsize, dpi):
        basename, font, metrics, symbol_name, num, glyph, offset = \
                self._get_info(font, sym, fontsize, dpi)
        filename = font.fname
        if basename.lower() == 'cmex10':
            oy += offset - 512/2048.*10.

        self.pswriter.append((ox, oy, filename, fontsize, num))

class BakomaSVGFonts(BakomaFonts):
    """Hack of BakomaFonts for SVG support."""
    def __init__(self):
        BakomaFonts.__init__(self)
        self.svg_glyphs = []
    
    def render(self, ox, oy, font, sym, fontsize, dpi):
        basename, font, metrics, symbol_name, num, glyph, offset = \
                self._get_info(font, sym, fontsize, dpi)

        oy += offset - 512/2048.*10.
        thetext = unichr(num)
        thetext.encode('utf-8')
        self.svg_glyphs.append((font, fontsize, thetext, ox, oy, metrics))

class StandardPSFonts(Fonts):
    """
    Use the standard postscript fonts for rendering to backend_ps
    """
    fnames = ('psyr', 'pncri8a', 'pcrr8a', 'pncr8a', 'pzcmi8a')
    # allocate a new set of fonts
    basepath = os.path.join( get_data_path(), 'fonts', 'afm' )

    fontmap = { 'cal' : 'pzcmi8a',  # Zapf Chancery
                'rm'  : 'pncr8a',   # New Century Schoolbook
                'tt'  : 'pcrr8a',   # Courier  
                'it'  : 'pncri8a',  # New Century Schoolbook Italic
                'sf'  : 'phvr8a',   # Helvetica
                'bf'  : 'pncb8a',   # New Century Schoolbook Bold
                None  : 'psyr'      # Symbol
                }

    def __init__(self):
        self.glyphd = {}
        self.fonts = {}

    def _get_font(self, font):
        if isinstance(font, str):
            if font not in self.fontmap.values():
                basename = self.fontmap[font]
            else:
                basename = font
        else:
            basename = font.get_fontname()

        cached_font = self.fonts.get(basename)
        if cached_font is None:
            if isinstance(font, str):
                fname = os.path.join(self.basepath, basename + ".afm")
                cached_font = AFM(file(fname, 'r'))
                cached_font.fname = fname
                basename = cached_font.get_fontname()
            else:
                cached_font = font
            self.fonts[basename] = cached_font
        return basename, cached_font

    def get_fonts(self):
        return [x.font for x in self.fonts.values()]
        
    def _get_info (self, font, sym, fontsize, dpi):
        'load the cmfont, metrics and glyph with caching'
        if hasattr(font, 'get_fontname'):
            fontname = font.get_fontname()
        else:
            fontname = font

        key = fontname, sym, fontsize, dpi
        tup = self.glyphd.get(key)

        if tup is not None:
            return tup

        if sym in "0123456789()" and font == 'it':
            font = 'rm'

        if latex_to_standard.has_key(sym):
            font, num = latex_to_standard[sym]
            glyph = chr(num)
        elif len(sym) == 1:
            glyph = sym
            num = ord(glyph)
        else:
            raise ValueError('unrecognized symbol "%s"' % (sym))
        basename, font = self._get_font(font)    
        
        try:
            symbol_name = font.get_name_char(glyph)
        except KeyError:
            raise ValueError('unrecognized symbol "%s"' % (sym))

        offset = 0

        scale = 0.001 * fontsize

        xmin, ymin, xmax, ymax = [val * scale
                                  for val in font.get_bbox_char(glyph)]
        metrics = Bunch(
            advance  = (xmax-xmin),
            width    = font.get_width_char(glyph) * scale,
            height   = font.get_width_char(glyph) * scale,
            xmin = xmin,
            xmax = xmax,
            ymin = ymin+offset,
            ymax = ymax+offset
            )

        self.glyphd[key] = basename, font, metrics, symbol_name, num, glyph, offset
        return self.glyphd[key]

    def set_canvas_size(self, w, h, pswriter):
        'Dimension the drawing canvas; may be a noop'
        self.width  = w
        self.height = h
        self.pswriter = pswriter

    def render(self, ox, oy, font, sym, fontsize, dpi):
        basename, font, metrics, symbol_name, num, glyph, offset = \
                self._get_info(font, sym, fontsize, dpi)
        ps = """/%(basename)s findfont
%(fontsize)s scalefont
setfont
%(ox)f %(oy)f moveto
/%(symbol_name)s glyphshow
""" % locals()
        self.pswriter.write(ps)


    def get_metrics(self, font, sym, fontsize, dpi):
        basename, font, metrics, symbol_name, num, glyph, offset = \
                self._get_info(font, sym, fontsize, dpi)
        return metrics

    def get_kern(self, font, symleft, symright, fontsize, dpi):
        basename, font1, metrics, symbol_name, num, glyph1, offset = \
                self._get_info(font, symleft, fontsize, dpi)
        basename, font2, metrics, symbol_name, num, glyph2, offset = \
                self._get_info(font, symright, fontsize, dpi)
        if font1.get_fontname() == font2.get_fontname():
            basename, font = self._get_font(font)
            return font.get_kern_dist(glyph1, glyph2) * 0.001 * fontsize
        return 0
    
class Element:
    fontsize = 12
    dpi = 72
    _padx, _pady = 2, 2  # the x and y padding in points
    _scale = 1.0

    def __init__(self):
        # a dict mapping the keys above, below, subscript,
        # superscript, right to Elements in that position
        self.neighbors = {}
        self.ox, self.oy = 0, 0

    def advance(self):
        'get the horiz advance'
        raise NotImplementedError('derived must override')

    def height(self):
        'get the element height: ymax-ymin'
        raise NotImplementedError('derived must override')

    def width(self):
        'get the element width: xmax-xmin'
        raise NotImplementedError('derived must override')

    def xmin(self):
        'get the xmin of ink rect'
        raise NotImplementedError('derived must override')

    def xmax(self):
        'get the xmax of ink rect'
        raise NotImplementedError('derived must override')

    def ymin(self):
        'get the ymin of ink rect'
        raise NotImplementedError('derived must override')

    def ymax(self):
        'get the ymax of ink rect'
        raise NotImplementedError('derived must override')

    def determine_font(self, font_stack):
        'a first pass to determine the font of this element (one of tt, it, rm , cal, bf, sf)'
        raise NotImplementedError('derived must override')

    def set_font(self, font):
        'set the font (one of tt, it, rm, cal, bf, sf)'
        raise NotImplementedError('derived must override')
    
    def render(self):
        'render to the fonts canvas'
        for element in self.neighbors.values():
            element.render()

    def set_origin(self, ox, oy):
        self.ox, self.oy = ox, oy

        # order matters! right needs to be evaled last
        keys = ('above', 'below', 'subscript', 'superscript', 'right')
        for loc in keys:
            element = self.neighbors.get(loc)
            if element is None: continue

            if loc=='above':
                nx = self.centerx() - element.width()/2.0
                ny = self.ymax() + self.pady() + (element.oy - element.ymax() + element.height())
                #print element, self.ymax(), element.height(), element.ymax(), element.ymin(), ny
            elif loc=='below':
                nx = self.centerx() - element.width()/2.0
                ny = self.ymin() - self.pady() - element.height()
            elif loc=='superscript':
                nx = self.xmax()
                ny = self.ymax() - self.pady()
            elif loc=='subscript':
                nx = self.xmax()
                ny = self.oy - 0.5*element.height()
            elif loc=='right':
                nx = self.ox + self.advance()
                if self.neighbors.has_key('subscript'):
                    o = self.neighbors['subscript']
                    nx = max(nx, o.ox + o.advance())
                if self.neighbors.has_key('superscript'):
                    o = self.neighbors['superscript']
                    nx = max(nx, o.ox + o.advance())

                ny = self.oy
            element.set_origin(nx, ny)

    def set_size_info(self, fontsize, dpi):
        self.fontsize = self._scale*fontsize
        self.dpi = dpi
        for loc, element in self.neighbors.items():
            if loc in ('subscript', 'superscript'):
                element.set_size_info(0.7*self.fontsize, dpi)
            else:
                element.set_size_info(self.fontsize, dpi)

    def pady(self):
        return self.dpi/72.0*self._pady

    def padx(self):
        return self.dpi/72.0*self._padx

    def set_padx(self, pad):
        'set the y padding in points'
        self._padx = pad

    def set_pady(self, pad):
        'set the y padding in points'
        self._pady = pad

    def set_scale(self, scale):
        'scale the element by scale'
        self._scale = scale

    def centerx(self):
        return 0.5 * (self.xmax() + self.xmin() )

    def centery(self):
        return 0.5 * (self.ymax() + self.ymin() )

    def __repr__(self):
        return str(self.__class__) + str(self.neighbors)

class FontElement(Element):
    def __init__(self, name):
        Element.__init__(self)
        self.name = name

    def advance(self):
        'get the horiz advance'
        return 0
        
    def height(self):
        'get the element height: ymax-ymin'
        return 0
        
    def width(self):
        'get the element width: xmax-xmin'
        return 0
        
    def xmin(self):
        'get the xmin of ink rect'
        return 0
        
    def xmax(self):
        'get the xmax of ink rect'
        return 0
        
    def ymin(self):
        'get the ymin of ink rect'
        return 0
        
    def ymax(self):
        'get the ymax of ink rect'
        return 0
        
    def determine_font(self, font_stack):
        font_stack[-1] = self.name

    def set_font(self, font):
        return
        
class SpaceElement(Element):
    'blank horizontal space'
    def __init__(self, space, height=0):
        """
        space is the amount of blank space in fraction of fontsize
        height is the height of the space in fraction of fontsize
        """
        Element.__init__(self)
        self.space = space
        self._height = height

    def advance(self):
        'get the horiz advance'
        return self.dpi/72.0*self.space*self.fontsize

    def height(self):
        'get the element height: ymax-ymin'
        return self._height*self.dpi/72.0*self.fontsize

    def width(self):
        'get the element width: xmax-xmin'
        return self.advance()

    def xmin(self):
        'get the minimum ink in x'
        return self.ox

    def xmax(self):
        'get the max ink in x'
        return self.ox + self.advance()

    def ymin(self):
        'get the minimum ink in y'
        return self.oy

    def ymax(self):
        'get the max ink in y'
        return self.oy + self.height()

    def determine_font(self, font_stack):
        # space doesn't care about font, only size
        for neighbor_type in ('above', 'below', 'subscript', 'superscript'):
            neighbor = self.neighbors.get(neighbor_type)
            if neighbor is not None:
                neighbor.determine_font(font_stack)

    def set_font(self, font_stack):
        # space doesn't care about font, only size
        pass
    
class SymbolElement(Element):
    hardcoded_font = False

    def __init__(self, sym):
        Element.__init__(self)
        self.sym = sym
        self.kern = None
        self.widthm = 1  # the width of an m; will be resized below

    def determine_font(self, font_stack):
        'set the font (one of tt, it, rm, cal, bf, sf)'
        self.set_font(font_stack[-1])
        for neighbor_type in ('above', 'below', 'subscript', 'superscript'):
            neighbor = self.neighbors.get(neighbor_type)
            if neighbor is not None:
                neighbor.determine_font(font_stack)
        
    def set_font(self, font, hardcoded=False):
        if hardcoded:
            self.hardcoded_font = True
            self.font = font
        if not self.hardcoded_font:
            assert not hasattr(self, 'font')
            self.font = font
        
    def set_origin(self, ox, oy):
        Element.set_origin(self, ox, oy)

    def set_size_info(self, fontsize, dpi):
        Element.set_size_info(self, fontsize, dpi)
        self.metrics = Element.fonts.get_metrics(
            self.font, self.sym, self.fontsize, dpi)

        mmetrics = Element.fonts.get_metrics(
            self.font, 'm', self.fontsize, dpi)
        self.widthm = mmetrics.width
        #print self.widthm

    def advance(self):
        'get the horiz advance'
        if self.kern is None:
            self.kern = 0
            if self.neighbors.has_key('right'):
                sym = None
                o = self.neighbors['right']
                if hasattr(o, 'sym'):
                    sym = o.sym
                elif isinstance(o, SpaceElement):
                    sym = ' '
                if sym is not None:
                    self.kern = Element.fonts.get_kern(
                        self.font, self.sym, sym, self.fontsize, self.dpi)
        return self.metrics.advance + self.kern
        #return self.metrics.advance # how to handle cm units?+ self.kern*self.widthm


    def height(self):
        'get the element height: ymax-ymin'
        return self.metrics.height

    def width(self):
        'get the element width: xmax-xmin'
        return self.metrics.width

    def xmin(self):
        'get the minimum ink in x'
        return self.ox + self.metrics.xmin

    def xmax(self):
        'get the max ink in x'
        return self.ox + self.metrics.xmax

    def ymin(self):
        'get the minimum ink in y'
        return self.oy + self.metrics.ymin

    def ymax(self):
        'get the max ink in y'
        return self.oy + self.metrics.ymax

    def render(self):
        'render to the fonts canvas'
        Element.fonts.render(
            self.ox, self.oy,
            self.font, self.sym, self.fontsize, self.dpi)
        Element.render(self)

    def __repr__(self):
        return self.sym

class AccentElement(SymbolElement):
    pass

class GroupElement(Element):
    """
    A group is a collection of elements
    """
    def __init__(self, elements):
        Element.__init__(self)
        if not isinstance(elements, list):
            elements = elements.asList()
        self.elements = elements
        for i in range(len(elements)-1):
            self.elements[i].neighbors['right'] = self.elements[i+1]

    def determine_font(self, font_stack):
        'set the font (one of tt, it, rm , cal)'
        font_stack.append(font_stack[-1])
        for element in self.elements:
            element.determine_font(font_stack)
        font_stack.pop()

    def set_font(self, font):
        return

    def set_size_info(self, fontsize, dpi):
        if len(self.elements):
            self.elements[0].set_size_info(self._scale*fontsize, dpi)
        Element.set_size_info(self, fontsize, dpi)
        #print 'set size'


    def set_origin(self, ox, oy):
        if len(self.elements):
            self.elements[0].set_origin(ox, oy)
        Element.set_origin(self, ox, oy)


    def advance(self):
        'get the horiz advance'
        if len(self.elements):
            return self.elements[-1].xmax() - self.elements[0].ox
        return 0


    def height(self):
        'get the element height: ymax-ymin'
        ymax = max([e.ymax() for e in self.elements])
        ymin = min([e.ymin() for e in self.elements])
        return ymax-ymin

    def width(self):
        'get the element width: xmax-xmin'
        xmax = max([e.xmax() for e in self.elements])
        xmin = min([e.xmin() for e in self.elements])
        return xmax-xmin

    def render(self):
        'render to the fonts canvas'
        if len(self.elements):
            self.elements[0].render()
        Element.render(self)

    def xmin(self):
        'get the minimum ink in x'
        return min([e.xmin() for e in self.elements])

    def xmax(self):
        'get the max ink in x'
        return max([e.xmax() for e in self.elements])

    def ymin(self):
        'get the minimum ink in y'
        return max([e.ymin() for e in self.elements])

    def ymax(self):
        'get the max ink in y'
        return max([e.ymax() for e in self.elements])

    def __repr__(self):
        return 'Group: [ %s ]' % ' '.join([str(e) for e in self.elements])

class MathGroupElement(GroupElement):
    def determine_font(self, font_stack):
        font_stack.append('it')
        for element in self.elements:
            element.determine_font(font_stack)
        font_stack.pop()

class NonMathGroupElement(GroupElement):
    def determine_font(self, font_stack):
        for element in self.elements:
            element.determine_font(font_stack)
        
class ExpressionElement(GroupElement):
    """
    The entire mathtext expression
    """

    def __repr__(self):
        return 'Expression: [ %s ]' % ' '.join([str(e) for e in self.elements])

    def determine_font(self, font_stack):
        GroupElement.determine_font(self, font_stack)

class Handler:
    symbols = []

    def clear(self):
        self.symbols = []

    def expression(self, s, loc, toks):
        #~ print "expr", toks
        self.expr = ExpressionElement(toks)
        return [self.expr]

    def math(self, s, loc, toks):
        #~ print "math", toks
        math = MathGroupElement(toks)
        return [math]

    def non_math(self, s, loc, toks):
        #~ print "non_math", toks
        # This is a hack, but it allows the system to use the
        # proper amount of advance when going from non-math to math
        s = toks[0] + ' '
        symbols = [SymbolElement(c) for c in s]
        self.symbols.extend(symbols)
        non_math = NonMathGroupElement(symbols)
        return [non_math]
    
    def space(self, s, loc, toks):
        assert(len(toks)==1)

        if toks[0]==r'\ ': num = 0.30 # 30% of fontsize
        elif toks[0]==r'\/': num = 0.1 # 10% of fontsize
        else:  # vspace
            num = float(toks[0][1]) # get the num out of \hspace{num}

        element = SpaceElement(num)
        self.symbols.append(element)
        return [element]

    def symbol(self, s, loc, toks):
        assert(len(toks)==1)
        #print "symbol", toks
        
        s  = toks[0]
        if charOverChars.has_key(s):
            under, over, pad = charOverChars[s]
            font, tok, scale = under
            sym = SymbolElement(tok)
            if font is not None:
                sym.set_font(font, hardcoded=True)
            sym.set_scale(scale)
            sym.set_pady(pad)

            font, tok, scale = over
            sym2 = SymbolElement(tok)
            if font is not None:
                sym2.set_font(font, hardcoded=True)
            sym2.set_scale(scale)

            sym.neighbors['above'] = sym2
            self.symbols.append(sym2)
        else:
            sym = SymbolElement(toks[0])
        self.symbols.append(sym)

        return [sym]

    def composite(self, s, loc, toks):

        assert(len(toks)==1)
        where, sym0, sym1 = toks[0]
        #keys = ('above', 'below', 'subscript', 'superscript', 'right')
        if where==r'\over':
            sym0.neighbors['above'] = sym1
        elif where==r'\under':
            sym0.neighbors['below'] = sym1

        self.symbols.append(sym0)
        self.symbols.append(sym1)

        return [sym0]

    def accent(self, s, loc, toks):

        assert(len(toks)==1)
        accent, sym = toks[0]

        d = {
            r'\hat'   : r'\circumflexaccent',
            r'\breve' : r'\combiningbreve',
            r'\bar'   : r'\combiningoverline',
            r'\grave' : r'\combininggraveaccent',
            r'\acute' : r'\combiningacuteaccent',
            r'\ddot'  : r'\combiningdiaeresis',
            r'\tilde' : r'\combiningtilde',
            r'\dot'   : r'\combiningdotabove',
            r'\vec'   : r'\combiningrightarrowabove',
            r'\"'     : r'\combiningdiaeresis',
            r"\`"     : r'\combininggraveaccent',
            r"\'"     : r'\combiningacuteaccent',
            r'\~'     : r'\combiningtilde',
            r'\.'     : r'\combiningdotabove',
            r'\^'   : r'\circumflexaccent',
             }
        above = AccentElement(d[accent])
        sym.neighbors['above'] = above
        sym.set_pady(1)
        self.symbols.append(above)
        return [sym]

    def function(self, s, loc, toks):
        #~ print "function", toks
        symbols = [FontElement("rm")]
        for c in toks[0]:
            sym = SymbolElement(c)
            symbols.append(sym)
            self.symbols.append(sym)
        return [GroupElement(symbols)]
    
    def group(self, s, loc, toks):
        assert(len(toks)==1)
        #print 'grp', toks
        grp = GroupElement(toks[0])
        return [grp]

    def font(self, s, loc, toks):
        assert(len(toks)==1)
        name = toks[0]
        #print 'fontgrp', toks
        font = FontElement(name)
        return [font]

    def latexfont(self, s, loc, toks):
        assert(len(toks)==1)
        name, grp = toks[0]
        if len(grp.elements):
            font = FontElement(name[4:])
            font.neighbors['right'] = grp.elements[0]
            grp.elements.insert(0, font)
            return [grp]
        return []
    
    _subsuperscript_names = {
        'normal':    ['subscript', 'superscript'],
        'overUnder': ['below', 'above']
    }

    _subsuperscript_indices = {
        '_': (0, 1),
        '^': (1, 0)
    }
         
    def subsuperscript(self, s, loc, toks):
        assert(len(toks)==1)
        #~ print 'subsuperscript', toks

        if len(toks[0]) == 1:
            return toks[0].asList()
        if len(toks[0]) == 3:
            prev, op, next = toks[0]
        elif len(toks[0]) == 2:
            prev = SpaceElement(0)
            op, next = toks[0]
        else:
            raise ParseException("Unable to parse subscript/superscript construct.")

        index, other_index = self._subsuperscript_indices[op]
        if self.is_overunder(prev):
            names = self._subsuperscript_names['overUnder']
        else:
            names = self._subsuperscript_names['normal']

        prev.neighbors[names[index]] = next

        for compound in self._subsuperscript_names.values():
            if compound[other_index] in next.neighbors:
                prev.neighbors[names[other_index]] = next.neighbors[compound[other_index]]
                del next.neighbors[compound[other_index]]
            elif compound[index] in next.neighbors:
                raise ValueError(
                    "Double %ss" %
                    self._subsuperscript_names['normal'][index])
        return [prev]

    def is_overunder(self, prev):
        return isinstance(prev, SymbolElement) and overunder.has_key(prev.sym)

handler = Handler()

# All forward declarations are here
font = Forward().setParseAction(handler.font).setName("font")
latexfont = Forward().setParseAction(handler.latexfont).setName("latexfont")
subsuper = Forward().setParseAction(handler.subsuperscript).setName("subsuper")
placeable = Forward().setName("placeable")
expression = Forward().setParseAction(handler.expression).setName("expression")

lbrace       = Literal('{').suppress()
rbrace       = Literal('}').suppress()
lbrack       = Literal('[')
rbrack       = Literal(']')
lparen       = Literal('(')
rparen       = Literal(')')
grouping     =(lbrack 
             | rbrack 
             | lparen 
             | rparen)

subscript    = Literal('_')
superscript  = Literal('^')

bslash       = Literal('\\')

langle       = Literal('<')
rangle       = Literal('>')
equals       = Literal('=')
relation     =(langle
             | rangle
             | equals)

colon        = Literal(':')
comma        = Literal(',')
period       = Literal('.')
semicolon    = Literal(';')
exclamation  = Literal('!')
punctuation  =(colon
             | comma
             | period
             | semicolon)

at           = Literal('@')
percent      = Literal('%')
ampersand    = Literal('&')
misc         =(exclamation
             | at
             | percent
             | ampersand)

over         = Literal('over')
under        = Literal('under')
overUnder    =(over
             | under)

accent       = oneOf("hat check dot breve acute ddot grave tilde bar vec "
                     "\" ` ' ~ . ^")

function     = oneOf("arccos csc ker min arcsin deg lg Pr arctan det lim sec "
                     "arg dim liminf sin cos exp limsup sinh cosh gcd ln sup "
                     "cot hom log tan coth inf max tanh")

number       = Combine(Word(nums) + Optional(Literal('.')) + Optional( Word(nums) ))

plus         = Literal('+')
minus        = Literal('-')
times        = Literal('*')
div          = Literal('/')
binop        =(plus 
             | minus
             | times
             | div)

fontname     = oneOf("rm cal it tt sf bf")
latex2efont  = oneOf("mathrm mathcal mathit mathtt mathsf mathbf")

texsym       = Combine(bslash + Word(alphanums) + NotAny("{"))

char         = Word(alphanums + ' ', exact=1).leaveWhitespace()

space        =(FollowedBy(bslash)
             +   (Literal(r'\ ')
               |  Literal(r'\/')
               |  Group(Literal(r'\hspace{') + number + Literal('}'))
                 )
              ).setParseAction(handler.space).setName('space')

symbol       = Regex("(" + ")|(".join(
               [
                 r"\\[a-zA-Z0-9]+(?!{)",
                 r"[a-zA-Z0-9 ]",
                 r"[+\-*/]",
                 r"[<>=]",
                 r"[:,.;!]",
                 r"[!@%&]",
                 r"[[\]()]",
                 r"\\\$"
               ])
             + ")"
             ).setParseAction(handler.symbol).leaveWhitespace()

_symbol      =(texsym
             | char
             | binop
             | relation
             | punctuation
             | misc
             | grouping
             ).setParseAction(handler.symbol).leaveWhitespace()

accent       = Group(
                 Combine(bslash + accent)
               + Optional(lbrace)
               + symbol
               + Optional(rbrace)
             ).setParseAction(handler.accent).setName("accent")

function     =(Suppress(bslash)
             + function).setParseAction(handler.function).setName("function")

group        = Group(
                 lbrace
               + OneOrMore(
                   space
                 | font
                 | latexfont
                 | subsuper
                 )
               + rbrace
             ).setParseAction(handler.group).setName("group")

font        <<(Suppress(bslash)
             + fontname)

latexfont   << Group(
                 Suppress(bslash)
               + latex2efont
               + group)

composite    = Group(
                 Combine(
                   bslash
                 + overUnder
                 )
               + group
               + group
             ).setParseAction(handler.composite).setName("composite")

placeable   <<(accent
             ^ function  
             ^ symbol
             ^ group
             ^ composite
             )

subsuper    << Group(
                 (
                   placeable
                 + ZeroOrMore(
                    ( subscript
                    | superscript
                    )
                   + subsuper
                   )
                 )
               | (( subscript | superscript) + placeable)
             )

math         = OneOrMore(
                 space
               | font
               | latexfont
               | subsuper
             ).setParseAction(handler.math).setName("math")

math_delim   =(~bslash
             + Literal('$'))

non_math     = Regex(r"(?:[^$]|(?:\\\$))*"
             ).setParseAction(handler.non_math).setName("non_math").leaveWhitespace()

expression  <<(
                 non_math
               + ZeroOrMore(
                   Suppress(math_delim)
                 + math
                 + Suppress(math_delim)
                 + non_math
                 )
               )
                     

####



class math_parse_s_ft2font_common:
    """
    Parse the math expression s, return the (bbox, fonts) tuple needed
    to render it.

    fontsize must be in points

    return is width, height, fonts
    """
    major, minor1, minor2, tmp, tmp = sys.version_info
    if major==2 and minor1==2:
        raise SystemExit('mathtext broken on python2.2.  We hope to get this fixed soon')

    def __init__(self, output):
        self.output = output
        self.cache = {}

    def __call__(self, s, dpi, prop, angle=0):
        cacheKey = (s, dpi, hash(prop), angle)
        if self.cache.has_key(cacheKey):
            w, h, fontlike, used_characters = self.cache[cacheKey]
            return w, h, fontlike, used_characters

        use_afm = False
        if self.output == 'SVG':
            self.font_object = BakomaSVGFonts()
            #self.font_object = MyUnicodeFonts(output='SVG')
        elif self.output == 'Agg':
            self.font_object = BakomaFonts()
            #self.font_object = MyUnicodeFonts()
        elif self.output == 'PS':
            if rcParams['ps.useafm']:
                self.font_object = StandardPSFonts()
                use_afm = True
            else:
                self.font_object = BakomaPSFonts()
                #self.font_object = MyUnicodeFonts(output='PS')
        elif self.output == 'PDF':
            self.font_object = BakomaPDFFonts()
        Element.fonts = self.font_object
        
        fontsize = prop.get_size_in_points()
            
        handler.clear()
        expression.parseString( s )

        if use_afm:
            fname = fontManager.findfont(prop, fontext='afm')
            default_font = AFM(file(fname, 'r'))
            default_font.fname = fname
        else:
            fname = fontManager.findfont(prop)
            default_font = FT2Font(fname)
        
        handler.expr.determine_font([default_font])
        handler.expr.set_size_info(fontsize, dpi)
        
        # set the origin once to allow w, h compution
        handler.expr.set_origin(0, 0)
        xmin = min([e.xmin() for e in handler.symbols])
        xmax = max([e.xmax() for e in handler.symbols])
        ymin = min([e.ymin() for e in handler.symbols])
        ymax = max([e.ymax() for e in handler.symbols])
        
        # now set the true origin - doesn't affect with and height
        w, h =  xmax-xmin, ymax-ymin
        # a small pad for the canvas size
        w += 2
        h += 2

        handler.expr.set_origin(0, h-ymax)

        if self.output in ('SVG', 'Agg'):
            Element.fonts.set_canvas_size(w,h)
        elif self.output == 'PS':
            pswriter = StringIO()
            Element.fonts.set_canvas_size(w, h, pswriter)
        elif self.output == 'PDF':
            pswriter = list()
            Element.fonts.set_canvas_size(w, h, pswriter)

        handler.expr.render()
        handler.clear()
        
        if self.output == 'SVG':
            # The empty list at the end is for lines
            svg_elements = Bunch(svg_glyphs=self.font_object.svg_glyphs,
                    svg_lines=[])
            self.cache[cacheKey] = \
                w, h, svg_elements, Element.fonts.get_used_characters()
        elif self.output == 'Agg':
            self.cache[cacheKey] = \
                w, h, self.font_object.get_fonts(), Element.fonts.get_used_characters()
        elif self.output in ('PS', 'PDF'):
            self.cache[cacheKey] = \
                w, h, pswriter, Element.fonts.get_used_characters()
        return self.cache[cacheKey]
            
if rcParams["mathtext.mathtext2"]:
    from matplotlib.mathtext2 import math_parse_s_ft2font
    from matplotlib.mathtext2 import math_parse_s_ft2font_svg
else:
    math_parse_s_ft2font = math_parse_s_ft2font_common('Agg')
    math_parse_s_ft2font_svg = math_parse_s_ft2font_common('SVG')
math_parse_s_ps = math_parse_s_ft2font_common('PS')
math_parse_s_pdf = math_parse_s_ft2font_common('PDF')

if 0: #__name__=='___main__':

    stests = [
            r'$dz/dt \/ = \/ \gamma x^2 \/ + \/ \rm{sin}(2\pi y+\phi)$',
            r'$dz/dt \/ = \/ \gamma xy^2 \/ + \/ \rm{s}(2\pi y+\phi)$',
            r'$x^1 2$',
            r'$\alpha_{i+1}^j \/ = \/ \rm{sin}(2\pi f_j t_i) e^{-5 t_i/\tau}$',
            r'$\cal{R}\prod_{i=\alpha_{i+1}}^\infty a_i\rm{sin}(2 \pi f x_i)$',
            r'$\bigodot \bigoplus \cal{R} a_i\rm{sin}(2 \pi f x_i)$',
            r'$x_i$',
            r'$5\/\angstrom\hspace{ 2.0 }\pi$',
            r'$x+1$',
            r'$i$',
            r'$i^j$',
            ]
    #~ w, h, fonts = math_parse_s_ft2font(s, 20, 72)
    for s in stests:
        try:
            print s
            print (expression + StringEnd()).parseString( s[1:-1] )
        except ParseException, pe:
            print "*** ERROR ***", pe.msg
            print s
            print 'X' + (' '*pe.loc)+'^'
            # how far did we get?
            print expression.parseString( s[1:-1] )
        print

    #w, h, fonts = math_parse_s_ps(s, 20, 72)


if __name__=='__main__':
    Element.fonts = DummyFonts()
    for i in range(5,20):
        s = '$10^{%02d}$'%i
        print 'parsing', s
        w, h, fonts = math_parse_s_ft2font(s, dpi=27, fontsize=12, angle=0)
    if 0:
        Element.fonts = DummyFonts()
        handler.clear()
        expression.parseString( s )

        handler.expr.set_size_info(12, 72)

        # set the origin once to allow w, h compution
        handler.expr.set_origin(0, 0)
        for e in handler.symbols:
            assert(hasattr(e, 'metrics'))
