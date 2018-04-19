from bokeh.io import show, output_file, curdoc
from bokeh.models import ColumnDataSource, BoxAnnotation
from bokeh.plotting import figure
from bokeh.layouts import gridplot, column
from bokeh.transform import jitter
import numpy as np
import pandas as pd


VERBOSE   = 1     # set verbosity level
nchannels = 120   # arbitrary. max numbers of channels to be considered for building patterns
tDrift    = 15.6  # in bx
xcell     = 42.   # cell width in mm
ycell     = 13.   # cell height in mm
vDrift    = xcell*0.5 / (tDrift*25.) # in mm/ns 

### DEFINE SOURCE OF COLUMNAR DATA
source          = ColumnDataSource(dict(tdc_channel=[], layer=[], fpga=[], channel_shifted=[], layer_shifted=[]))
source_hits     = ColumnDataSource(dict(thehist=[], theleftedges=[], therightedges=[]))
source_hits_orb = ColumnDataSource(dict(thehist=[], theleftedges=[], therightedges=[]))
source_hits_bx  = ColumnDataSource(dict(thehist=[], theleftedges=[], therightedges=[]))
source_hits_tdc = ColumnDataSource(dict(thehist=[], theleftedges=[], therightedges=[]))

### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)
p_hits = figure(plot_width=600,
                plot_height=400,
                title="Hits per channel",
                x_axis_label="Channel",
                )

p_hits.quad(top='thehist',
            bottom=0,
            left='theleftedges',
            right='therightedges',
            #line_color="white",
            source=source_hits)

### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)
p_hits_orb = figure(plot_width=600,
                plot_height=400,
                title="Hits per orbit",
                x_axis_label="Orbit",
                )

p_hits_orb.quad(top='thehist',
            bottom=0,
            left='theleftedges',
            right='therightedges',
            #line_color="white",
            source=source_hits_orb)

### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)
p_hits_bx = figure(plot_width=600,
                plot_height=400,
                title="Hits per bx",
                x_axis_label="Bx",
                )

p_hits_bx.quad(top='thehist',
            bottom=0,
            left='theleftedges',
            right='therightedges',
            #line_color="white",
            source=source_hits_bx)

### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)
p_hits_tdc = figure(plot_width=600,
                plot_height=400,
                title="Hits per TDC count",
                x_axis_label="TDC count",
                )

p_hits_tdc.quad(top='thehist',
            bottom=0,
            left='theleftedges',
            right='therightedges',
            #line_color="white",
            source=source_hits_tdc)


#
#
#
# ### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)
# p_bx = figure(plot_width=800,
#               plot_height=600,
#               title="Hits per bx",
#               x_axis_label="Bx",
#               )
#
# p_bx.Quad(source=source,
#                values='bx',
#               )
#
#
# ### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)
# p_orbit = figure(plot_width=800,
#               plot_height=600,
#               title="Hits per orbit",
#               x_axis_label="Orbit",
#               )
#
# p_orbit.Quad(source=source,
#                values='orbit',
#               )
#
#
# ### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)
# p_count = figure(plot_width=800,
#               plot_height=600,
#               title="Hits per TDC count",
#               x_axis_label="TDC count",
#               )
#
# p_count.Quad(source=source,
#                values='orbit',
#               )
#


###########################
### LIVE OCCUPANCY PLOT ###
###########################

### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)
p = figure(plot_width=600,
           plot_height=400,
           y_range=[0,12],
           x_range=[0,140],
           title="Occupancy",
           x_axis_label="Channel",
           y_axis_label="Layer",
          )

### ADD HORIZONTAL LINES TO FIGURE
p.line([0,140], 4)
p.line([0,140], 8)

### ADD GREY BOX TO FIGURE
mid_box = BoxAnnotation(bottom=4, top=8, fill_alpha=0.1, fill_color='grey')
p.add_layout(mid_box)

### ADD TEXT TO FIGURE
p.text(64, 9.75, text=["Phi1"],  text_color="firebrick", text_align="center", text_font_size="20pt", alpha=0.25)
p.text(64, 5.75, text=["Theta"], text_color="firebrick", text_align="center", text_font_size="20pt", alpha=0.25)
p.text(64, 1.75, text=["Phi2"],  text_color="firebrick", text_align="center", text_font_size="20pt", alpha=0.25)

### DEFINE FILLING RULE FOR SCATTER PLOT
p.scatter(source=source,
          x='channel_shifted',
          y='layer_shifted',
          alpha=0.1,
          marker='square',
          size=10,
          line_color="navy",
          fill_color="orange",
         )


