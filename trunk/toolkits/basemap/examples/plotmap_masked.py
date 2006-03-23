# make plot of etopo bathymetry/topography data on
# lambert conformal conic map projection, drawing coastlines, state and
# country boundaries, and parallels/meridians.

# demonstrates use of masked arrays to mask out certain regions
# (in this case the oceans)

from matplotlib.toolkits.basemap import Basemap, shiftgrid
from pylab import *
from matplotlib.numerix import ma
import matplotlib.colors as colors

# read in topo data (on a regular lat/lon grid)
# longitudes go from 20 to 380.
topoin = array(load('etopo20data.gz'),'d')
lonsin = array(load('etopo20lons.gz'),'d')
latsin = array(load('etopo20lats.gz'),'d')
# shift data so lons go from -180 to 180 instead of 20 to 380.
topoin,lonsin = shiftgrid(180.,topoin,lonsin,start=False)

# setup of basemap ('lcc' = lambert conformal conic).
# use major and minor sphere radii from WGS84 ellipsoid.
m = Basemap(llcrnrlon=-145.5,llcrnrlat=1.,urcrnrlon=-2.566,urcrnrlat=46.352,\
            rsphere=(6378137.00,6356752.3142),\
            resolution='l',area_thresh=1000.,projection='lcc',\
            lat_1=50.,lon_0=-107.)
# transform to nx x ny regularly spaced native projection grid
nx = int((m.xmax-m.xmin)/40000.)+1; ny = int((m.ymax-m.ymin)/40000.)+1
topodat,x,y = m.transform_scalar(topoin,lonsin,latsin,nx,ny,returnxy=True)
# create the figure.
fig=figure(figsize=(8,8))
# add an axes, leaving room for colorbar on the right.
ax = fig.add_axes([0.1,0.1,0.7,0.7])
# make topodat a masked array, masking values lower than sea level.
topodat = where(topodat < 0.,1.e10,topodat)
topodatm = ma.masked_values(topodat, 1.e10)
palette = cm.YlOrRd
palette.set_bad('aqua', 1.0)
# plot image over map with imshow.
im = m.imshow(topodatm,palette,norm=colors.normalize(vmin=0.0,vmax=3000.0,clip=False))
# setup colorbar axes instance.
l,b,w,h = ax.get_position()
cax = axes([l+w+0.075, b, 0.05, h])
colorbar(tickfmt='%d', cax=cax) # draw colorbar
axes(ax)  # make the original axes current again
# plot blue dot on boulder, colorado and label it as such.
xpt,ypt = m(-104.237,40.125) 
m.plot([xpt],[ypt],'bo') 
text(xpt+100000,ypt+100000,'Boulder')
# draw coastlines and political boundaries.
m.drawcoastlines()
m.drawcountries()
m.drawstates()
# draw parallels and meridians.
# label on left, right and bottom of map.
parallels = arange(0.,80,20.)
m.drawparallels(parallels,labels=[1,1,0,1])
meridians = arange(10.,360.,30.)
m.drawmeridians(meridians,labels=[1,1,0,1])
# set title.
title('Masked ETOPO Topography - via imshow')
show()
