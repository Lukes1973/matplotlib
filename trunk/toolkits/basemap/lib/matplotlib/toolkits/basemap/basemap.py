"""
Module for plotting data on maps with matplotlib.

Contains the Basemap class (which does most of the 
heavy lifting), and the following functions:

NetCDFFile: Read local and remote NetCDF datasets.

interp:  bilinear interpolation between rectilinear grids.

shiftgrid:  shifts global lat/lon grids east or west.

addcyclic: Add cyclic (wraparound) point in longitude.

num2date: convert from a numeric time value to a datetime object.

date2num: convert from a datetime object to a numeric time value.
"""
from matplotlib import rcParams
from matplotlib import __version__ as _matplotlib_version
# check to make sure matplotlib is not too old.
_mpl_required_version = '0.90'
if _matplotlib_version < _mpl_required_version:
    raise ImportError('your matplotlib is too old - basemap '
    'requires version %s or higher'% _matplotlib_version)
from matplotlib.collections import LineCollection
from matplotlib.patches import Ellipse, Circle, Polygon
from matplotlib.lines import Line2D
import pyproj, sys, os, math, dbflib
from proj import Proj
import numpy as npy
from numpy import linspace, squeeze, ma
from matplotlib.cbook import is_scalar, dedent
from shapelib import ShapeFile
import _geos, pupynere, netcdftime

# basemap data files now installed in lib/matplotlib/toolkits/basemap/data
basemap_datadir = os.sep.join([os.path.dirname(__file__), 'data'])

__version__ = '0.9.9'

# supported map projections.
_projnames = {'cyl'      : 'Cylindrical Equidistant',
             'merc'     : 'Mercator',
             'tmerc'    : 'Transverse Mercator',
             'omerc'    : 'Oblique Mercator',
             'mill'     : 'Miller Cylindrical',
             'lcc'      : 'Lambert Conformal',
             'laea'     : 'Lambert Azimuthal Equal Area',
             'nplaea'   : 'North-Polar Lambert Azimuthal',
             'splaea'   : 'South-Polar Lambert Azimuthal',
             'eqdc'     : 'Equidistant Conic',
             'aeqd'     : 'Azimuthal Equidistant',
             'npaeqd'   : 'North-Polar Azimuthal Equidistant',
             'spaeqd'   : 'South-Polar Azimuthal Equidistant',
             'aea'      : 'Albers Equal Area',
             'stere'    : 'Stereographic',
             'npstere'  : 'North-Polar Stereographic',
             'spstere'  : 'South-Polar Stereographic',
             'cass'     : 'Cassini-Soldner',
             'poly'     : 'Polyconic',
             'ortho'    : 'Orthographic',
             'geos'     : 'Geostationary',
             'sinu'     : 'Sinusoidal',
             'moll'     : 'Mollweide',
             'robin'    : 'Robinson',
             'gnom'     : 'Gnomonic',
             }
supported_projections = []
for _items in _projnames.iteritems():
    supported_projections.append("'%s' = %s\n" % (_items))
supported_projections = ''.join(supported_projections)

# projection specific parameters.
projection_params = {'cyl'      : 'corners only (no width/height)',
             'merc'     : 'corners plus lat_ts (no width/height)',
             'tmerc'    : 'lon_0,lat_0',
             'omerc'    : 'lon_0,lat_0,lat_1,lat_2,lon_1,lon_2,no width/height',
             'mill'     : 'corners only (no width/height)',
             'lcc'      : 'lon_0,lat_0,lat_1,lat_2',
             'laea'     : 'lon_0,lat_0',
             'nplaea'   : 'bounding_lat,lon_0,lat_0,no corners or width/height',
             'splaea'   : 'bounding_lat,lon_0,lat_0,no corners or width/height',
             'eqdc'     : 'lon_0,lat_0,lat_1,lat_2',
             'aeqd'     : 'lon_0,lat_0',
             'npaeqd'   : 'bounding_lat,lon_0,lat_0,no corners or width/height',
             'spaeqd'   : 'bounding_lat,lon_0,lat_0,no corners or width/height',
             'aea'      : 'lon_0,lat_0,lat_1',
             'stere'    : 'lon_0,lat_0,lat_ts',
             'npstere'  : 'bounding_lat,lon_0,lat_0,no corners or width/height',
             'spstere'  : 'bounding_lat,lon_0,lat_0,no corners or width/height',
             'cass'     : 'lon_0,lat_0',
             'poly'     : 'lon_0,lat_0',
             'ortho'    : 'lon_0,lat_0',
             'geos'     : 'lon_0,lat_0,satellite_height',
             'sinu'     : 'lon_0,lat_0,no corners or width/height',
             'moll'     : 'lon_0,lat_0,no corners or width/height',
             'robin'    : 'lon_0,lat_0,no corners or width/height',
             'gnom'     : 'lon_0,lat_0',
             }

# The __init__ docstring is pulled out here because it is so long;
# Having it in the usual place makes it hard to get from the
# __init__ argument list to the code that uses the arguments.
_Basemap_init_doc = """
 create a Basemap instance.

 This sets up a basemap with specified map projection.
 and creates the coastline data structures in native map projection
 coordinates.

 arguments:

 projection - map projection. Supported projections are:
%(supported_projections)s
  Default is 'cyl'.

 For most map projections, the map projection region can either be
 specified by setting these keywords:

 llcrnrlon - longitude of lower left hand corner of the desired map domain (degrees).
 llcrnrlat - latitude of lower left hand corner of the desired map domain (degrees).
 urcrnrlon - longitude of upper right hand corner of the desired map domain (degrees).
 urcrnrlat - latitude of upper right hand corner of the desired map domain (degrees).

 or these keywords:

 width  - width of desired map domain in projection coordinates (meters).
 height - height of desired map domain in projection coordinates (meters).
 lon_0  - center of desired map domain (in degrees).
 lat_0  - center of desired map domain (in degrees).

 For 'sinu', 'moll', 'npstere', 'spstere', 'nplaea', 'splaea', 'nplaea',
 'splaea', 'npaeqd', 'spaeqd' or 'robin', the values of
 llcrnrlon,llcrnrlat,urcrnrlon,urcrnrlat,width and height are ignored
 (because either they are computed internally, or entire globe is
 always plotted). For the cylindrical projections
 ('cyl','merc' and 'mill'), the default is to use
 llcrnrlon=-180,llcrnrlat=-90, urcrnrlon=180 and urcrnrlat=90). For all other
 projections except 'ortho' and 'geos', either the lat/lon values of the
 corners or width and height must be specified by the user.
 For 'ortho' and 'geos', the lat/lon values of the corners may be specified,
 but if they are not, the entire globe is plotted.

 resolution - resolution of boundary database to use. Can be 'c' (crude),
  'l' (low), 'i' (intermediate), 'h' (high), 'f' (full) or None.
  If None, no boundary data will be read in (and class methods
  such as drawcoastlines will raise an exception if invoked).
  Resolution drops off by roughly 80%%
  between datasets.  Higher res datasets are much slower to draw.
  Default 'c'. Coastline data is from the GSHHS
  (http://www.soest.hawaii.edu/wessel/gshhs/gshhs.html).
  State, country and river datasets from the Generic Mapping
  Tools (http://gmt.soest.hawaii.edu).

 area_thresh - coastline or lake with an area smaller than area_thresh
  in km^2 will not be plotted.  Default 10000,1000,100,10,1 for resolution
  'c','l','i','h','f'.

 rsphere - radius of the sphere used to define map projection (default
  6370997 meters, close to the arithmetic mean radius of the earth). If
  given as a sequence, the first two elements are interpreted as
  the the radii of the major and minor axes of an ellipsoid. Note: sometimes
  an ellipsoid is specified by the major axis and an 'inverse flattening
  parameter' (if).  The minor axis (b) can be computed from the major axis (a)
  and the inverse flattening parameter using the formula if = a/(a-b).

 suppress_ticks - suppress automatic drawing of axis ticks and labels
 in map projection coordinates.  Default False, so parallels and meridians
 can be labelled instead. If parallel or meridian labelling is requested
 (using drawparallels and drawmeridians methods), automatic tick labelling
 will be supressed even is suppress_ticks=False.  suppress_ticks=False
 is useful if you want to use your own custom tick formatter, or
 if you want to let matplotlib label the axes in meters
 using native map projection coordinates

 anchor - determines how map is placed in axes rectangle (passed to
 axes.set_aspect). Default is 'C', which means map is centered.
 Allowed values are ['C', 'SW', 'S', 'SE', 'E', 'NE', 'N', 'NW', 'W'].

 ax - set default axes instance (default None - pylab.gca() may be used
 to get the current axes instance).  If you don't want pylab to be imported,
 you can either set this to a pre-defined axes instance, or use the 'ax'
 keyword in each Basemap method call that does drawing. In the first case,
 all Basemap method calls will draw to the same axes instance.  In the
 second case, you can draw to different axes with the same Basemap instance.
 You can also use the 'ax' keyword in individual method calls to
 selectively override the default axes instance.

 The following parameters are map projection parameters which all default to
 None.  Not all parameters are used by all projections, some are ignored.
 The module variable 'projection_params' is a dictionary which
 lists which parameters apply to which projections.

 lat_ts - latitude of true scale for mercator projection, optional
  for stereographic projection.
 lat_1 - first standard parallel for lambert conformal, albers
  equal area projection and equidistant conic projections. Latitude of one
  of the two points on the projection centerline for oblique mercator.
  If lat_1 is not given, but lat_0 is, lat_1 is set to lat_0 for
  lambert conformal, albers equal area and equidistant conic.
 lat_2 - second standard parallel for lambert conformal, albers
  equal area projection and equidistant conic projections. Latitude of one
  of the two points on the projection centerline for oblique mercator.
  If lat_2 is not given, it is set to lat_1 for
  lambert conformal, albers equal area and equidistant conic.
 lon_1 - longitude of one of the two points on the projection centerline
  for oblique mercator.
 lon_2 - longitude of one of the two points on the projection centerline
  for oblique mercator.
 lat_0 - central latitude (y-axis origin) - used by all projections,
  Must be equator for mercator projection.
 lon_0 - central meridian (x-axis origin) - used by all projections,
 boundinglat - bounding latitude for pole-centered projections (npstere,spstere,
  nplaea,splaea,npaeqd,spaeqd).  These projections are square regions centered
  on the north or south pole.  The longitude lon_0 is at 6-o'clock, and the
  latitude circle boundinglat is tangent to the edge of the map at lon_0.
 satellite_height - height of satellite (in m) above equator -
  only relevant for geostationary projections ('geos'). Default 35,786 km.

 Here are the most commonly used class methods (see the docstring
 for each for more details):

 To draw a graticule grid (labelled latitude and longitude lines)
 use the drawparallels and drawmeridians methods.

 To draw coastline, rivers and political boundaries, use the
 the drawcontinents, drawrivers, drawcountries and drawstates methods.

 To fill the continents and inland lakes, use the fillcontinents method.

 To draw the boundary of the map projection region, and fill the 
 interior a certain color, use the drawmapboundary method.

 The contour, contourf, pcolor, pcolormesh, plot, scatter
 quiver and imshow methods use the corresponding matplotlib axes
 methods to draw on the map.

 The transform_scalar method can be used to interpolate regular
 lat/lon grids of scalar data to native map projection grids.

 The transform_vector method can be used to interpolate and rotate
 regular lat/lon grids of vector data to native map projection grids.

 The rotate_vector method rotates a vector field from lat/lon
 coordinates into map projections coordinates, without doing any 
 interpolation.

 The readshapefile method can be used to read in data from ESRI
 shapefiles.

 The drawgreatcircle method draws great circles on the map.
""" % locals()

# unsupported projection error message.
_unsupported_projection = ["'%s' is an unsupported projection.\n"]
_unsupported_projection.append("The supported projections are:\n")
_unsupported_projection.append(supported_projections)
_unsupported_projection = ''.join(_unsupported_projection)

def _validated_ll(param, name, minval, maxval):
    param = float(param)
    if param > maxval or param < minval:
        raise ValueError('%s must be between %f and %f degrees' %
                                           (name, minval, maxval))
    return param

def _insert_validated(d, param, name, minval, maxval):
    if param is not None:
        d[name] = _validated_ll(param, name, minval, maxval)