### UPDATE RULE
global maxrows
maxrows = 0
def update_data():
  ### IMPORT DATAFRAME FROM CSV FILE (EXCLUDE LINES PREVIOUSLY READ)
  excluderows = range(1,maxrows+1)
  hits=pd.read_csv("/mnt/rammo/output_unpacked_1024_w0_newfw_newlib.txt", skiprows=excluderows)
  global maxrows
  thisnrows = len(hits.index)
  if thisnrows > maxrows:
    maxrows += thisnrows

  hits=hits[hits.HEAD == 1]

  hits = hits[(hits['TDC_CHANNEL'] != 139)]
  

  ### ADD LAYER AND SHIFTED-X COLUMNS TO DATAFRAME
  conditions  = [ (hits['TDC_CHANNEL'] % 4 == 1 ),  (hits['TDC_CHANNEL'] % 4 == 2 ), (hits['TDC_CHANNEL'] % 4 == 3 ), (hits['TDC_CHANNEL'] % 4 == 0 ),]
  chanshift_x = [                                  0,                                  -1,                                  0,                                 -1,]
  layer_y     = [                                  1,                                   3,                                  2,                                  4,]
  pos_y       = [                          ycell*3.5,                           ycell*1.5,                          ycell*2.5,                          ycell*0.5,]
  posshift_x  = [                                  0,                                   0,                                0.5,                                0.5,]
  hits['LAYER']      = np.select(conditions, layer_y,      default=0)
  hits['X_CHSHIFT']  = np.select(conditions, chanshift_x,  default=0)
  hits['X_POSSHIFT'] = np.select(conditions, posshift_x,   default=0)
  hits['Y_POS']      = np.select(conditions, pos_y,        default=0)

  # define time within the orbit (in bx) : BX + TDC/30
  hits['TIME'] = hits['BX_COUNTER'] + hits['TDC_MEAS']/30.
  # print hits.head()

  allhits=pd.read_csv("/mnt/rammo/output_unpacked_1024_w0_newfw_newlib.txt")
  #print allhits.head()
  allhits=allhits[allhits.HEAD == 1]
  allhits = allhits[(allhits['TDC_CHANNEL'] != 139)]
  np.seterr(divide='ignore', invalid='ignore')
  hist, edges = np.histogram(allhits.TDC_CHANNEL, density=False, bins=range(0,140))
  hist_orb, edges_orb = np.histogram(allhits.ORBIT_CNT, density=False, bins=range(0,5000))
  hist_bx, edges_bx = np.histogram(allhits.BX_COUNTER, density=False, bins=range(0,4000))
  hist_tdc, edges_tdc = np.histogram(allhits.TDC_MEAS, density=False, bins=range(0,150))

  # print hits.TDC_CHANNEL
  new_data = dict(tdc_channel=hits.TDC_CHANNEL,
                  # tdc_count=hits.TDC_MEAS,
                  # bx=hits.BX,
                  # orbit=hits.ORBIT,
                  layer=hits.LAYER,
                  fpga=hits.FPGA,
                  channel_shifted=hits.TDC_CHANNEL+hits.X_CHSHIFT,
                  layer_shifted=(hits.FPGA-1)*4+(hits.LAYER),
                  )

  new_data_hist = dict(thehist=hist,
                  theleftedges=edges[:-1],
                  therightedges=edges[1:]
                  )

  new_data_hist_orb = dict(thehist=hist_orb,
                  theleftedges=edges_orb[:-1],
                  therightedges=edges_orb[1:]
                  )

  new_data_hist_bx = dict(thehist=hist_bx,
                  theleftedges=edges_bx[:-1],
                  therightedges=edges_bx[1:]
                  )

  new_data_hist_tdc = dict(thehist=hist_tdc,
                  theleftedges=edges_tdc[:-1],
                  therightedges=edges_tdc[1:]
                  )


  source.stream(new_data)
  source_hits.stream(new_data_hist)
  source_hits_orb.stream(new_data_hist_orb)
  source_hits_bx.stream(new_data_hist_bx)
  source_hits_tdc.stream(new_data_hist_tdc)


#### POPULATE FIGURE WITH HISTOGRAM
#hist, edges = np.histogram(pd.TDC_MEAS, density=True, bins=50)
#p = figure(title="Normal Distribution ($mu$=0, $sigma$=0.5)")
#p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], line_color=None)

### DEFINE FIGURE OUTPUT
# output_file("test.html")

### SHOW OUTPUT IN BROWSER
# show(p)

curdoc().add_root(gridplot([p,p_hits,None],[p_hits_orb, p_hits_bx, p_hits_tdc]))
#curdoc().add_root(column([p,p_hits]))
curdoc().add_periodic_callback(update_data, 100)

