#!/usr/bin/env python
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.transform import cumsum
from bokeh.models.widgets import Panel, Tabs
from bokeh.layouts import row, column, gridplot
from config import *

### PLOTS ###
# hits per channel
chan_ds = {}
p_chan = {}
for theVIRTEX in range(NVIRTEX):
  chan_ds[theVIRTEX] = ColumnDataSource(dict(thex=[],they=[]))
  p_chan[theVIRTEX] = figure(plot_width=600,
                plot_height=400,
                title="Hit rate per channel - V7 {}".format(theVIRTEX),
                x_axis_label="Channel",
                y_axis_label="Rate [Hz]")
  p_chan[theVIRTEX].vbar(x='thex',
            top='they',
            width=0.9,
            bottom=0,
            source=chan_ds[theVIRTEX])
t_chan = Panel(child=row(p_chan[0],p_chan[1]), title='Hit rate')


# occupancy
occ_ds = {}
occ_tt = {}
p_occ = {}
for theSL in range(NSL):
  occ_ds[theSL] = ColumnDataSource(dict(occchan=[],occlay=[],somecolors=[],rates=[]))
  occ_tt[theSL] = [
    ("rate [Hz]", "@rates"),
  ]
  p_occ[theSL] = figure(plot_width=600,
                 plot_height=400,
                 y_range=[4.5,0.5],
                 x_range=[-1,NCHANNELS+1],
                 title="Occupancy - Chamber {}".format(theSL),
                 y_axis_label="Layer",
                 x_axis_label="Channel",
	         tooltips=occ_tt[theSL])
  p_occ[theSL].scatter(x='occchan',
                y='occlay',
                fill_color='somecolors',
                marker='square',
                size=14,
                line_color='black',
                source=occ_ds[theSL])
t_occ  = Panel(child=gridplot([[p_occ[0],p_occ[1]],[p_occ[2],p_occ[3]]]), title='Occupancy')

# timebox
tmb_ds  = {}
p_timebox = {}
for theSL in range(NSL):
  tmb_ds[theSL] = ColumnDataSource(dict(timens_hist=[],timens_ledge=[],timens_redge=[]))
  p_timebox[theSL] = figure(plot_width=600,
                   plot_height=400,
                   title="Timebox - Chamber {}".format(theSL),
                   x_axis_label="Time [ns]",
                   y_axis_label="Hits")
  p_timebox[theSL].quad(top='timens_hist',
               bottom=0,
               left='timens_ledge',
               right='timens_redge',
               source=tmb_ds[theSL])       
t_tmb  = Panel(child=gridplot([[p_timebox[0],p_timebox[1]],[p_timebox[2],p_timebox[3]]]), title='Timebox')

# posx
posx_ds  = {}
p_posx = {}
for theSL in range(NSL):
  posx_ds[theSL] = ColumnDataSource(dict(posx_hist=[],posx_ledge=[],posx_redge=[]))
  p_posx[theSL] = figure(plot_width=600,
                   plot_height=400,
                   title="Local hit position - Chamber {}".format(theSL),
                   x_axis_label="Distance from wire [mm]",
                   y_axis_label="Hits")
  p_posx[theSL].quad(top='posx_hist',
               bottom=0,
               left='posx_ledge',
               right='posx_redge',
               source=posx_ds[theSL])
t_posx  = Panel(child=gridplot([[p_posx[0],p_posx[1]],[p_posx[2],p_posx[3]]]), title='Corrected x position')

# tdcc
tdcc_ds  = {}
p_tdcc = {}
for theSL in range(NSL):
  tdcc_ds[theSL] = ColumnDataSource(dict(hist=[],ledge=[],redge=[]))
  p_tdcc[theSL] = figure(plot_width=600,
                   plot_height=400,
                   title="Active channels - Chamber {}".format(theSL),
                   x_axis_label="Channel",
                   y_axis_label="Hits")
  p_tdcc[theSL].quad(top='hist',
               bottom=0,
               left='ledge',
               right='redge',
               source=tdcc_ds[theSL])
t_tdcc  = Panel(child=gridplot([[p_tdcc[0],p_tdcc[1]],[p_tdcc[2],p_tdcc[3]]]), title='Active channels')

# posg
posg_ds = {}
posg_last_ds = {}
p_posg = {}
for theSL in range(NSL):
  posg_ds[theSL] = ColumnDataSource(dict(xpos_l=[],xpos_r=[],zpos=[]))
  posg_last_ds[theSL] = ColumnDataSource(dict(xpos_l_last=[],xpos_r_last=[],zpos_last=[]))
  p_posg[theSL] = figure(plot_width=1800,
               plot_height=120,
               y_range=[0,60],
               x_range=[-XCELL/2,XCELL*(NCHANNELS/4+1)],
               title="Hit position - Chamber {}".format(theSL),
               y_axis_label="y (mm)",
               x_axis_label="x (mm)",
	       toolbar_location="above")
  p_posg[theSL].quad(top=grid_t,
           bottom=grid_b,
           left=grid_l,
           right=grid_r, 
           fill_color='white',
           line_color='black')
  p_posg[theSL].scatter(x='xpos_r',
              y='zpos',
              marker='square',
              size=2,
              source=posg_ds[theSL])
  p_posg[theSL].scatter(x='xpos_l',
              y='zpos',
              marker='square',
              size=2,
              source=posg_ds[theSL])
  p_posg[theSL].scatter(x='xpos_r_last',
              y='zpos_last',
              marker='square',
              size=4,
              color='red',
              source=posg_last_ds[theSL])
  p_posg[theSL].scatter(x='xpos_l_last',
              y='zpos_last',
              marker='square',
              size=4,
	      color='red',
              source=posg_last_ds[theSL])
t_posg  = Panel(child=column(p_posg[0],p_posg[1],p_posg[2],p_posg[3]), title='Hits in geometry')


### WEBPAGE TABS ###
# tabs = Tabs(tabs=[t_chan,t_occ,t_tmb,t_posg])
tabs = Tabs(tabs=[t_chan,t_occ,t_tmb,t_posx,t_tdcc,t_posg])