class Basemap(object):
    """
    Class for plotting data on map projections with matplotlib.
    See __init__ docstring for details on how to create a class
    instance for a given map projection.

    Useful instance variables:

    projection - map projection. Print the module variable
    "supported_projections" to see a list.
    aspect - map aspect ratio (size of y dimension / size of x dimension).
    llcrnrlon - longitude of lower left hand corner of the desired map domain.
    llcrnrlon - latitude of lower left hand corner of the desired map domain.
    urcrnrlon - longitude of upper right hand corner of the desired map domain.
    urcrnrlon - latitude of upper right hand corner of the desired map domain.
    llcrnrx,llcrnry,urcrnrx,urcrnry - corners of map domain in projection coordinates.
    rmajor,rminor - equatorial and polar radii of ellipsoid used (in meters).
    resolution - resolution of boundary dataset being used ('c' for crude,
      'l' for low, etc.). If None, no boundary dataset is associated with the
      Basemap instance.
    srs - a string representing the 'spatial reference system' for the map
      projection as defined by PROJ.4.

    Example Usage:

    >>> from matplotlib.toolkits.basemap import Basemap
    >>> from pylab import load, meshgrid, title, arange, show
    >>> # read in topo data (on a regular lat/lon grid)
    >>> etopo = load('etopo20data.gz')
    >>> lons  = load('etopo20lons.gz')
    >>> lats  = load('etopo20lats.gz')
    >>> # create Basemap instance for Robinson projection.
    >>> m = Basemap(projection='robin',lon_0=0.5*(lons[0]+lons[-1]))
    >>> # compute native map projection coordinates for lat/lon grid.
    >>> x, y = m(*meshgrid(lons,lats))
    >>> # make filled contour plot.
    >>> cs = m.contourf(x,y,etopo,30,cmap=cm.jet)
    >>> m.drawcoastlines() # draw coastlines
    >>> m.drawmapboundary() # draw a line around the map region
    >>> m.drawparallels(arange(-90.,120.,30.),labels=[1,0,0,0]) # draw parallels
    >>> m.drawmeridians(arange(0.,420.,60.),labels=[0,0,0,1]) # draw meridians
    >>> title('Robinson Projection') # add a title
    >>> show()

    [this example (simpletest.py) plus many others can be found in the
     examples directory of source distribution.  The "OO" version of this
     example (which does not use pylab) is called "simpletest_oo.py".]
    """

    def __init__(self, llcrnrlon=None, llcrnrlat=None,
                       urcrnrlon=None, urcrnrlat=None,
                       width=None, height=None,
                       projection='cyl', resolution='c',
                       area_thresh=None, rsphere=6370997.0,
                       lat_ts=None,
                       lat_1=None, lat_2=None,
                       lat_0=None, lon_0=None,
                       lon_1=None, lon_2=None,
                       suppress_ticks=True,
                       satellite_height=35786000,
                       boundinglat=None,
                       anchor='C',
                       ax=None):
        # docstring is added after __init__ method definition

        # where to put plot in figure (default is 'C' or center)
        self.anchor = anchor
        # map projection.
        self.projection = projection

        # set up projection parameter dict.
        projparams = {}
        projparams['proj'] = projection
        try:
            if rsphere[0] > rsphere[1]:
                projparams['a'] = rsphere[0]
                projparams['b'] = rsphere[1]
            else:
                projparams['a'] = rsphere[1]
                projparams['b'] = rsphere[0]
        except:
            if projection == 'tmerc':
            # use bR_a instead of R because of obscure bug
            # in proj4 for tmerc projection.
                projparams['bR_a'] = rsphere
            else:
                projparams['R'] = rsphere
        # set units to meters.
        projparams['units']='m'
        # check for sane values of lon_0, lat_0, lat_ts, lat_1, lat_2
        _insert_validated(projparams, lat_0, 'lat_0', -90, 90)
        _insert_validated(projparams, lat_1, 'lat_1', -90, 90)
        _insert_validated(projparams, lat_2, 'lat_2', -90, 90)
        _insert_validated(projparams, lat_ts, 'lat_ts', -90, 90)
        _insert_validated(projparams, lon_0, 'lon_0', -360, 720)
        _insert_validated(projparams, lon_1, 'lon_1', -360, 720)
        _insert_validated(projparams, lon_2, 'lon_2', -360, 720)
        if projection == 'geos':
            projparams['h'] = satellite_height
        # check for sane values of projection corners.
        using_corners = (None not in [llcrnrlon,llcrnrlat,urcrnrlon,urcrnrlat])
        if using_corners:
            self.llcrnrlon = _validated_ll(llcrnrlon, 'llcrnrlon', -360, 720)
            self.urcrnrlon = _validated_ll(urcrnrlon, 'urcrnrlon', -360, 720)
            self.llcrnrlat = _validated_ll(llcrnrlat, 'llcrnrlat', -90, 90)
            self.urcrnrlat = _validated_ll(urcrnrlat, 'urcrnrlat', -90, 90)

        # for each of the supported projections,
        # compute lat/lon of domain corners
        # and set values in projparams dict as needed.

        if projection in ['lcc', 'eqdc', 'aea']:
            # if lat_0 is given, but not lat_1,
            # set lat_1=lat_0
            if lat_1 is None and lat_0 is not None:
                lat_1 = lat_0
                projparams['lat_1'] = lat_1
            if lat_1 is None or lon_0 is None:
                raise ValueError('must specify lat_1 or lat_0 and lon_0 for %s basemap (lat_2 is optional)' % _projnames[projection])
            if lat_2 is None:
                projparams['lat_2'] = lat_1
            if not using_corners:
                if width is None or height is None:
                    raise ValueError, 'must either specify lat/lon values of corners (llcrnrlon,llcrnrlat,ucrnrlon,urcrnrlat) in degrees or width and height in meters'
                if lon_0 is None or lat_0 is None:
                    raise ValueError, 'must specify lon_0 and lat_0 when using width, height to specify projection region'
                llcrnrlon,llcrnrlat,urcrnrlon,urcrnrlat = _choosecorners(width,height,**projparams)
                self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
                self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
        elif projection == 'stere':
            if lat_0 is None or lon_0 is None:
                raise ValueError, 'must specify lat_0 and lon_0 for Stereographic basemap (lat_ts is optional)'
            if not using_corners:
                if width is None or height is None:
                    raise ValueError, 'must either specify lat/lon values of corners (llcrnrlon,llcrnrlat,ucrnrlon,urcrnrlat) in degrees or width and height in meters'
                if lon_0 is None or lat_0 is None:
                    raise ValueError, 'must specify lon_0 and lat_0 when using width, height to specify projection region'
                llcrnrlon,llcrnrlat,urcrnrlon,urcrnrlat = _choosecorners(width,height,**projparams)
                self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
                self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
        elif projection in ['spstere', 'npstere',
                            'splaea', 'nplaea',
                            'spaeqd', 'npaeqd']:
            if boundinglat is None or lon_0 is None:
                raise ValueError('must specify boundinglat and lon_0 for %s basemap' % _projnames[projection])
            if projection[0] == 's':
                sgn = -1
            else:
                sgn = 1
            rootproj = projection[2:]
            projparams['proj'] = rootproj
            if rootproj == 'stere':
                projparams['lat_ts'] = sgn * 90.
            projparams['lat_0'] = sgn * 90.
            self.llcrnrlon = lon_0 - sgn*45.
            self.urcrnrlon = lon_0 + sgn*135.
            proj = pyproj.Proj(projparams)
            x,y = proj(lon_0,boundinglat)
            lon,self.llcrnrlat = proj(math.sqrt(2.)*y,0.,inverse=True)
            self.urcrnrlat = self.llcrnrlat
            if width is not None or height is not None:
                print 'warning: width and height keywords ignored for %s projection' % _projnames[projection]
        elif projection == 'laea':
            if lat_0 is None or lon_0 is None:
                raise ValueError, 'must specify lat_0 and lon_0 for Lambert Azimuthal basemap'
            if not using_corners:
                if width is None or height is None:
                    raise ValueError, 'must either specify lat/lon values of corners (llcrnrlon,llcrnrlat,ucrnrlon,urcrnrlat) in degrees or width and height in meters'
                if lon_0 is None or lat_0 is None:
                    raise ValueError, 'must specify lon_0 and lat_0 when using width, height to specify projection region'
                llcrnrlon,llcrnrlat,urcrnrlon,urcrnrlat = _choosecorners(width,height,**projparams)
                self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
                self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
        elif projection == 'merc':
            if lat_ts is None:
                raise ValueError, 'must specify lat_ts for Mercator basemap'
            # clip plot region to be within -89.99S to 89.99N
            # (mercator is singular at poles)
            if not using_corners:
                llcrnrlon = -180.
                llcrnrlat = -90.
                urcrnrlon = 180
                urcrnrlat = 90.
            if llcrnrlat < -89.99: llcrnrlat = -89.99
            if llcrnrlat > 89.99: llcrnrlat = 89.99
            if urcrnrlat < -89.99: urcrnrlat = -89.99
            if urcrnrlat > 89.99: urcrnrlat = 89.99
            self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
            self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
            if width is not None or height is not None:
                print 'warning: width and height keywords ignored for %s projection' % self.projection
        elif projection in ['tmerc','gnom','cass','poly'] :
            if lat_0 is None or lon_0 is None:
                raise ValueError, 'must specify lat_0 and lon_0 for Transverse Mercator, Gnomonic, Cassini-Soldnerr Polyconic basemap'
            if not using_corners:
                if width is None or height is None:
                    raise ValueError, 'must either specify lat/lon values of corners (llcrnrlon,llcrnrlat,ucrnrlon,urcrnrlat) in degrees or width and height in meters'
                if lon_0 is None or lat_0 is None:
                    raise ValueError, 'must specify lon_0 and lat_0 when using width, height to specify projection region'
                llcrnrlon,llcrnrlat,urcrnrlon,urcrnrlat = _choosecorners(width,height,**projparams)
                self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
                self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
        elif projection == 'ortho':
            if not projparams.has_key('R'):
                raise ValueError, 'orthographic projection only works for perfect spheres - not ellipsoids'
            if lat_0 is None or lon_0 is None:
                raise ValueError, 'must specify lat_0 and lon_0 for Orthographic basemap'
            if width is not None or height is not None:
                print 'warning: width and height keywords ignored for %s projection' % self.projection
            if not using_corners:
                llcrnrlon = -180.
                llcrnrlat = -90.
                urcrnrlon = 180
                urcrnrlat = 90.
                self._fulldisk = True
            else:
                self._fulldisk = False
            self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
            self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
            # FIXME: won't work for points exactly on equator??
            if npy.abs(lat_0) < 1.e-2: lat_0 = 1.e-2
            projparams['lat_0'] = lat_0
        elif projection == 'geos':
            if lon_0 is None:
                raise ValueError, 'must specify lon_0 for Geostationary basemap'
            if width is not None or height is not None:
                print 'warning: width and height keywords ignored for %s projection' % self.projection
            if not using_corners:
                llcrnrlon = -180.
                llcrnrlat = -90.
                urcrnrlon = 180
                urcrnrlat = 90.
                self._fulldisk = True
            else:
                self._fulldisk = False
            self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
            self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
        elif projection in ['moll','robin','sinu']:
            if lon_0 is None:
                raise ValueError, 'must specify lon_0 for Robinson, Mollweide, or Sinusoidal basemap'
            if width is not None or height is not None:
                print 'warning: width and height keywords ignored for %s projection' % self.projection
            llcrnrlon = -180.
            llcrnrlat = -90.
            urcrnrlon = 180
            urcrnrlat = 90.
            self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
            self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
        elif projection == 'omerc':
            if lat_1 is None or lon_1 is None or lat_2 is None or lon_2 is None:
                raise ValueError, 'must specify lat_1,lon_1 and lat_2,lon_2 for Oblique Mercator basemap'
            projparams['lat_1'] = lat_1
            projparams['lon_1'] = lon_1
            projparams['lat_2'] = lat_2
            projparams['lon_2'] = lon_2
            if not using_corners:
                raise ValueError, 'cannot specify map region with width and height keywords for this projection, please specify lat/lon values of corners'
        elif projection == 'aeqd':
            if lat_0 is None or lon_0 is None:
                raise ValueError, 'must specify lat_0 and lon_0 for Azimuthal Equidistant basemap'
            if not using_corners:
                if width is None or height is None:
                    raise ValueError, 'must either specify lat/lon values of corners (llcrnrlon,llcrnrlat,ucrnrlon,urcrnrlat) in degrees or width and height in meters'
                if lon_0 is None or lat_0 is None:
                    raise ValueError, 'must specify lon_0 and lat_0 when using width, height to specify projection region'
                llcrnrlon,llcrnrlat,urcrnrlon,urcrnrlat = _choosecorners(width,height,**projparams)
                self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
                self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
        elif projection == 'mill':
            if not using_corners:
                llcrnrlon = -180.
                llcrnrlat = -90.
                urcrnrlon = 180
                urcrnrlat = 90.
                self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
                self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
            if width is not None or height is not None:
                print 'warning: width and height keywords ignored for %s projection' % self.projection
        elif projection == 'cyl':
            if not using_corners:
                llcrnrlon = -180.
                llcrnrlat = -90.
                urcrnrlon = 180
                urcrnrlat = 90.
                self.llcrnrlon = llcrnrlon; self.llcrnrlat = llcrnrlat
                self.urcrnrlon = urcrnrlon; self.urcrnrlat = urcrnrlat
            if width is not None or height is not None:
                print 'warning: width and height keywords ignored for %s projection' % self.projection
        else:
            raise ValueError(_unsupported_projection % projection)

        # initialize proj4
        proj = Proj(projparams,self.llcrnrlon,self.llcrnrlat,self.urcrnrlon,self.urcrnrlat)

        # make sure axis ticks are suppressed.
        self.noticks = suppress_ticks

        # make Proj instance a Basemap instance variable.
        self.projtran = proj
        # copy some Proj attributes.
        atts = ['rmajor','rminor','esq','flattening','ellipsoid','projparams']
        for att in atts:
            self.__dict__[att] = proj.__dict__[att]
        # these only exist for geostationary projection.
        if hasattr(proj,'_width'):
            self.__dict__['_width'] = proj.__dict__['_width']
        if hasattr(proj,'_height'):
            self.__dict__['_height'] = proj.__dict__['_height']
        # spatial reference string (useful for georeferencing output
        # images with gdal_translate).
        if hasattr(self,'_proj4'):
            self.srs = proj._proj4.srs
        else:
            pjargs = []
            for key,value in self.projparams.iteritems():
                # 'cyl' projection translates to 'eqc' in PROJ.4
                if projection == 'cyl' and key == 'proj':
                    value = 'eqc'
                # ignore x_0 and y_0 settings for 'cyl' projection
                # (they are not consistent with what PROJ.4 uses)
                elif projection == 'cyl' and key in ['x_0','y_0']:
                    continue
                pjargs.append('+'+key+"="+str(value)+' ')
            self.srs = ''.join(pjargs)
        # set instance variables defining map region.
        self.xmin = proj.xmin
        self.xmax = proj.xmax
        self.ymin = proj.ymin
        self.ymax = proj.ymax
        if projection == 'cyl':
            self.aspect = (self.urcrnrlat-self.llcrnrlat)/(self.urcrnrlon-self.llcrnrlon)
        else:
            self.aspect = (proj.ymax-proj.ymin)/(proj.xmax-proj.xmin)
        self.llcrnrx = proj.llcrnrx
        self.llcrnry = proj.llcrnry
        self.urcrnrx = proj.urcrnrx
        self.urcrnry = proj.urcrnry

        # set min/max lats for projection domain.
        if projection in ['mill','cyl','merc']:
            self.latmin = self.llcrnrlat
            self.latmax = self.urcrnrlat
        elif projection in ['ortho','geos','moll','robin','sinu']:
            self.latmin = -90.
            self.latmax = 90.
        else:
            lons, lats = self.makegrid(101,101)
            self.latmin = lats.min()
            self.latmax = lats.max()

        # if ax == None, pylab.gca may be used.
        self.ax = ax
        self.lsmask = None

        # set defaults for area_thresh.
        self.resolution = resolution
        if area_thresh is None and resolution is not None:
            if resolution == 'c':
                area_thresh = 10000.
            elif resolution == 'l':
                area_thresh = 1000.
            elif resolution == 'i':
                area_thresh = 100.
            elif resolution == 'h':
                area_thresh = 10.
            elif resolution == 'f':
                area_thresh = 1.
            else:
                raise ValueError, "boundary resolution must be one of 'c','l','i','h' or 'f'"
        self.area_thresh = area_thresh
        # define map boundary polygon (in lat/lon coordinates)
        self._boundarypolyll, self._boundarypolyxy = self._getmapboundary()
        # read in coastline polygons, only keeping those that
        # intersect map boundary polygon.
        if self.resolution is not None:
            self.coastsegs, self.coastpolygontypes = self._readboundarydata('gshhs')
            # reformat for use in matplotlib.patches.Polygon.
            self.coastpolygons = []
            # also, split coastline segments that jump across entire plot.
            coastsegs = []
            for seg in self.coastsegs:
                x, y = zip(*seg)
                self.coastpolygons.append((x,y))
                x = npy.array(x,npy.float64); y = npy.array(y,npy.float64)
                xd = (x[1:]-x[0:-1])**2
                yd = (y[1:]-y[0:-1])**2
                dist = npy.sqrt(xd+yd)
                split = dist > 5000000.
                if npy.sum(split) and self.projection not in ['merc','cyl','mill']:
                    ind = (npy.compress(split,squeeze(split*npy.indices(xd.shape)))+1).tolist()
                    iprev = 0
                    ind.append(len(xd))
                    for i in ind:
                        # don't add empty lists.
                        if len(range(iprev,i)): 
                            coastsegs.append(zip(x[iprev:i],y[iprev:i]))
                        iprev = i
                else:
                    coastsegs.append(seg)
            self.coastsegs = coastsegs
    # set __init__'s docstring
    __init__.__doc__ = _Basemap_init_doc

    def __call__(self,x,y,inverse=False):
        """
        Calling a Basemap class instance with the arguments lon, lat will
        convert lon/lat (in degrees) to x/y native map projection
        coordinates (in meters).  If optional keyword 'inverse' is
        True (default is False), the inverse transformation from x/y
        to lon/lat is performed.

        For cylindrical equidistant projection ('cyl'), this
        does nothing (i.e. x,y == lon,lat).

        For non-cylindrical projections, the inverse transformation
        always returns longitudes between -180 and 180 degrees. For
        cylindrical projections (self.projection == 'cyl','mill' or 'merc')
        the inverse transformation will return longitudes between
        self.llcrnrlon and self.llcrnrlat.

        input arguments lon, lat can be either scalar floats or N arrays.
        """
        return self.projtran(x,y,inverse=inverse)

    def makegrid(self,nx,ny,returnxy=False):
        """
        return arrays of shape (ny,nx) containing lon,lat coordinates of
        an equally spaced native projection grid.
        if returnxy = True, the x,y values of the grid are returned also.
        """
        return self.projtran.makegrid(nx,ny,returnxy=returnxy)

    def _readboundarydata(self,name):
        """
        read boundary data, clip to map projection region.
        """
        msg = dedent("""
        Unable to open boundary dataset file. Only the 'crude', 'low',
        'intermediate' and 'high' resolution datasets are installed by default.
        If you are requesting a 'full' resolution dataset, you may need to
        download and install those files separately
        (see the basemap README for details).""")
        try:
            bdatfile = open(os.path.join(basemap_datadir,name+'_'+self.resolution+'.dat'),'rb')
            bdatmetafile = open(os.path.join(basemap_datadir,name+'meta_'+self.resolution+'.dat'),'r')
        except:
            raise IOError, msg
        polygons = []
        polygon_types = []
        # coastlines are polygons, other boundaries are line segments.
        if name == 'gshhs':
            Shape = _geos.Polygon
        else:
            Shape = _geos.LineString
        # see if map projection region polygon contains a pole.
        NPole = _geos.Point(self(0.,90.))
        SPole = _geos.Point(self(0.,-90.))
        boundarypolyxy = self._boundarypolyxy
        boundarypolyll = self._boundarypolyll
        hasNP = NPole.within(boundarypolyxy)
        hasSP = SPole.within(boundarypolyxy)
        containsPole = hasNP or hasSP
        # these projections cannot cross pole.
        if containsPole and\
           self.projection in ['tmerc','cass','omerc','merc','mill','cyl','robin','moll','sinu','geos']:
            raise ValueError('%s projection cannot cross pole'%(self.projection))
        # make sure orthographic projection has containsPole=True
        # we will compute the intersections in stereographic
        # coordinates, then transform to orthographic.
        if self.projection == 'ortho' and name == 'gshhs':
            containsPole = True
            lon_0=self.projparams['lon_0']
            lat_0=self.projparams['lat_0']
            re = self.projparams['R']
            # center of stereographic projection restricted to be 
            # nearest one of 6 points on the sphere (every 90 deg lat/lon).
            lon0 = 90.*(npy.around(lon_0/90.))
            lat0 = 90.*(npy.around(lat_0/90.))
            if npy.abs(int(lat0)) == 90: lon0=0.
            maptran = pyproj.Proj(proj='stere',lon_0=lon0,lat_0=lat0,R=re)
            # boundary polygon for orthographic projection
            # in stereographic coorindates.
            b = self._boundarypolyll.boundary
            blons = b[:,0]; blats = b[:,1]
            b[:,0], b[:,1] = maptran(blons, blats)
            boundarypolyxy = _geos.Polygon(b)
        for line in bdatmetafile:
            linesplit = line.split()
            area = float(linesplit[1])
            south = float(linesplit[3])
            north = float(linesplit[4])
            if area < 0.: area = 1.e30
            useit = self.latmax>=south and self.latmin<=north and area>self.area_thresh
            if useit:
                type = int(linesplit[0])
                npts = int(linesplit[2])
                offsetbytes = int(linesplit[5])
                bytecount = int(linesplit[6])
                bdatfile.seek(offsetbytes,0)
                # read in binary string convert into an npts by 2
                # numpy array (first column is lons, second is lats).
                polystring = bdatfile.read(bytecount)
                # binary data is little endian.
                b = npy.array(npy.fromstring(polystring,dtype='<f4'),'f8')
                b.shape = (npts,2)
                b2 = b.copy()
                # if map boundary polygon is a valid one in lat/lon
                # coordinates (i.e. it does not contain either pole),
                # the intersections of the boundary geometries
                # and the map projection region can be computed before
                # transforming the boundary geometry to map projection
                # coordinates (this saves time, especially for small map
                # regions and high-resolution boundary geometries).
                if not containsPole:
                    # close Antarctica.
                    if name == 'gshhs' and south < -68 and area > 10000:
                        lons = b[:,0]
                        lats = b[:,1]
                        lons2 = lons[:-2][::-1]
                        lats2 = lats[:-2][::-1]
                        lons1 = lons2 - 360.
                        lons3 = lons2 + 360.
                        lons = lons1.tolist()+lons2.tolist()+lons3.tolist()
                        lats = lats2.tolist()+lats2.tolist()+lats2.tolist()
                        lonstart,latstart = lons[0], lats[0]
                        lonend,latend = lons[-1], lats[-1]
                        lons.insert(0,lonstart)
                        lats.insert(0,-90.)
                        lons.append(lonend)
                        lats.append(-90.)
                        b = npy.empty((len(lons),2),npy.float64)
                        b[:,0] = lons; b[:,1] = lats
                        poly = _geos.Polygon(b)
                        antart = True
                    else:
                        poly = Shape(b)
                        antart = False
                    # create duplicate polygons shifted by -360 and +360
                    # (so as to properly treat polygons that cross
                    # Greenwich meridian).
                    if not antart:
                        b2[:,0] = b[:,0]-360
                        poly1 = Shape(b2)
                        b2[:,0] = b[:,0]+360
                        poly2 = Shape(b2)
                        polys = [poly1,poly,poly2]
                    else: # Antartica already extends from -360 to +720.
                        polys = [poly]
                    for poly in polys:
                        # if polygon instersects map projection
                        # region, process it.
                        if poly.intersects(boundarypolyll):
                            # if geometry intersection calculation fails,
                            # just move on.
                            try:
                                geoms = poly.intersection(boundarypolyll)
                            except:
                                pass
                            # iterate over geometries in intersection.
                            for psub in geoms:
                                # only coastlines are polygons,
                                # which have a 'boundary' attribute.
                                # otherwise, use 'coords' attribute
                                # to extract coordinates.
                                b = psub.boundary
                                blons = b[:,0]; blats = b[:,1]
                                # transformation from lat/lon to
                                # map projection coordinates.
                                bx, by = self(blons, blats)
                                polygons.append(zip(bx,by))
                                polygon_types.append(type)
                # if map boundary polygon is not valid in lat/lon
                # coordinates, compute intersection between map
                # projection region and boundary geometries in map
                # projection coordinates.
                else:
                    # transform coordinates from lat/lon
                    # to map projection coordinates.
                    # special case for ortho, compute coastline polygon
                    # vertices in stereographic coords.
                    if name == 'gshhs' and self.projection == 'ortho':
                        b[:,0], b[:,1] = maptran(b[:,0], b[:,1])
                    else:
                        b[:,0], b[:,1] = self(b[:,0], b[:,1])
                    goodmask = npy.logical_and(b[:,0]<1.e20,b[:,1]<1.e20)
                    # if less than two points are valid in
                    # map proj coords, skip this geometry.
                    if npy.sum(goodmask) <= 1: continue
                    if name != 'gshhs':
                        # if not a polygon,
                        # just remove parts of geometry that are undefined
                        # in this map projection.
                        bx = npy.compress(goodmask, b[:,0])
                        by = npy.compress(goodmask, b[:,1])
                        # for orthographic projection, all points
                        # outside map projection region are eliminated
                        # with the above step, so we're done.
                        if self.projection == 'ortho':
                            polygons.append(zip(bx,by))
                            polygon_types.append(type)
                            continue
                    # create a GEOS geometry object.
                    poly = Shape(b)
                    # if geometry instersects map projection
                    # region, and doesn't have any invalid points, process it.
                    if goodmask.all() and poly.intersects(boundarypolyxy):
                        # if geometry intersection calculation fails,
                        # just move on.
                        try:
                            geoms = poly.intersection(boundarypolyxy)
                        except:
                            pass
                        # iterate over geometries in intersection.
                        for psub in geoms:
                            b = psub.boundary
                            # if projection == 'ortho',
                            # transform polygon from stereographic
                            # to orthographic coordinates.
                            if self.projection == 'ortho':
                                # if coastline polygon covers more than 99%
                                # of map region for fulldisk projection,
                                # it's probably bogus, so skip it.
                                areafrac = psub.area()/boundarypolyxy.area()
                                if name == 'gshhs' and\
                                   self._fulldisk and\
                                   areafrac > 0.99: continue
                                # inverse transform from stereographic
                                # to lat/lon.
                                b[:,0], b[:,1] = maptran(b[:,0], b[:,1], inverse=True)
                                # orthographic.
                                b[:,0], b[:,1]= self(b[:,0], b[:,1])
                            polygons.append(zip(b[:,0],b[:,1]))
                            polygon_types.append(type)
        return polygons, polygon_types

    def _getmapboundary(self):
        """
        create map boundary polygon (in lat/lon and x/y coordinates)
        """
        nx = 100
        ny = 100
        maptran = self
        if self.projection in ['ortho','geos']:
            # circular region.
            thetas = linspace(0.,2.*npy.pi,2*nx*ny)[:-1]
            if self.projection == 'ortho':
                rminor = self.rmajor
                rmajor = self.rmajor
            else:
                rminor = self._height
                rmajor = self._width
            x = rmajor*npy.cos(thetas) + rmajor
            y = rminor*npy.sin(thetas) + rminor
            b = npy.empty((len(x),2),npy.float64)
            b[:,0]=x; b[:,1]=y
            boundaryxy = _geos.Polygon(b)
            # compute proj instance for full disk, if necessary.
            if not self._fulldisk:
                projparms = self.projparams
                del projparms['x_0']
                del projparms['y_0']
                if self.projection == 'ortho':
                    llcrnrx = -self.rmajor
                    llcrnry = -self.rmajor
                    urcrnrx = -llcrnrx
                    urcrnry = -llcrnry
                else:
                    llcrnrx = -self._width
                    llcrnry = -self._height
                    urcrnrx = -llcrnrx
                    urcrnry = -llcrnry
                projparms['x_0']=-llcrnrx
                projparms['y_0']=-llcrnry
                maptran = pyproj.Proj(projparms)
        elif self.projection in ['moll','robin','sinu']:
            # quasi-elliptical region.
            lon_0 = self.projparams['lon_0']
            # left side
            lats1 = linspace(-89.9,89.9,ny).tolist()
            lons1 = len(lats1)*[lon_0-179.9]
            # top.
            lons2 = linspace(lon_0-179.9,lon_0+179.9,nx).tolist()
            lats2 = len(lons2)*[89.9]
            # right side
            lats3 = linspace(89.9,-89.9,ny).tolist()
            lons3 = len(lats3)*[lon_0+179.9]
            # bottom.
            lons4 = linspace(lon_0+179.9,lon_0-179.9,nx).tolist()
            lats4 = len(lons4)*[-89.9]
            lons = npy.array(lons1+lons2+lons3+lons4,npy.float64)
            lats = npy.array(lats1+lats2+lats3+lats4,npy.float64)
            x, y = maptran(lons,lats)
            b = npy.empty((len(x),2),npy.float64)
            b[:,0]=x; b[:,1]=y
            boundaryxy = _geos.Polygon(b)
        else: # all other projections are rectangular.
            # left side (x = xmin, ymin <= y <= ymax)
            yy = linspace(self.ymin, self.ymax, ny)[:-1]
            x = len(yy)*[self.xmin]; y = yy.tolist()
            # top (y = ymax, xmin <= x <= xmax)
            xx = npy.linspace(self.xmin, self.xmax, nx)[:-1]
            x = x + xx.tolist()
            y = y + len(xx)*[self.ymax]
            # right side (x = xmax, ymin <= y <= ymax)
            yy = linspace(self.ymax, self.ymin, ny)[:-1]
            x = x + len(yy)*[self.xmax]; y = y + yy.tolist()
            # bottom (y = ymin, xmin <= x <= xmax)
            xx = linspace(self.xmax, self.xmin, nx)[:-1]
            x = x + xx.tolist()
            y = y + len(xx)*[self.ymin]
            x = npy.array(x,npy.float64)
            y = npy.array(y,npy.float64)
            b = npy.empty((4,2),npy.float64)
            b[:,0]=[self.xmin,self.xmin,self.xmax,self.xmax]
            b[:,1]=[self.ymin,self.ymax,self.ymax,self.ymin]
            boundaryxy = _geos.Polygon(b)
        if self.projection in ['mill','merc','cyl']:
            # make sure map boundary doesn't quite include pole.
            if self.urcrnrlat > 89.9999:
                urcrnrlat = 89.9999
            else:
                urcrnrlat = self.urcrnrlat
            if self.llcrnrlat < -89.9999:
                llcrnrlat = -89.9999
            else:
                llcrnrlat = self.llcrnrlat
            lons = [self.llcrnrlon, self.llcrnrlon, self.urcrnrlon, self.urcrnrlon]
            lats = [llcrnrlat, urcrnrlat, urcrnrlat, llcrnrlat]
            x, y = self(lons, lats)
            b = npy.empty((len(x),2),npy.float64)
            b[:,0]=x; b[:,1]=y
            boundaryxy = _geos.Polygon(b)
        else:
            if self.projection not in ['moll','robin','sinu']:
                lons, lats = maptran(x,y,inverse=True)
                # fix lons so there are no jumps.
                n = 1
                lonprev = lons[0]
                for lon,lat in zip(lons[1:],lats[1:]):
                    if npy.abs(lon-lonprev) > 90.:
                        if lonprev < 0:
                            lon = lon - 360.
                        else:
                            lon = lon + 360
                        lons[n] = lon
                    lonprev = lon
                    n = n + 1
        b = npy.empty((len(lons),2),npy.float64)
        b[:,0]=lons; b[:,1]=lats
        boundaryll = _geos.Polygon(b)
        return boundaryll, boundaryxy


    def drawmapboundary(self,color='k',linewidth=1.0,fill_color=None,\
                        zorder=None,ax=None):
        """
        draw boundary around map projection region, optionally
        filling interior of region.

        linewidth - line width for boundary (default 1.)
        color - color of boundary line (default black)
        fill_color - fill the map region background with this
         color (default is no fill or fill with axis background color).
        zorder - sets the zorder for filling map background
         (default 0).
        ax - axes instance to use (default None, use default axes 
         instance).
        """
        # get current axes instance (if none specified).
        if ax is None and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif ax is None and self.ax is not None:
            ax = self.ax
        if self.projection == 'ortho' and self._fulldisk: # circular region.
            # define a circle patch, add it to axes instance.
            circle = Circle((self.rmajor,self.rmajor),self.rmajor)
            ax.add_patch(circle)
            if fill_color is None:
                circle.set_fill(False)
            else:
                circle.set_facecolor(fill_color)
                circle.set_zorder(0)
            circle.set_edgecolor(color)
            circle.set_linewidth(linewidth)
            circle.set_clip_on(False)
            if zorder is not None:
                circle.set_zorder(zorder)
        elif self.projection == 'geos' and self._fulldisk: # elliptical region
            # define an Ellipse patch, add it to axes instance.
            ellps = Ellipse((self._width,self._height),2.*self._width,2.*self._height)
            ax.add_patch(ellps)
            if fill_color is None:
                ellps.set_fill(False)
            else:
                ellps.set_facecolor(fill_color)
                ellps.set_zorder(0)
            ellps.set_edgecolor(color)
            ellps.set_linewidth(linewidth)
            ellps.set_clip_on(False)
            if zorder is not None:
                ellps.set_zorder(0)
        elif self.projection in ['moll','robin','sinu']:  # elliptical region.
            nx = 100; ny = 100
            # quasi-elliptical region.
            lon_0 = self.projparams['lon_0']
            # left side
            lats1 = linspace(-89.9,89.9,ny).tolist()
            lons1 = len(lats1)*[lon_0-179.9]
            # top.
            lons2 = linspace(lon_0-179.9,lon_0+179.9,nx).tolist()
            lats2 = len(lons2)*[89.9]
            # right side
            lats3 = linspace(89.9,-89.9,ny).tolist()
            lons3 = len(lats3)*[lon_0+179.9]
            # bottom.
            lons4 = linspace(lon_0+179.9,lon_0-179.9,nx).tolist()
            lats4 = len(lons4)*[-89.9]
            lons = npy.array(lons1+lons2+lons3+lons4,npy.float64)
            lats = npy.array(lats1+lats2+lats3+lats4,npy.float64)
            x, y = self(lons,lats)
            xy = zip(x,y)
            poly = Polygon(xy,edgecolor=color,linewidth=linewidth)
            ax.add_patch(poly)
            if fill_color is None:
                poly.set_fill(False)
            else:
                poly.set_facecolor(fill_color)
                poly.set_zorder(0)
            poly.set_clip_on(False)
            if zorder is not None:
                poly.set_zorder(zorder)
        else: # all other projections are rectangular.
            ax.axesPatch.set_linewidth(linewidth)
            if fill_color is None:
                ax.axesPatch.set_facecolor(ax.get_axis_bgcolor())
            else:
                ax.axesPatch.set_facecolor(fill_color)
                ax.axesPatch.set_zorder(0)
            ax.axesPatch.set_edgecolor(color)
            ax.set_frame_on(True)
            if zorder is not None:
                ax.axesPatch.set_zorder(zorder)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)

    def fillcontinents(self,color='0.8',lake_color=None,ax=None,zorder=None):
        """
        Fill continents.

        color - color to fill continents (default gray).
        lake_color - color to fill inland lakes (default axes background).
        ax - axes instance (overrides default axes instance).
        zorder - sets the zorder for the continent polygons (if not specified,
        uses default zorder for a Polygon patch). Set to zero if you want to paint
        over the filled continents).

        After filling continents, lakes are re-filled with axis background color.
        """
        if self.resolution is None:
            raise AttributeError, 'there are no boundary datasets associated with this Basemap instance'
        # get current axes instance (if none specified).
        if ax is None and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif ax is None and self.ax is not None:
            ax = self.ax
        # get axis background color.
        axisbgc = ax.get_axis_bgcolor()
        np = 0
        for x,y in self.coastpolygons:
            xa = npy.array(x,npy.float32)
            ya = npy.array(y,npy.float32)
        # check to see if all four corners of domain in polygon (if so,
        # don't draw since it will just fill in the whole map).
            delx = 10; dely = 10
            if self.projection in ['cyl']:
                delx = 0.1
                dely = 0.1
            test1 = npy.fabs(xa-self.urcrnrx) < delx
            test2 = npy.fabs(xa-self.llcrnrx) < delx
            test3 = npy.fabs(ya-self.urcrnry) < dely
            test4 = npy.fabs(ya-self.llcrnry) < dely
            hasp1 = npy.sum(test1*test3)
            hasp2 = npy.sum(test2*test3)
            hasp4 = npy.sum(test2*test4)
            hasp3 = npy.sum(test1*test4)
            if not hasp1 or not hasp2 or not hasp3 or not hasp4:
                xy = zip(xa.tolist(),ya.tolist())
                if self.coastpolygontypes[np] not in [2,4]:
                    poly = Polygon(xy,facecolor=color,edgecolor=color,linewidth=0)
                else: # lakes filled with background color by default
                    if lake_color is None:
                        poly = Polygon(xy,facecolor=axisbgc,edgecolor=axisbgc,linewidth=0)
                    else:
                        poly = Polygon(xy,facecolor=lake_color,edgecolor=lake_color,linewidth=0)
                if zorder is not None:
                    poly.set_zorder(zorder)
                ax.add_patch(poly)
            np = np + 1
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)

    def drawcoastlines(self,linewidth=1.,color='k',antialiased=1,ax=None,zorder=None):
        """
        Draw coastlines.

        linewidth - coastline width (default 1.)
        color - coastline color (default black)
        antialiased - antialiasing switch for coastlines (default True).
        ax - axes instance (overrides default axes instance)
        zorder - sets the zorder for the coastlines (if not specified,
        uses default zorder for LineCollections).
        """
        if self.resolution is None:
            raise AttributeError, 'there are no boundary datasets associated with this Basemap instance'
        # get current axes instance (if none specified).
        if ax is None and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif ax is None and self.ax is not None:
            ax = self.ax
        coastlines = LineCollection(self.coastsegs,antialiaseds=(antialiased,))
        coastlines.set_color(color)
        coastlines.set_linewidth(linewidth)
        if zorder is not None:
            coastlines.set_zorder(zorder)
        ax.add_collection(coastlines)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)

    def drawcountries(self,linewidth=0.5,color='k',antialiased=1,ax=None,zorder=None):
        """
        Draw country boundaries.

        linewidth - country boundary line width (default 0.5)
        color - country boundary line color (default black)
        antialiased - antialiasing switch for country boundaries (default True).
        ax - axes instance (overrides default axes instance)
        zorder - sets the zorder for the country boundaries (if not specified,
        uses default zorder for LineCollections).
        """
        if self.resolution is None:
            raise AttributeError, 'there are no boundary datasets associated with this Basemap instance'
        # read in country line segments, only keeping those that
        # intersect map boundary polygon.
        if not hasattr(self,'cntrysegs'):
            self.cntrysegs, types = self._readboundarydata('countries')
        # get current axes instance (if none specified).
        if ax is None and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif ax is None and self.ax is not None:
            ax = self.ax
        coastlines = LineCollection(self.cntrysegs,antialiaseds=(antialiased,))
        coastlines.set_color(color)
        coastlines.set_linewidth(linewidth)
        if zorder is not None:
            coastlines.set_zorder(zorder)
        ax.add_collection(coastlines)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)

    def drawstates(self,linewidth=0.5,color='k',antialiased=1,ax=None,zorder=None):
        """
        Draw state boundaries in Americas.

        linewidth - state boundary line width (default 0.5)
        color - state boundary line color (default black)
        antialiased - antialiasing switch for state boundaries (default True).
        ax - axes instance (overrides default axes instance)
        zorder - sets the zorder for the state boundaries (if not specified,
        uses default zorder for LineCollections).
        """
        if self.resolution is None:
            raise AttributeError, 'there are no boundary datasets associated with this Basemap instance'
        # read in state line segments, only keeping those that
        # intersect map boundary polygon.
        if not hasattr(self,'statesegs'):
            self.statesegs, types = self._readboundarydata('states')
        # get current axes instance (if none specified).
        if ax is None and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif ax is None and self.ax is not None:
            ax = self.ax
        coastlines = LineCollection(self.statesegs,antialiaseds=(antialiased,))
        coastlines.set_color(color)
        coastlines.set_linewidth(linewidth)
        if zorder is not None:
            coastlines.set_zorder(zorder)
        ax.add_collection(coastlines)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)

    def drawrivers(self,linewidth=0.5,color='k',antialiased=1,ax=None,zorder=None):
        """
        Draw major rivers.

        linewidth - river boundary line width (default 0.5)
        color - river boundary line color (default black)
        antialiased - antialiasing switch for river boundaries (default True).
        ax - axes instance (overrides default axes instance)
        zorder - sets the zorder for the rivers (if not specified,
        uses default zorder for LineCollections).
        """
        if self.resolution is None:
            raise AttributeError, 'there are no boundary datasets associated with this Basemap instance'
        # read in river line segments, only keeping those that
        # intersect map boundary polygon.
        if not hasattr(self,'riversegs'):
            self.riversegs, types = self._readboundarydata('rivers')
        # get current axes instance (if none specified).
        if ax is None and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif ax is None and self.ax is not None:
            ax = self.ax
        coastlines = LineCollection(self.riversegs,antialiaseds=(antialiased,))
        coastlines.set_color(color)
        coastlines.set_linewidth(linewidth)
        if zorder is not None:
            coastlines.set_zorder(zorder)
        ax.add_collection(coastlines)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)

    def readshapefile(self,shapefile,name,drawbounds=True,zorder=None,
                      linewidth=0.5,color='k',antialiased=1,ax=None):
        """
        read in shape file, draw boundaries on map.

        Restrictions:
         - Assumes shapes are 2D
         - vertices must be in geographic (lat/lon) coordinates.

        shapefile - path to shapefile components.  Example:
         shapefile='/home/jeff/esri/world_borders' assumes that
         world_borders.shp, world_borders.shx and world_borders.dbf
         live in /home/jeff/esri.
        name - name for Basemap attribute to hold the shapefile
         vertices in native map projection coordinates.
         Class attribute name+'_info' is a list of dictionaries, one
         for each shape, containing attributes of each shape from dbf file.
         For example, if name='counties', self.counties
         will be a list of vertices for each shape in map projection
         coordinates and self.counties_info will be a list of dictionaries
         with shape attributes. Rings in individual shapes are split out
         into separate polygons.  Additional keys
         'RINGNUM' and 'SHAPENUM' are added to shape attribute dictionary.
        drawbounds - draw boundaries of shapes (default True)
        zorder = shape boundary zorder (if not specified, default for LineCollection
        is used).
        linewidth - shape boundary line width (default 0.5)
        color - shape boundary line color (default black)
        antialiased - antialiasing switch for shape boundaries (default True).
        ax - axes instance (overrides default axes instance)

        returns a tuple (num_shapes, type, min, max) containing shape file info.
        num_shapes is the number of shapes, type is the type code (one of
        the SHPT* constants defined in the shapelib module, see
        http://shapelib.maptools.org/shp_api.html) and min and
        max are 4-element lists with the minimum and maximum values of the
        vertices.
        """
        # open shapefile, read vertices for each object, convert
        # to map projection coordinates (only works for 2D shape types).
        try:
            shp = ShapeFile(shapefile)
        except:
            raise IOError, 'error reading shapefile %s.shp' % shapefile
        try:
            dbf = dbflib.open(shapefile)
        except:
            raise IOError, 'error reading dbffile %s.dbf' % shapefile
        info = shp.info()
        if info[1] not in [1,3,5,8]:
            raise ValueError, 'readshapefile can only handle 2D shape types'
        shpsegs = []
        shpinfo = []
        for npoly in range(shp.info()[0]):
            shp_object = shp.read_object(npoly)
            verts = shp_object.vertices()
            rings = len(verts)
            for ring in range(rings):
                lons, lats = zip(*verts[ring])
                if max(lons) > 721. or min(lons) < -721. or max(lats) > 91. or min(lats) < -91:
                    msg=dedent("""
                        shapefile must have lat/lon vertices  - it looks like this one has vertices
                        in map projection coordinates. You can convert the shapefile to geographic
                        coordinates using the shpproj utility from the shapelib tools
                        (http://shapelib.maptools.org/shapelib-tools.html)""")
                    raise ValueError,msg
                x, y = self(lons, lats)
                shpsegs.append(zip(x,y))
                if ring == 0:
                    shapedict = dbf.read_record(npoly)
                # add information about ring number to dictionary.
                shapedict['RINGNUM'] = ring+1
                shapedict['SHAPENUM'] = npoly+1
                shpinfo.append(shapedict)
        # draw shape boundaries using LineCollection.
        if drawbounds:
            # get current axes instance (if none specified).
            if ax is None and self.ax is None:
                try:
                    ax = pylab.gca()
                except:
                    import pylab
                    ax = pylab.gca()
            elif ax is None and self.ax is not None:
                ax = self.ax
            # make LineCollections for each polygon.
            lines = LineCollection(shpsegs,antialiaseds=(1,))
            lines.set_color(color)
            lines.set_linewidth(linewidth)
            if zorder is not None:
                lines.set_zorder(zorder)
            ax.add_collection(lines)
            # set axes limits to fit map region.
            self.set_axes_limits(ax=ax)
        # save segments/polygons and shape attribute dicts as class attributes.
        self.__dict__[name]=shpsegs
        self.__dict__[name+'_info']=shpinfo
        shp.close()
        dbf.close()
        return info

    def drawparallels(self,circles,color='k',linewidth=1.,zorder=None, \
                      dashes=[1,1],labels=[0,0,0,0],labelstyle=None, \
                      fmt='%g',xoffset=None,yoffset=None,ax=None,**kwargs):
        """
        draw parallels (latitude lines).

        circles - list containing latitude values to draw (in degrees).
        color - color to draw parallels (default black).
        linewidth - line width for parallels (default 1.)
        zorder - sets the zorder for parallels (if not specified,
        uses default zorder for Line2D class).
        dashes - dash pattern for parallels (default [1,1], i.e. 1 pixel on,
         1 pixel off).
        labels - list of 4 values (default [0,0,0,0]) that control whether
         parallels are labelled where they intersect the left, right, top or
         bottom of the plot. For example labels=[1,0,0,1] will cause parallels
         to be labelled where they intersect the left and bottom of the plot,
         but not the right and top.
        labelstyle - if set to "+/-", north and south latitudes are labelled
         with "+" and "-", otherwise they are labelled with "N" and "S".
        fmt can be is a format string to format the parallel labels
         (default '%g') or a function that takes a latitude value 
         in degrees as it's only argument and returns a formatted string.
        xoffset - label offset from edge of map in x-direction
         (default is 0.01 times width of map in map projection coordinates).
        yoffset - label offset from edge of map in y-direction
         (default is 0.01 times height of map in map projection coordinates).
        ax - axes instance (overrides default axes instance)

        additional keyword arguments control text properties for labels (see
         pylab.text documentation)
        """
        # get current axes instance (if none specified).
        if ax is None and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif ax is None and self.ax is not None:
            ax = self.ax
        # don't draw meridians past latmax, always draw parallel at latmax.
        latmax = 80.
        # offset for labels.
        if yoffset is None:
            yoffset = (self.urcrnry-self.llcrnry)/100.
            if self.aspect > 1:
                yoffset = self.aspect*yoffset
            else:
                yoffset = yoffset/self.aspect
        if xoffset is None:
            xoffset = (self.urcrnrx-self.llcrnrx)/100.

        if self.projection in ['merc','cyl','mill','moll','robin','sinu']:
            lons = npy.arange(self.llcrnrlon,self.urcrnrlon+0.01,0.01)
        elif self.projection in ['tmerc']:
            lon_0 = self.projparams['lon_0']
            # tmerc only defined within +/- 90 degrees of lon_0
            lons = npy.arange(lon_0-90,lon_0+90.01,0.01)
        else:
            lons = npy.arange(0,360.01,0.01)
        # make sure latmax degree parallel is drawn if projection not merc or cyl or miller
        try:
            circlesl = circles.tolist()
        except:
            circlesl = circles
        if self.projection not in ['merc','cyl','mill','moll','robin','sinu']:
            if max(circlesl) > 0 and latmax not in circlesl:
                circlesl.append(latmax)
            if min(circlesl) < 0 and -latmax not in circlesl:
                circlesl.append(-latmax)
        xdelta = 0.01*(self.xmax-self.xmin)
        ydelta = 0.01*(self.ymax-self.ymin)
        for circ in circlesl:
            lats = circ*npy.ones(len(lons),npy.float32)
            x,y = self(lons,lats)
            # remove points outside domain.
            testx = npy.logical_and(x>=self.xmin-xdelta,x<=self.xmax+xdelta)
            x = npy.compress(testx, x)
            y = npy.compress(testx, y)
            testy = npy.logical_and(y>=self.ymin-ydelta,y<=self.ymax+ydelta)
            x = npy.compress(testy, x)
            y = npy.compress(testy, y)
            if len(x) > 1 and len(y) > 1:
                # split into separate line segments if necessary.
                # (not necessary for mercator or cylindrical or miller).
                xd = (x[1:]-x[0:-1])**2
                yd = (y[1:]-y[0:-1])**2
                dist = npy.sqrt(xd+yd)
                split = dist > 500000.
                if npy.sum(split) and self.projection not in ['merc','cyl','mill','moll','robin','sinu']:
                    ind = (npy.compress(split,squeeze(split*npy.indices(xd.shape)))+1).tolist()
                    xl = []
                    yl = []
                    iprev = 0
                    ind.append(len(xd))
                    for i in ind:
                        xl.append(x[iprev:i])
                        yl.append(y[iprev:i])
                        iprev = i
                else:
                    xl = [x]
                    yl = [y]
                # draw each line segment.
                for x,y in zip(xl,yl):
                    # skip if only a point.
                    if len(x) > 1 and len(y) > 1:
                        l = Line2D(x,y,linewidth=linewidth)
                        l.set_color(color)
                        l.set_dashes(dashes)
                        if zorder is not None:
                            l.set_zorder(zorder)
                        ax.add_line(l)
        # draw labels for parallels
        # parallels not labelled for fulldisk orthographic or geostationary
        if self.projection in ['ortho','geos'] and max(labels):
            if self._fulldisk:
                print 'Warning: Cannot label parallels on full-disk Orthographic or Geostationary basemap'
                labels = [0,0,0,0]
        # search along edges of map to see if parallels intersect.
        # if so, find x,y location of intersection and draw a label there.
        dx = (self.xmax-self.xmin)/1000.
        dy = (self.ymax-self.ymin)/1000.
        if self.projection in ['moll','robin','sinu']:
            lon_0 = self.projparams['lon_0']
        for dolab,side in zip(labels,['l','r','t','b']):
            if not dolab: continue
            # for cylindrical projections, don't draw parallels on top or bottom.
            if self.projection in ['cyl','merc','mill','moll','robin','sinu'] and side in ['t','b']: continue
            if side in ['l','r']:
                nmax = int((self.ymax-self.ymin)/dy+1)
                yy = linspace(self.llcrnry,self.urcrnry,nmax)
                # mollweide inverse transform undefined at South Pole
                if self.projection == 'moll' and yy[0] < 1.e-4:
                    yy[0] = 1.e-4
                if side == 'l':
                    lons,lats = self(self.llcrnrx*npy.ones(yy.shape,npy.float32),yy,inverse=True)
                    lons = lons.tolist(); lats = lats.tolist()
                else:
                    lons,lats = self(self.urcrnrx*npy.ones(yy.shape,npy.float32),yy,inverse=True)
                    lons = lons.tolist(); lats = lats.tolist()
                if max(lons) > 1.e20 or max(lats) > 1.e20:
                    raise ValueError,'inverse transformation undefined - please adjust the map projection region'
                # adjust so 0 <= lons < 360
                lons = [(lon+360) % 360 for lon in lons]
            else:
                nmax = int((self.xmax-self.xmin)/dx+1)
                xx = linspace(self.llcrnrx,self.urcrnrx,nmax)
                if side == 'b':
                    lons,lats = self(xx,self.llcrnry*npy.ones(xx.shape,npy.float32),inverse=True)
                    lons = lons.tolist(); lats = lats.tolist()
                else:
                    lons,lats = self(xx,self.urcrnry*npy.ones(xx.shape,npy.float32),inverse=True)
                    lons = lons.tolist(); lats = lats.tolist()
                if max(lons) > 1.e20 or max(lats) > 1.e20:
                    raise ValueError,'inverse transformation undefined - please adjust the map projection region'
                # adjust so 0 <= lons < 360
                lons = [(lon+360) % 360 for lon in lons]
            for lat in circles:
                # find index of parallel (there may be two, so
                # search from left and right).
                nl = _searchlist(lats,lat)
                nr = _searchlist(lats[::-1],lat)
                if nr != -1: nr = len(lons)-nr-1
                try: # fmt is a function that returns a formatted string
                    latlab = fmt(lat)
                except: # fmt is a format string.
                    if lat<0:
                        if rcParams['text.usetex']:
                            if labelstyle=='+/-':
                                latlabstr = r'${\/-%s\/^{\circ}}$'%fmt
                            else:
                                latlabstr = r'${%s\/^{\circ}\/S}$'%fmt
                        else:
                            if labelstyle=='+/-':
                                latlabstr = u'-%s\N{DEGREE SIGN}'%fmt
                            else:
                                latlabstr = u'%s\N{DEGREE SIGN}S'%fmt
                        latlab = latlabstr%npy.fabs(lat)
                    elif lat>0:
                        if rcParams['text.usetex']:
                            if labelstyle=='+/-':
                                latlabstr = r'${\/+%s\/^{\circ}}$'%fmt
                            else:
                                latlabstr = r'${%s\/^{\circ}\/N}$'%fmt
                        else:
                            if labelstyle=='+/-':
                                latlabstr = u'+%s\N{DEGREE SIGN}'%fmt
                            else:
                                latlabstr = u'%s\N{DEGREE SIGN}N'%fmt
                        latlab = latlabstr%lat
                    else:
                        if rcParams['text.usetex']:
                            latlabstr = r'${%s\/^{\circ}}$'%fmt
                        else:
                            latlabstr = u'%s\N{DEGREE SIGN}'%fmt
                        latlab = latlabstr%lat
                # parallels can intersect each map edge twice.
                for i,n in enumerate([nl,nr]):
                    # don't bother if close to the first label.
                    if i and abs(nr-nl) < 100: continue
                    if n >= 0:
                        if side == 'l':
                            if self.projection in ['moll','robin','sinu']:
                                xlab,ylab = self(lon_0-179.9,lat)
                            else:
                                xlab = self.llcrnrx
                            xlab = xlab-xoffset
                            ax.text(xlab,yy[n],latlab,horizontalalignment='right',verticalalignment='center',**kwargs)
                        elif side == 'r':
                            if self.projection in ['moll','robin','sinu']:
                                xlab,ylab = self(lon_0+179.9,lat)
                            else:
                                xlab = self.urcrnrx
                            xlab = xlab+xoffset
                            ax.text(xlab,yy[n],latlab,horizontalalignment='left',verticalalignment='center',**kwargs)
                        elif side == 'b':
                            ax.text(xx[n],self.llcrnry-yoffset,latlab,horizontalalignment='center',verticalalignment='top',**kwargs)
                        else:
                            ax.text(xx[n],self.urcrnry+yoffset,latlab,horizontalalignment='center',verticalalignment='bottom',**kwargs)

        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)

    def drawmeridians(self,meridians,color='k',linewidth=1., zorder=None,\
                      dashes=[1,1],labels=[0,0,0,0],labelstyle=None,\
                      fmt='%g',xoffset=None,yoffset=None,ax=None,**kwargs):
        """
        draw meridians (longitude lines).

        meridians - list containing longitude values to draw (in degrees).
        color - color to draw meridians (default black).
        linewidth - line width for meridians (default 1.)
        zorder - sets the zorder for meridians (if not specified,
        uses default zorder for Line2D class).
        dashes - dash pattern for meridians (default [1,1], i.e. 1 pixel on,
         1 pixel off).
        labels - list of 4 values (default [0,0,0,0]) that control whether
         meridians are labelled where they intersect the left, right, top or
         bottom of the plot. For example labels=[1,0,0,1] will cause meridians
         to be labelled where they intersect the left and bottom of the plot,
         but not the right and top.
        labelstyle - if set to "+/-", east and west longitudes are labelled
         with "+" and "-", otherwise they are labelled with "E" and "W".
        fmt can be is a format string to format the meridian labels
         (default '%g') or a function that takes a longitude value
         in degrees as it's only argument and returns a formatted string.
        xoffset - label offset from edge of map in x-direction
         (default is 0.01 times width of map in map projection coordinates).
        yoffset - label offset from edge of map in y-direction
         (default is 0.01 times height of map in map projection coordinates).
        ax - axes instance (overrides default axes instance)

        additional keyword arguments control text properties for labels (see
         pylab.text documentation)
        """
        # get current axes instance (if none specified).
        if ax is None and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif ax is None and self.ax is not None:
            ax = self.ax
        # don't draw meridians past latmax, always draw parallel at latmax.
        latmax = 80. # not used for cyl, merc or miller projections.
        # offset for labels.
        if yoffset is None:
            yoffset = (self.urcrnry-self.llcrnry)/100.
            if self.aspect > 1:
                yoffset = self.aspect*yoffset
            else:
                yoffset = yoffset/self.aspect
        if xoffset is None:
            xoffset = (self.urcrnrx-self.llcrnrx)/100.

        if self.projection not in ['merc','cyl','mill','moll','robin','sinu']:
            lats = npy.arange(-latmax,latmax+0.01,0.01)
        else:
            lats = npy.arange(-90,90.01,0.01)
        xdelta = 0.01*(self.xmax-self.xmin)
        ydelta = 0.01*(self.ymax-self.ymin)
        for merid in meridians:
            lons = merid*npy.ones(len(lats),npy.float32)
            x,y = self(lons,lats)
            # remove points outside domain.
            testx = npy.logical_and(x>=self.xmin-xdelta,x<=self.xmax+xdelta)
            x = npy.compress(testx, x)
            y = npy.compress(testx, y)
            testy = npy.logical_and(y>=self.ymin-ydelta,y<=self.ymax+ydelta)
            x = npy.compress(testy, x)
            y = npy.compress(testy, y)
            if len(x) > 1 and len(y) > 1:
                # split into separate line segments if necessary.
                # (not necessary for mercator or cylindrical or miller).
                xd = (x[1:]-x[0:-1])**2
                yd = (y[1:]-y[0:-1])**2
                dist = npy.sqrt(xd+yd)
                split = dist > 500000.
                if npy.sum(split) and self.projection not in ['merc','cyl','mill','moll','robin','sinu']:
                    ind = (npy.compress(split,squeeze(split*npy.indices(xd.shape)))+1).tolist()
                    xl = []
                    yl = []
                    iprev = 0
                    ind.append(len(xd))
                    for i in ind:
                        xl.append(x[iprev:i])
                        yl.append(y[iprev:i])
                        iprev = i
                else:
                    xl = [x]
                    yl = [y]
                # draw each line segment.
                for x,y in zip(xl,yl):
                    # skip if only a point.
                    if len(x) > 1 and len(y) > 1:
                        l = Line2D(x,y,linewidth=linewidth)
                        l.set_color(color)
                        l.set_dashes(dashes)
                        if zorder is not None:
                            l.set_zorder(zorder)
                        ax.add_line(l)
        # draw labels for meridians.
        # meridians not labelled for sinusoidal, mollweide, or
        # or full-disk orthographic/geostationary.
        if self.projection in ['sinu','moll'] and max(labels):
            print 'Warning: Cannot label meridians on Sinusoidal or Mollweide basemap'
            labels = [0,0,0,0]
        if self.projection in ['ortho','geos'] and max(labels):
            if self._fulldisk:
                print 'Warning: Cannot label meridians on full-disk Geostationary or Orthographic basemap'
                labels = [0,0,0,0]
        # search along edges of map to see if parallels intersect.
        # if so, find x,y location of intersection and draw a label there.
        dx = (self.xmax-self.xmin)/1000.
        dy = (self.ymax-self.ymin)/1000.
        if self.projection in ['moll','sinu','robin']:
            lon_0 = self.projparams['lon_0']
            xmin,ymin = self(lon_0-179.9,-90)
            xmax,ymax = self(lon_0+179.9,90)
        for dolab,side in zip(labels,['l','r','t','b']):
            if not dolab: continue
            # for cylindrical projections, don't draw meridians on left or right.
            if self.projection in ['cyl','merc','mill','sinu','robin','moll'] and side in ['l','r']: continue
            if side in ['l','r']:
                nmax = int((self.ymax-self.ymin)/dy+1)
                yy = linspace(self.llcrnry,self.urcrnry,nmax)
                if side == 'l':
                    lons,lats = self(self.llcrnrx*npy.ones(yy.shape,npy.float32),yy,inverse=True)
                    lons = lons.tolist(); lats = lats.tolist()
                else:
                    lons,lats = self(self.urcrnrx*npy.ones(yy.shape,npy.float32),yy,inverse=True)
                    lons = lons.tolist(); lats = lats.tolist()
                if max(lons) > 1.e20 or max(lats) > 1.e20:
                    raise ValueError,'inverse transformation undefined - please adjust the map projection region'
                # adjust so 0 <= lons < 360
                lons = [(lon+360) % 360 for lon in lons]
            else:
                nmax = int((self.xmax-self.xmin)/dx+1)
                xx = linspace(self.llcrnrx,self.urcrnrx,nmax)
                if side == 'b':
                    lons,lats = self(xx,self.llcrnry*npy.ones(xx.shape,npy.float32),inverse=True)
                    lons = lons.tolist(); lats = lats.tolist()
                else:
                    lons,lats = self(xx,self.urcrnry*npy.ones(xx.shape,npy.float32),inverse=True)
                    lons = lons.tolist(); lats = lats.tolist()
                if max(lons) > 1.e20 or max(lats) > 1.e20:
                    raise ValueError,'inverse transformation undefined - please adjust the map projection region'
                # adjust so 0 <= lons < 360
                lons = [(lon+360) % 360 for lon in lons]
            for lon in meridians:
                # adjust so 0 <= lon < 360
                lon2 = (lon+360) % 360
                # find index of meridian (there may be two, so
                # search from left and right).
                nl = _searchlist(lons,lon2)
                nr = _searchlist(lons[::-1],lon2)
                if nr != -1: nr = len(lons)-nr-1
                try: # fmt is a function that returns a formatted string
                    lonlab = fmt(lon)
                except: # fmt is a format string.
                    if lon2>180:
                        if rcParams['text.usetex']:
                            if labelstyle=='+/-':
                                lonlabstr = r'${\/-%s\/^{\circ}}$'%fmt
                            else:
                                lonlabstr = r'${%s\/^{\circ}\/W}$'%fmt
                        else:
                            if labelstyle=='+/-':
                                lonlabstr = u'-%s\N{DEGREE SIGN}'%fmt
                            else:
                                lonlabstr = u'%s\N{DEGREE SIGN}W'%fmt
                        lonlab = lonlabstr%npy.fabs(lon2-360)
                    elif lon2<180 and lon2 != 0:
                        if rcParams['text.usetex']:
                            if labelstyle=='+/-':
                                lonlabstr = r'${\/+%s\/^{\circ}}$'%fmt
                            else:
                                lonlabstr = r'${%s\/^{\circ}\/E}$'%fmt
                        else:
                            if labelstyle=='+/-':
                                lonlabstr = u'+%s\N{DEGREE SIGN}'%fmt
                            else:
                                lonlabstr = u'%s\N{DEGREE SIGN}E'%fmt
                        lonlab = lonlabstr%lon2
                    else:
                        if rcParams['text.usetex']:
                            lonlabstr = r'${%s\/^{\circ}}$'%fmt
                        else:
                            lonlabstr = u'%s\N{DEGREE SIGN}'%fmt
                        lonlab = lonlabstr%lon2
                # meridians can intersect each map edge twice.
                for i,n in enumerate([nl,nr]):
                    lat = lats[n]/100.
                    # no meridians > latmax for projections other than merc,cyl,miller.
                    if self.projection not in ['merc','cyl','mill'] and lat > latmax: continue
                    # don't bother if close to the first label.
                    if i and abs(nr-nl) < 100: continue
                    if n >= 0:
                        if side == 'l':
                            ax.text(self.llcrnrx-xoffset,yy[n],lonlab,horizontalalignment='right',verticalalignment='center',**kwargs)
                        elif side == 'r':
                            ax.text(self.urcrnrx+xoffset,yy[n],lonlab,horizontalalignment='left',verticalalignment='center',**kwargs)
                        elif side == 'b':
                            if self.projection != 'robin' or (xx[n] > xmin and xx[n] < xmax):
                                ax.text(xx[n],self.llcrnry-yoffset,lonlab,horizontalalignment='center',verticalalignment='top',**kwargs)
                        else:
                            if self.projection != 'robin' or (xx[n] > xmin and xx[n] < xmax):
                                ax.text(xx[n],self.urcrnry+yoffset,lonlab,horizontalalignment='center',verticalalignment='bottom',**kwargs)

        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)

    def gcpoints(self,lon1,lat1,lon2,lat2,npoints):
        """
        compute npoints points along a great circle with endpoints
        (lon1,lat1) and (lon2,lat2).  Returns arrays x,y
        with map projection coordinates.
        """
        gc = pyproj.Geod(a=self.rmajor,b=self.rminor)
        lonlats = gc.npts(lon1,lat1,lon2,lat2,npoints-2)
        lons=[lon1];lats=[lat1]
        for lon,lat in lonlats:
            lons.append(lon); lats.append(lat)
        lons.append(lon2); lats.append(lat2)
        x, y = self(lons, lats)
        return x,y

    def drawgreatcircle(self,lon1,lat1,lon2,lat2,del_s=100.,**kwargs):
        """
        draw a great circle on the map.

        lon1,lat1 - longitude,latitude of one endpoint of the great circle.
        lon2,lat2 - longitude,latitude of the other endpoint of the great circle.
        del_s - points on great circle computed every delta kilometers (default 100).

        Other keyword arguments (**kwargs) control plotting of great circle line,
        see pylab.plot documentation for details.

        Note:  cannot handle situations in which the great circle intersects
        the edge of the map projection domain, and then re-enters the domain.
        """
        # use great circle formula for a perfect sphere.
        gc = pyproj.Geod(a=self.rmajor,b=self.rminor)
        az12,az21,dist = gc.inv(lon1,lat1,lon2,lat2)
        npoints = int((dist+0.5*1000.*del_s)/(1000.*del_s))
        lonlats = gc.npts(lon1,lat1,lon2,lat2,npoints)
        lons = [lon1]; lats = [lat1]
        for lon, lat in lonlats:
            lons.append(lon)
            lats.append(lat)
        lons.append(lon2); lats.append(lat2)
        x, y = self(lons, lats)
        self.plot(x,y,**kwargs)

    def transform_scalar(self,datin,lons,lats,nx,ny,returnxy=False,checkbounds=False,order=1,masked=False):
        """
        interpolate a scalar field (datin) from a lat/lon grid with longitudes =
        lons and latitudes = lats to a (ny,nx) native map projection grid.
        Typically used to transform data to map projection coordinates
        so it can be plotted on the map with imshow.

        lons, lats must be rank-1 arrays containing longitudes and latitudes
        (in degrees) of datin grid in increasing order
        (i.e. from dateline eastward, and South Pole northward).
        For non-cylindrical projections (those other than
        cylindrical equidistant, mercator and miller)
        lons must fit within range -180 to 180.

        if returnxy=True, the x and y values of the native map projection grid
        are also returned.

        If checkbounds=True, values of lons and lats are checked to see that
        they lie within the map projection region.  Default is False.
        If checkbounds=False, points outside map projection region will
        be clipped to values on the boundary if masked=False. If masked=True,
        the return value will be a masked array with those points masked.

        The order keyword can be 0 for nearest-neighbor interpolation,
        or 1 for bilinear interpolation (default 1).
        """
        # check that lons, lats increasing
        delon = lons[1:]-lons[0:-1]
        delat = lats[1:]-lats[0:-1]
        if min(delon) < 0. or min(delat) < 0.:
            raise ValueError, 'lons and lats must be increasing!'
        # check that lons in -180,180 for non-cylindrical projections.
        if self.projection not in ['cyl','merc','mill']:
            lonsa = npy.array(lons)
            count = npy.sum(lonsa < -180.00001) + npy.sum(lonsa > 180.00001)
            if count > 1:
                raise ValueError,'grid must be shifted so that lons are monotonically increasing and fit in range -180,+180 (see shiftgrid function)'
            # allow for wraparound point to be outside.
            elif count == 1 and math.fabs(lons[-1]-lons[0]-360.) > 1.e-4:
                raise ValueError,'grid must be shifted so that lons are monotonically increasing and fit in range -180,+180 (see shiftgrid function)'
        if returnxy:
            lonsout, latsout, x, y = self.makegrid(nx,ny,returnxy=True)
        else:
            lonsout, latsout = self.makegrid(nx,ny)
        datout = interp(datin,lons,lats,lonsout,latsout,checkbounds=checkbounds,order=order,masked=masked)
        if returnxy:
            return datout, x, y
        else:
            return datout

    def transform_vector(self,uin,vin,lons,lats,nx,ny,returnxy=False,checkbounds=False,order=1,masked=False):
        """
        rotate and interpolate a vector field (uin,vin) from a lat/lon grid
        with longitudes = lons and latitudes = lats to a
        (ny,nx) native map projection grid.

        lons, lats must be rank-1 arrays containing longitudes and latitudes
        (in degrees) of datin grid in increasing order
        (i.e. from dateline eastward, and South Pole northward).
        For non-cylindrical projections (those other than
        cylindrical equidistant, mercator and miller)
        lons must fit within range -180 to 180.

        The input vector field is defined in spherical coordinates (it
        has eastward and northward components) while the output
        vector field is rotated to map projection coordinates (relative
        to x and y). The magnitude of the vector is preserved.

        if returnxy=True, the x and y values of the native map projection grid
        are also returned (default False).

        If checkbounds=True, values of lons and lats are checked to see that
        they lie within the map projection region.  Default is False.
        If checkbounds=False, points outside map projection region will
        be clipped to values on the boundary if masked=False. If masked=True,
        the return value will be a masked array with those points masked.

        The order keyword can be 0 for nearest-neighbor interpolation,
        or 1 for bilinear interpolation (default 1).
        """
        # check that lons, lats increasing
        delon = lons[1:]-lons[0:-1]
        delat = lats[1:]-lats[0:-1]
        if min(delon) < 0. or min(delat) < 0.:
            raise ValueError, 'lons and lats must be increasing!'
        # check that lons in -180,180 for non-cylindrical projections.
        if self.projection not in ['cyl','merc','mill']:
            lonsa = npy.array(lons)
            count = npy.sum(lonsa < -180.00001) + npy.sum(lonsa > 180.00001)
            if count > 1:
                raise ValueError,'grid must be shifted so that lons are monotonically increasing and fit in range -180,+180 (see shiftgrid function)'
            # allow for wraparound point to be outside.
            elif count == 1 and math.fabs(lons[-1]-lons[0]-360.) > 1.e-4:
                raise ValueError,'grid must be shifted so that lons are monotonically increasing and fit in range -180,+180 (see shiftgrid function)'
        lonsout, latsout, x, y = self.makegrid(nx,ny,returnxy=True)
        # interpolate to map projection coordinates.
        uin = interp(uin,lons,lats,lonsout,latsout,checkbounds=checkbounds,order=order,masked=masked)
        vin = interp(vin,lons,lats,lonsout,latsout,checkbounds=checkbounds,order=order,masked=masked)
        # rotate from geographic to map coordinates.
        if ma.isMaskedArray(uin):
            mask = ma.getmaskarray(uin)
            uin = uin.filled(1)
            vin = vin.filled(1)
            masked = True  # override kwarg with reality
        uvc = uin + 1j*vin
        uvmag = npy.abs(uvc)
        delta = 0.1 # increment in longitude
        dlon = delta*uin/uvmag
        dlat = delta*(vin/uvmag)*npy.cos(latsout*npy.pi/180.0)
        farnorth = latsout+dlat >= 90.0
        somenorth = farnorth.any()
        if somenorth:
            dlon[farnorth] *= -1.0
            dlat[farnorth] *= -1.0
        lon1 = lonsout + dlon
        lat1 = latsout + dlat
        xn, yn = self(lon1, lat1)
        vecangle = npy.arctan2(yn-y, xn-x)
        if somenorth:
            vecangle[farnorth] += npy.pi
        uvcout = uvmag * npy.exp(1j*vecangle)
        uout = uvcout.real
        vout = uvcout.imag
        if masked:
            uout = ma.array(uout, mask=mask)
            vout = ma.array(vout, mask=mask)
        if returnxy:
            return uout,vout,x,y
        else:
            return uout,vout

    def rotate_vector(self,uin,vin,lons,lats,returnxy=False):
        """
        rotate a vector field (uin,vin) on a rectilinear lat/lon grid
        with longitudes = lons and latitudes = lats from geographical into map
        projection coordinates.

        Differs from transform_vector in that no interpolation is done,
        the vector is returned on the same lat/lon grid, but rotated into
        x,y coordinates.

        lons, lats must be rank-2 arrays containing longitudes and latitudes
        (in degrees) of grid.

        if returnxy=True, the x and y values of the lat/lon grid
        are also returned (default False).

        The input vector field is defined in spherical coordinates (it
        has eastward and northward components) while the output
        vector field is rotated to map projection coordinates (relative
        to x and y). The magnitude of the vector is preserved.
        """
        x, y = self(lons, lats)
        # rotate from geographic to map coordinates.
        if ma.isMaskedArray(uin):
            mask = ma.getmaskarray(uin)
            masked = True
            uin = uin.filled(1)
            vin = vin.filled(1)
        else:
            masked = False
        uvc = uin + 1j*vin
        uvmag = npy.abs(uvc)
        delta = 0.1 # increment in longitude
        dlon = delta*uin/uvmag
        dlat = delta*(vin/uvmag)*npy.cos(lats*npy.pi/180.0)
        farnorth = lats+dlat >= 90.0
        somenorth = farnorth.any()
        if somenorth:
            dlon[farnorth] *= -1.0
            dlat[farnorth] *= -1.0
        lon1 = lons + dlon
        lat1 = lats + dlat
        xn, yn = self(lon1, lat1)
        vecangle = npy.arctan2(yn-y, xn-x)
        if somenorth:
            vecangle[farnorth] += npy.pi
        uvcout = uvmag * npy.exp(1j*vecangle)
        uout = uvcout.real
        vout = uvcout.imag
        if masked:
            uout = ma.array(uout, mask=mask)
            vout = ma.array(vout, mask=mask)
        if returnxy:
            return uout,vout,x,y
        else:
            return uout,vout

    def set_axes_limits(self,ax=None):
        """
        Set axis limits, fix aspect ratio for map domain using current
        or specified axes instance.
        """
        # get current axes instance (if none specified).
        if ax is None and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif ax is None and self.ax is not None:
            ax = self.ax
        # update data limits for map domain.
        corners = ((self.llcrnrx,self.llcrnry), (self.urcrnrx,self.urcrnry))
        ax.update_datalim( corners )
        ax.set_xlim((self.llcrnrx, self.urcrnrx))
        ax.set_ylim((self.llcrnry, self.urcrnry))
        # turn off axes frame for non-rectangular projections.
        if self.projection in ['moll','robin','sinu']:
            ax.set_frame_on(False)
        if self.projection in ['ortho','geos'] and self._fulldisk:
            ax.set_frame_on(False)
        # make sure aspect ratio of map preserved.
        # plot is re-centered in bounding rectangle.
        # (anchor instance var determines where plot is placed)
        ax.set_aspect('equal',adjustable='box',anchor=self.anchor)
        ax.apply_aspect()
        # make sure axis ticks are turned off.
        if self.noticks:
            ax.set_xticks([])
            ax.set_yticks([])

    def scatter(self, *args, **kwargs):
        """
        Plot points with markers on the map (see pylab.scatter documentation).
        extra keyword 'ax' can be used to override the default axes instance.
        """
        if not kwargs.has_key('ax') and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif not kwargs.has_key('ax') and self.ax is not None:
            ax = self.ax
        else:
            ax = kwargs.pop('ax')
        # allow callers to override the hold state by passing hold=True|False
        b = ax.ishold()
        h = kwargs.pop('hold',None)
        if h is not None:
            ax.hold(h)
        try:
            ret =  ax.scatter(*args, **kwargs)
            try:
                pylab.draw_if_interactive()
            except:
                pass
        except:
            ax.hold(b)
            raise
        ax.hold(b)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)
        return ret

    def plot(self, *args, **kwargs):
        """
        Draw lines and/or markers on the map (see pylab.plot documentation).
        extra keyword 'ax' can be used to override the default axis instance.
        """
        if not kwargs.has_key('ax') and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif not kwargs.has_key('ax') and self.ax is not None:
            ax = self.ax
        else:
            ax = kwargs.pop('ax')
        # allow callers to override the hold state by passing hold=True|False
        b = ax.ishold()
        h = kwargs.pop('hold',None)
        if h is not None:
            ax.hold(h)
        try:
            ret =  ax.plot(*args, **kwargs)
            try:
                pylab.draw_if_interactive()
            except:
                pass
        except:
            ax.hold(b)
            raise
        ax.hold(b)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)
        return ret

    def imshow(self, *args, **kwargs):
        """
        Display an image over the map (see pylab.imshow documentation).
        extent and origin keywords set automatically so image will be drawn
        over map region.
        extra keyword 'ax' can be used to override the default axis instance.
        """
        if not kwargs.has_key('ax') and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif not kwargs.has_key('ax') and self.ax is not None:
            ax = self.ax
        else:
            ax = kwargs.pop('ax')
        kwargs['extent']=(self.llcrnrx,self.urcrnrx,self.llcrnry,self.urcrnry)
        # use origin='lower', unless overridden.
        if not kwargs.has_key('origin'):
            kwargs['origin']='lower'
        # allow callers to override the hold state by passing hold=True|False
        b = ax.ishold()
        h = kwargs.pop('hold',None)
        if h is not None:
            ax.hold(h)
        try:
            ret =  ax.imshow(*args, **kwargs)
            try:
                pylab.draw_if_interactive()
            except:
                pass
        except:
            ax.hold(b)
            raise
        ax.hold(b)
        # reset current active image (only if pylab is imported).
        try:
            pylab.gci._current = ret
        except:
            pass
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)
        return ret

    def pcolor(self,x,y,data,**kwargs):
        """
        Make a pseudo-color plot over the map.
        see pylab.pcolor documentation for definition of **kwargs
        If x or y are outside projection limb (i.e. they have values > 1.e20)
        they will be convert to masked arrays with those values masked.
        As a result, those values will not be plotted.
        extra keyword 'ax' can be used to override the default axis instance.
        """
        if not kwargs.has_key('ax') and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif not kwargs.has_key('ax') and self.ax is not None:
            ax = self.ax
        else:
            ax = kwargs.pop('ax')
        # make x,y masked arrays
        # (masked where data is outside of projection limb)
        x = ma.masked_values(npy.where(x > 1.e20,1.e20,x), 1.e20)
        y = ma.masked_values(npy.where(y > 1.e20,1.e20,y), 1.e20)
        # allow callers to override the hold state by passing hold=True|False
        b = ax.ishold()
        h = kwargs.pop('hold',None)
        if h is not None:
            ax.hold(h)
        try:
            ret =  ax.pcolor(x,y,data,**kwargs)
            try:
                pylab.draw_if_interactive()
            except:
                pass
        except:
            ax.hold(b)
            raise
        ax.hold(b)
        # reset current active image (only if pylab is imported).
        try:
            pylab.gci._current = ret
        except:
            pass
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)
        return ret

    def pcolormesh(self,x,y,data,**kwargs):
        """
        Make a pseudo-color plot over the map.
        see pylab.pcolormesh documentation for definition of **kwargs
        extra keyword 'ax' can be used to override the default axis instance.
        """
        if not kwargs.has_key('ax') and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif not kwargs.has_key('ax') and self.ax is not None:
            ax = self.ax
        else:
            ax = kwargs.pop('ax')
        # allow callers to override the hold state by passing hold=True|False
        b = ax.ishold()
        h = kwargs.pop('hold',None)
        if h is not None:
            ax.hold(h)
        try:
            ret =  ax.pcolormesh(x,y,data,**kwargs)
            try:
                pylab.draw_if_interactive()
            except:
                pass
        except:
            ax.hold(b)
            raise
        ax.hold(b)
        # reset current active image (only if pylab is imported).
        try:
            pylab.gci._current = ret
        except:
            pass
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)
        return ret

    def contour(self,x,y,data,*args,**kwargs):
        """
        Make a contour plot over the map (see pylab.contour documentation).
        extra keyword 'ax' can be used to override the default axis instance.
        """
        if not kwargs.has_key('ax') and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif not kwargs.has_key('ax') and self.ax is not None:
            ax = self.ax
        else:
            ax = kwargs.pop('ax')
        # make sure x is monotonically increasing - if not,
        # print warning suggesting that the data be shifted in longitude
        # with the shiftgrid function.
        # only do this check for global projections.
        if self.projection in ['merc','cyl','mill','moll','robin','sinu']:
            xx = x[x.shape[0]/2,:]
            condition = (xx >= self.xmin) & (xx <= self.xmax)
            xl = xx.compress(condition).tolist()
            xs = xl[:]
            xs.sort()
            if xl != xs:
                print dedent("""
                     WARNING: x coordinate not montonically increasing - contour plot
                     may not be what you expect.  If it looks odd, your can either
                     adjust the map projection region to be consistent with your data, or
                     (if your data is on a global lat/lon grid) use the shiftgrid
                     function to adjust the data to be consistent with the map projection
                     region (see examples/contour_demo.py).""")
        # mask for points outside projection limb.
        xymask = npy.logical_or(npy.greater(x,1.e20),npy.greater(y,1.e20))
        data = ma.asarray(data)
        # combine with data mask.
        mask = npy.logical_or(ma.getmaskarray(data),xymask)
        data = ma.masked_array(data,mask=mask)
        # allow callers to override the hold state by passing hold=True|False
        b = ax.ishold()
        h = kwargs.pop('hold',None)
        if h is not None:
            ax.hold(h)
        try:
            CS = ax.contour(x,y,data,*args,**kwargs)
            try:
                pylab.draw_if_interactive()
            except:
                pass
        except:
            ax.hold(b)
            raise
        ax.hold(b)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)
        # reset current active image (only if pylab is imported).
        try:
            try: # new contour.
                if CS._A is not None: pylab.gci._current = CS
            except: # old contour.
                if CS[1].mappable is not None: pylab.gci._current = CS[1].mappable
        except:
            pass
        return CS

    def contourf(self,x,y,data,*args,**kwargs):
        """
        Make a filled contour plot over the map (see pylab.contourf documentation).
        If x or y are outside projection limb (i.e. they have values > 1.e20),
        the corresponing data elements will be masked.
        Extra keyword 'ax' can be used to override the default axis instance.
        """
        if not kwargs.has_key('ax') and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif not kwargs.has_key('ax') and self.ax is not None:
            ax = self.ax
        else:
            ax = kwargs.pop('ax')
        # make sure x is monotonically increasing - if not,
        # print warning suggesting that the data be shifted in longitude
        # with the shiftgrid function.
        # only do this check for global projections.
        if self.projection in ['merc','cyl','mill','moll','robin','sinu']:
            xx = x[x.shape[0]/2,:]
            condition = (xx >= self.xmin) & (xx <= self.xmax)
            xl = xx.compress(condition).tolist()
            xs = xl[:]
            xs.sort()
            if xl != xs:
                print dedent("""
                     WARNING: x coordinate not montonically increasing - contour plot
                     may not be what you expect.  If it looks odd, your can either
                     adjust the map projection region to be consistent with your data, or
                     (if your data is on a global lat/lon grid) use the shiftgrid
                     function to adjust the data to be consistent with the map projection
                     region (see examples/contour_demo.py).""")
        # mask for points outside projection limb.
        xymask = npy.logical_or(npy.greater(x,1.e20),npy.greater(y,1.e20))
        data = ma.asarray(data)
        # combine with data mask.
        mask = npy.logical_or(ma.getmaskarray(data),xymask)
        data = ma.masked_array(data,mask=mask)
        # allow callers to override the hold state by passing hold=True|False
        b = ax.ishold()
        h = kwargs.pop('hold',None)
        if h is not None:
            ax.hold(h)
        try:
            CS = ax.contourf(x,y,data,*args,**kwargs)
            try:
                pylab.draw_if_interactive()
            except:
                pass
        except:
            ax.hold(b)
            raise
        ax.hold(b)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)
        # reset current active image (only if pylab is imported).
        try:
            try: # new contour.
                if CS._A is not None: pylab.gci._current = CS
            except: # old contour.
                if CS[1].mappable is not None: pylab.gci._current = CS[1].mappable
        except:
            pass
        return CS

    def quiver(self, x, y, u, v, *args, **kwargs):
        """
        Make a vector plot (u, v) with arrows on the map.

        Extra arguments (*args and **kwargs) passed to quiver Axes method (see
        pylab.quiver documentation for details).
        extra keyword 'ax' can be used to override the default axis instance.
        """
        if not kwargs.has_key('ax') and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif not kwargs.has_key('ax') and self.ax is not None:
            ax = self.ax
        else:
            ax = kwargs.pop('ax')
        # allow callers to override the hold state by passing hold=True|False
        b = ax.ishold()
        h = kwargs.pop('hold',None)
        if h is not None:
            ax.hold(h)
        try:
            ret =  ax.quiver(x,y,u,v,*args,**kwargs)
            try:
                pylab.draw_if_interactive()
            except:
                pass
        except:
            ax.hold(b)
            raise
        ax.hold(b)
        # set axes limits to fit map region.
        self.set_axes_limits(ax=ax)
        return ret

    def drawlsmask(self,rgba_land,rgba_ocean,lsmask=None,
                   lsmask_lons=None,lsmask_lats=None,lakes=False,**kwargs):
        """
        draw land-sea mask image.

        *Note*  the land-sea mask image cannot be overlaid on top
        of other images, due to limitations in matplotlib image handling.

        land is colored with rgba integer tuple rgba_land.
        ocean is colored with rgba integer tuple rgba_ocean.

        For example, to color oceans blue and land green, use
        rgba_ocean = (0,0,255,255) and rgba_land  = (0,255,0,255).
        To make oceans transparent (useful if you just want to mask land
        regions over another image), use rgba_ocean = (0,0,255,0).

        If lakes=True, inland lakes are also colored with
        rgba_ocean (default is lakes=False).

        Default land-sea mask is from
        http://www.ngdc.noaa.gov/seg/cdroms/graham/graham/graham.htm
        and has 5-minute resolution.

        To specify your own global land-sea mask, set the
        lsmask keyword to a (nlats, nlons) array
        with 0's for ocean pixels, 1's for land pixels and
        optionally 2's for inland lake pixels.
        The lsmask_lons keyword should be a 1-d array
        with the longitudes of the mask, lsmask_lats should be
        a 1-d array with the latitudes.  Longitudes should be ordered
        from -180 W eastward, latitudes from -90 S northward.
        If any of the lsmask, lsmask_lons or lsmask_lats keywords are not
        set, the default land-sea mask is used.

        extra keyword 'ax' can be used to override the default axis instance.
        """
        # look for axes instance (as keyword, an instance variable
        # or from pylab.gca().
        if not kwargs.has_key('ax') and self.ax is None:
            try:
                ax = pylab.gca()
            except:
                import pylab
                ax = pylab.gca()
        elif not kwargs.has_key('ax') and self.ax is not None:
            ax = self.ax
        else:
            ax = kwargs.pop('ax')
        # if lsmask,lsmask_lons,lsmask_lats keywords not given,
        # read default land-sea mask in from file.
        if lsmask is None or lsmask_lons is None or lsmask_lats is None:
            # if lsmask instance variable already set, data already
            # read in.
            if self.lsmask is None:
                # read in land/sea mask.
                lsmaskf = open(os.path.join(basemap_datadir,'5minmask.bin'),'rb')
                nlons = 4320; nlats = nlons/2
                delta = 360./float(nlons)
                lsmask_lons = npy.arange(-180+0.5*delta,180.,delta)
                lsmask_lats = npy.arange(-90.+0.5*delta,90.,delta)
                lsmask = npy.reshape(npy.fromstring(lsmaskf.read(),npy.uint8),(nlats,nlons))
                lsmaskf.close()
        # instance variable lsmask is set on first invocation,
        # it contains the land-sea mask interpolated to the native
        # projection grid.  Further calls to drawlsmask will not
        # redo the interpolation (unless a new land-sea mask is passed
        # in via the lsmask, lsmask_lons, lsmask_lats keywords).

        # transform mask to nx x ny regularly spaced native projection grid
        # nx and ny chosen to have roughly the same horizontal
        # resolution as mask.
        if self.lsmask is None:
            nlons = len(lsmask_lons)
            nlats = len(lsmask_lats)
            if self.projection == 'cyl':
                dx = lsmask_lons[1]-lsmask_lons[0]
            else:
                dx = 2.*math.pi*self.rmajor/float(nlons)
            nx = int((self.xmax-self.xmin)/dx)+1; ny = int((self.ymax-self.ymin)/dx)+1
        # interpolate rgba values from proj='cyl' (geographic coords)
        # to a rectangular map projection grid.
            mask,x,y = self.transform_scalar(lsmask,lsmask_lons,\
                       lsmask_lats,nx,ny,returnxy=True,order=0,masked=255)
            # for these projections, points outside the projection
            # limb have to be set to transparent manually.
            if self.projection in ['moll','robin','sinu']:
                lons, lats = self(x, y, inverse=True)
                lon_0 = self.projparams['lon_0']
                lats = lats[:,nx/2]
                lons1 = (lon_0+180.)*npy.ones(lons.shape[0],npy.float64)
                lons2 = (lon_0-180.)*npy.ones(lons.shape[0],npy.float64)
                xmax,ytmp = self(lons1,lats)
                xmin,ytmp = self(lons2,lats)
                for j in range(lats.shape[0]):
                    xx = x[j,:]
                    mask[j,:]=npy.where(npy.logical_or(xx<xmin[j],xx>xmax[j]),\
                                        255,mask[j,:])
            self.lsmask = mask
        # optionally, set lakes to ocean color.
        if lakes:
            mask = npy.where(self.lsmask==2,0,self.lsmask)
        else:
            mask = self.lsmask
        ny, nx = mask.shape
        rgba = npy.ones((ny,nx,4),npy.uint8)
        rgba_land = npy.array(rgba_land,npy.uint8)
        rgba_ocean = npy.array(rgba_ocean,npy.uint8)
        for k in range(4):
            rgba[:,:,k] = npy.where(mask,rgba_land[k],rgba_ocean[k])
        # make points outside projection limb transparent.
        rgba[:,:,3] = npy.where(mask==255,0,rgba[:,:,3])
        # plot mask as rgba image.
        im = self.imshow(rgba,interpolation='nearest',ax=ax,**kwargs)
        return im

