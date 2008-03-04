from mpl_toolkits.basemap import Basemap
from pylab import title, show, arange, figure

# create Basemap instance for Orthographic (satellite view) projection.
lon_0 = float(raw_input('enter reference longitude (lon_0):'))
lat_0 = float(raw_input('enter reference latitude (lat_0):'))

# map with land/sea mask plotted
fig = figure()
m = Basemap(projection='ortho',lon_0=lon_0,lat_0=lat_0,resolution=None)
# plot land-sea mask.
rgba_land = (0,255,0,255) # land green.
rgba_ocean = (0,0,255,255) # ocean blue.
# lakes=True means plot inland lakes with ocean color.
m.drawlsmask(rgba_land, rgba_ocean, lakes=True)
# draw parallels and meridians.
m.drawparallels(arange(-90.,120.,30.))
m.drawmeridians(arange(0.,420.,60.))
m.drawmapboundary()
title('Orthographic Map Centered on Lon=%s, Lat=%s' % (lon_0,lat_0))

# map with continents drawn and filled.
fig = figure()
m = Basemap(projection='ortho',lon_0=lon_0,lat_0=lat_0,resolution='l')
m.drawcoastlines()
m.fillcontinents(color='coral',lake_color='aqua')
m.drawcountries()
# draw parallels and meridians.
m.drawparallels(arange(-90.,120.,30.))
m.drawmeridians(arange(0.,420.,60.))
m.drawmapboundary(fill_color='aqua')
# add a map scale.
length = 5000 
x1,y1 = 0.2*m.xmax, 0.2*m.ymax
lon1,lat1 = m(x1,y1,inverse=True)
m.drawmapscale(lon1,lat1,lon_0,lat_0,length,fontsize=8,barstyle='fancy',\
               labelstyle='fancy',units='km')
title('Orthographic Map Centered on Lon=%s, Lat=%s' % (lon_0,lat_0))
show()
