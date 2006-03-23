#####################################
# pylab-free version of simpletest.py
#####################################
# set backend to Agg.
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.toolkits.basemap import Basemap
from matplotlib.figure import Figure
from matplotlib.mlab import meshgrid
import matplotlib.numerix as nx
import matplotlib.cm as cm
from matplotlib.mlab import load

# read in topo data (on a regular lat/lon grid)
# longitudes go from 20 to 380.
etopo = nx.array(load('etopo20data.gz'),'d')
lons = nx.array(load('etopo20lons.gz'),'d')
lats = nx.array(load('etopo20lats.gz'),'d')
# create figure.
fig = Figure()
canvas = FigureCanvas(fig)
# create axes instance, leaving room for colorbar at bottom.
ax = fig.add_axes([0.125,0.175,0.75,0.75])
# create Basemap instance for Robinson projection.
# set 'ax' keyword so pylab won't be imported.
m = Basemap(projection='robin',lon_0=0.5*(lons[0]+lons[-1]),ax=ax)
# make filled contour plot.
x, y = m(*meshgrid(lons, lats))
cs = m.contourf(x,y,etopo,30,cmap=cm.jet)
# draw coastlines.
m.drawcoastlines()
# draw a line around the map region.
m.drawmapboundary()
# draw parallels and meridians.
m.drawparallels(nx.arange(-60.,90.,30.),labels=[1,0,0,0],fontsize=10)
m.drawmeridians(nx.arange(0.,420.,60.),labels=[0,0,0,1],fontsize=10)
# add a title.
ax.set_title('Robinson Projection')
# add a colorbar.
l,b,w,h = ax.get_position()
cax = fig.add_axes([l, b-0.1, w, 0.03],frameon=False) # setup colorbar axes
fig.colorbar(cs, cax=cax, tickfmt='%d', orientation='horizontal',clabels=cs.levels[::3]) 
# save image (width 800 pixels with dpi=100 and fig width 8 inches).
canvas.print_figure('simpletest',dpi=100)
# done.
print 'image saved in simpletest.png'