### End of Basemap class

def _searchlist(a,x):
    """
    like bisect, but works for lists that are not sorted,
    and are not in increasing order.
    returns -1 if x does not fall between any two elements"""
    # make sure x is a float (and not an array scalar)
    x = float(x)
    itemprev = a[0]
    nslot = -1
    eps = 180.
    for n,item in enumerate(a[1:]):
        if item < itemprev:
            if itemprev-item>eps:
                if ((x>itemprev and x<=360.) or (x<item and x>=0.)):
                    nslot = n+1
                    break
            elif x <= itemprev and x > item and itemprev:
                nslot = n+1
                break
        else:
            if item-itemprev>eps:
                if ((x<itemprev and x>=0.) or (x>item and x<=360.)):
                    nslot = n+1
                    break
            elif x >= itemprev and x < item:
                nslot = n+1
                break
        itemprev = item
    return nslot

def interp(datain,xin,yin,xout,yout,checkbounds=False,masked=False,order=1):
    """
    dataout = interp(datain,xin,yin,xout,yout,order=1)

    interpolate data (datain) on a rectilinear grid (with x=xin
    y=yin) to a grid with x=xout, y=yout.

    datain is a rank-2 array with 1st dimension corresponding to y,
    2nd dimension x.

    xin, yin are rank-1 arrays containing x and y of
    datain grid in increasing order.

    xout, yout are rank-2 arrays containing x and y of desired output grid.

    If checkbounds=True, values of xout and yout are checked to see that
    they lie within the range specified by xin and xin.  Default is False.
    If checkbounds=False, and xout,yout are outside xin,yin, interpolated
    values will be clipped to values on boundary of input grid (xin,yin)
    if masked=False. If masked=True, the return value will be a masked
    array with those points masked. If masked is set to a number, then
    points outside the range of xin and yin will be set to that number.

    The order keyword can be 0 for nearest-neighbor interpolation,
    or 1 for bilinear interpolation (default 1).

    If datain is a masked array and order=1 (bilinear interpolation) is
    used, elements of dataout will be masked if any of the four surrounding
    points in datain are masked.  To avoid this, do the interpolation in two
    passes, first with order=1 (producing dataout1), then with order=0
    (producing dataout2).  Then replace all the masked values in dataout1
    with the corresponding elements in dataout2 (using numerix.where).
    This effectively uses nearest neighbor interpolation if any of the
    four surrounding points in datain are masked, and bilinear interpolation
    otherwise.
    """
    # xin and yin must be monotonically increasing.
    if xin[-1]-xin[0] < 0 or yin[-1]-yin[0] < 0:
        raise ValueError, 'xin and yin must be increasing!'
    if xout.shape != yout.shape:
        raise ValueError, 'xout and yout must have same shape!'
    # check that xout,yout are
    # within region defined by xin,yin.
    if checkbounds:
        if xout.min() < xin.min() or \
           xout.max() > xin.max() or \
           yout.min() < yin.min() or \
           yout.max() > yin.max():
            raise ValueError, 'yout or xout outside range of yin or xin'
    # compute grid coordinates of output grid.
    delx = xin[1:]-xin[0:-1]
    dely = yin[1:]-yin[0:-1]
    if max(delx)-min(delx) < 1.e-4 and max(dely)-min(dely) < 1.e-4:
        # regular input grid.
        xcoords = (len(xin)-1)*(xout-xin[0])/(xin[-1]-xin[0])
        ycoords = (len(yin)-1)*(yout-yin[0])/(yin[-1]-yin[0])
    else:
        # irregular (but still rectilinear) input grid.
        xoutflat = xout.flatten(); youtflat = yout.flatten()
        ix = (npy.searchsorted(xin,xoutflat)-1).tolist()
        iy = (npy.searchsorted(yin,youtflat)-1).tolist()
        xoutflat = xoutflat.tolist(); xin = xin.tolist()
        youtflat = youtflat.tolist(); yin = yin.tolist()
        xcoords = []; ycoords = []
        for n,i in enumerate(ix):
            if i < 0:
                xcoords.append(-1) # outside of range on xin (lower end)
            elif i >= len(xin)-1:
                xcoords.append(len(xin)) # outside range on upper end.
            else:
                xcoords.append(float(i)+(xoutflat[n]-xin[i])/(xin[i+1]-xin[i]))
        for m,j in enumerate(iy):
            if j < 0:
                ycoords.append(-1) # outside of range of yin (on lower end)
            elif j >= len(yin)-1:
                ycoords.append(len(yin)) # outside range on upper end
            else:
                ycoords.append(float(j)+(youtflat[m]-yin[j])/(yin[j+1]-yin[j]))
        xcoords = npy.reshape(xcoords,xout.shape)
        ycoords = npy.reshape(ycoords,yout.shape)
    # data outside range xin,yin will be clipped to
    # values on boundary.
    if masked:
        xmask = npy.logical_or(npy.less(xcoords,0),npy.greater(xcoords,len(xin)-1))
        ymask = npy.logical_or(npy.less(ycoords,0),npy.greater(ycoords,len(yin)-1))
        xymask = npy.logical_or(xmask,ymask)
    xcoords = npy.clip(xcoords,0,len(xin)-1)
    ycoords = npy.clip(ycoords,0,len(yin)-1)
    # interpolate to output grid using bilinear interpolation.
    if order == 1:
        xi = xcoords.astype(npy.int32)
        yi = ycoords.astype(npy.int32)
        xip1 = xi+1
        yip1 = yi+1
        xip1 = npy.clip(xip1,0,len(xin)-1)
        yip1 = npy.clip(yip1,0,len(yin)-1)
        delx = xcoords-xi.astype(npy.float32)
        dely = ycoords-yi.astype(npy.float32)
        dataout = (1.-delx)*(1.-dely)*datain[yi,xi] + \
                  delx*dely*datain[yip1,xip1] + \
                  (1.-delx)*dely*datain[yip1,xi] + \
                  delx*(1.-dely)*datain[yi,xip1]
    elif order == 0:
        xcoordsi = npy.around(xcoords).astype(npy.int32)
        ycoordsi = npy.around(ycoords).astype(npy.int32)
        dataout = datain[ycoordsi,xcoordsi]
    else:
        raise ValueError,'order keyword must be 0 or 1'
    if masked and isinstance(masked,bool):
        dataout = ma.masked_array(dataout)
        newmask = ma.mask_or(ma.getmask(dataout), xymask)
        dataout = ma.masked_array(dataout,mask=newmask)
    elif masked and is_scalar(masked):
        dataout = npy.where(xymask,masked,dataout)
    return dataout

