from matplotlib.toolkits.basemap import Basemap
from pylab import title, show, arange, figure

# create Basemap instance for Geostationary (satellite view) projection.
lon_0 = float(raw_input('enter reference longitude (lon_0):'))
#h = float(raw_input('enter satellite height above equator in meters (satellite_height):'))
h = 35785831.0

# map with land/sea mask plotted
fig=figure()
m = Basemap(projection='geos',lon_0=lon_0,satellite_height=h,rsphere=(6378137.00,6356752.3142),resolution=None)
# plot land-sea mask.
rgba_land = (0,255,0,255) # land green.
rgba_ocean = (0,0,255,255) # ocean blue.
# lakes=True means plot inland lakes with ocean color.
m.drawlsmask(rgba_land, rgba_ocean, lakes=True)
# draw parallels and meridians.
m.drawparallels(arange(-90.,120.,30.))
m.drawmeridians(arange(0.,420.,60.))
m.drawmapboundary()
title('Geostationary Map Centered on Lon=%s, Satellite Height=%s' % (lon_0,h))

# map with continents drawn and filled.
fig = figure()
m = Basemap(projection='geos',lon_0=lon_0,satellite_height=h,rsphere=(6378137.00,6356752.3142),resolution='l')
m.drawcoastlines()
m.fillcontinents(color='coral')
m.drawcountries()
# draw parallels and meridians.
m.drawparallels(arange(-90.,120.,30.))
m.drawmeridians(arange(0.,420.,60.))
m.drawmapboundary()
title('Geostationary Map Centered on Lon=%s, Satellite Height=%s' % (lon_0,h))
show()
show()