def shiftgrid(lon0,datain,lonsin,start=True):
    """
    shift global lat/lon grid east or west.
    assumes wraparound (or cyclic point) is included.

    lon0:  starting longitude for shifted grid
           (ending longitude if start=False). lon0 must be on
           input grid (within the range of lonsin).
    datain:  original data.
    lonsin:  original longitudes.
    start[True]: if True, lon0 represents the starting longitude
    of the new grid. if False, lon0 is the ending longitude.

    returns dataout,lonsout (data and longitudes on shifted grid).
    """
    if npy.fabs(lonsin[-1]-lonsin[0]-360.) > 1.e-4:
        raise ValueError, 'cyclic point not included'
    if lon0 < lonsin[0] or lon0 > lonsin[-1]:
        raise ValueError, 'lon0 outside of range of lonsin'
    i0 = npy.argmin(npy.fabs(lonsin-lon0))
    dataout = npy.zeros(datain.shape,datain.dtype)
    lonsout = npy.zeros(lonsin.shape,lonsin.dtype)
    if start:
        lonsout[0:len(lonsin)-i0] = lonsin[i0:]
    else:
        lonsout[0:len(lonsin)-i0] = lonsin[i0:]-360.
    dataout[:,0:len(lonsin)-i0] = datain[:,i0:]
    if start:
        lonsout[len(lonsin)-i0:] = lonsin[1:i0+1]+360.
    else:
        lonsout[len(lonsin)-i0:] = lonsin[1:i0+1]
    dataout[:,len(lonsin)-i0:] = datain[:,1:i0+1]
    return dataout,lonsout

def addcyclic(arrin,lonsin):
    """
    arrout, lonsout = addcyclic(arrin, lonsin)

    Add cyclic (wraparound) point in longitude.
    """
    nlats = arrin.shape[0]
    nlons = arrin.shape[1]
    if hasattr(arrin,'mask'):
        arrout  = ma.zeros((nlats,nlons+1),arrin.dtype)
    else:
        arrout  = npy.zeros((nlats,nlons+1),arrin.dtype)
    arrout[:,0:nlons] = arrin[:,:]
    arrout[:,nlons] = arrin[:,0]
    if hasattr(lonsin,'mask'):
        lonsout = ma.zeros(nlons+1,lonsin.dtype)
    else:
        lonsout = npy.zeros(nlons+1,lonsin.dtype)
    lonsout[0:nlons] = lonsin[:]
    lonsout[nlons]  = lonsin[-1] + lonsin[1]-lonsin[0]
    return arrout,lonsout

def _choosecorners(width,height,**kwargs):
    """
    private function to determine lat/lon values of projection region corners,
    given width and height of projection region in meters.
    """
    p = pyproj.Proj(kwargs)
    urcrnrlon, urcrnrlat = p(0.5*width,0.5*height, inverse=True)
    llcrnrlon, llcrnrlat = p(-0.5*width,-0.5*height, inverse=True)
    corners = llcrnrlon,llcrnrlat,urcrnrlon,urcrnrlat
    # test for invalid projection points on output
    if llcrnrlon > 1.e20 or urcrnrlon > 1.e20:
        raise ValueError, 'width and/or height too large for this projection, try smaller values'
    else:
        return corners

has_pynio = True
try:
    from PyNGL import nio
except ImportError:
    has_pynio = False

def NetCDFFile(file, maskandscale=True):
    """NetCDF File reader.  API is the same as Scientific.IO.NetCDF.
    If 'file' is a URL that starts with 'http', it is assumed
    to be a remote OPenDAP dataset, and the python dap client is used
    to retrieve the data. Only the OPenDAP Array and Grid data
    types are recognized.  If file does not start with 'http', it
    is assumed to be a local file.  If possible, the file will be read 
    with a pure python NetCDF reader, otherwise PyNIO 
    (http://www.pyngl.ucar.edu/Nio.shtml) will be used (if it is installed).
    PyNIO supports NetCDF version 4, GRIB1, GRIB2, HDF4 and HDFEOS2 files.
    Data read from OPenDAP and NetCDF version 3 datasets will 
    automatically be converted to masked arrays if the variable has either
    a 'missing_value' or '_FillValue' attribute, and some data points
    are equal to the value specified by that attribute.  In addition,
    variables stored as integers that have the 'scale_factor' and
    'add_offset' attribute will automatically be rescaled to floats when
    read. If PyNIO is used, neither of the automatic conversions will
    be performed.  To suppress these automatic conversions, set the
    maskandscale keyword to False. 
    """
    if file.startswith('http'):
        return pupynere._RemoteFile(file,maskandscale)
    else:
        # use pynio if it is installed and the file cannot
        # be read with the pure python netCDF reader.  This allows
        # netCDF version 4, GRIB1, GRIB2, HDF4 and HDFEOS files
        # to be read.
        if has_pynio:
            try:
                f = pupynere._LocalFile(file,maskandscale)
            except:
                f = nio.open_file(file)
        # otherwise, use the pupynere netCDF 3 pure python reader.
        # (will fail if file is not a netCDF version 3 file).
        else:
            f = pupynere._LocalFile(file,maskandscale)
        return f

def num2date(times,units,calendar='standard'):
    """
    Return datetime objects given numeric time values. The units
    of the numeric time values are described by the units argument
    and the calendar keyword. The datetime objects represent 
    UTC with no time-zone offset, even if the specified 
    units contain a time-zone offset.

    Like the matplotlib num2date function, except that it allows
    for different units and calendars.  Behaves the same if
    units = 'days since 0001-01-01 00:00:00' and 
    calendar = 'proleptic_gregorian'.

    Arguments:

    times - numeric time values. Maximum resolution is 1 second.

    units - a string of the form '<time-units> since <reference time>'
     describing the time units. <time-units> can be days, hours, minutes
     or seconds.  <reference-time> is the time origin. A valid choice
     would be units='hours since 0001-01-01 00:00:00'.

    calendar - describes the calendar used in the time calculations. 
     All the values currently defined in the CF metadata convention 
     (http://cf-pcmdi.llnl.gov/documents/cf-conventions/) are supported.
     Valid calendars 'standard', 'gregorian', 'proleptic_gregorian'
     'noleap', '365_day', '360_day', 'julian', 'all_leap', '366_day'.
     Default is 'standard', which is a mixed Julian/Gregorian calendar.

    Returns a datetime instance, or an array of datetime instances.

    The datetime instances returned are 'real' python datetime 
    objects if the date falls in the Gregorian calendar (i.e. 
    calendar='proleptic_gregorian', or calendar = 'standard' or 'gregorian'
    and the date is after 1582-10-15). Otherwise, they are 'phony' datetime 
    objects which support some but not all the methods of 'real' python
    datetime objects.  This is because the python datetime module cannot
    the weird dates in some calendars (such as '360_day' and 'all_leap'
    which don't exist in any real world calendar.
    """
    cdftime = netcdftime.utime(units,calendar=calendar)
    return cdftime.num2date(times)

def date2num(dates,units,calendar='standard'):
    """
    Return numeric time values given datetime objects. The units
    of the numeric time values are described by the units argument
    and the calendar keyword. The datetime objects must
    be in UTC with no time-zone offset.  If there is a 
    time-zone offset in units, it will be applied to the
    returned numeric values.

    Like the matplotlib date2num function, except that it allows
    for different units and calendars.  Behaves the same if
    units = 'days since 0001-01-01 00:00:00' and 
    calendar = 'proleptic_gregorian'.

    Arguments:

    dates - A datetime object or a sequence of datetime objects.

    units - a string of the form '<time-units> since <reference time>'
     describing the time units. <time-units> can be days, hours, minutes
     or seconds.  <reference-time> is the time origin. A valid choice
     would be units='hours since 0001-01-01 00:00:00'.

    calendar - describes the calendar used in the time calculations. 
     All the values currently defined in the CF metadata convention 
     (http://cf-pcmdi.llnl.gov/documents/cf-conventions/) are supported.
     Valid calendars 'standard', 'gregorian', 'proleptic_gregorian'
     'noleap', '365_day', '360_day', 'julian', 'all_leap', '366_day'.
     Default is 'standard', which is a mixed Julian/Gregorian calendar.

    Returns a numeric time value, or an array of numeric time values.

    The maximum resolution of the numeric time values is 1 second.
    """
    cdftime = netcdftime.utime(units,calendar=calendar)
    return cdftime.date2num(dates)
