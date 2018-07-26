from bokeh.io import show, output_file, curdoc
from bokeh.models import ColumnDataSource, BoxAnnotation
from bokeh.plotting import figure
from bokeh.layouts import gridplot, column
from bokeh.transform import jitter
from bokeh.models import formatters
import threading
import multiprocessing
import math
import numpy as np
import pandas as pd
import itertools
import os 

#                         / z-axis (beam direction)
#                        .
#                       .
#                  ///////////|   
#                 ///////////||
#                ||||||||||||||
#                ||||||||||||||  SL 1/3
#                ||||||||||||/
#                |||||||||||/
#  y-axis       .          .
#(vertical     .          .
# pointing    .          .
# upward)    .          .
#   ^       .          .           y-axis
#   |   ///////////|  .            ^ 
#   |  ///////////|| .             |  z-axis 
#   | ||||||||||||||.              | / 
#   | ||||||||||||||  SL 0/2       |/
#   | ||||||||||||/                +-------> x-axis 
#   | |||||||||||/                 
#   +-------------> x-axis (horizontal)


#    layer #             cell numbering scheme
#      1         |    1    |    5    |    9    |
#      2              |    3    |    7    |   11    |
#      3         |    2    |    6    |   10    |
#      4              |    4    |    8    |   12    |


#############################################
### DEFINITIONS
###
### nchannels = max n. channels to be considered to evaluate triplet patterns
### tDrift    = drift time assumed in the computation of mean-timer equations (in bx)
### meantime  -> function returning the expected t0 out of hits triples. None by default
###             timelist is a len=3 list of hits time (in bx, relative to orbit: BX + TDC/30) 
###             key is the identifier of the univoque equation to be used given the pattern of hits in the triplet
### patterns  =  dictionary of patterns (list of triples of hits time in bx relative to orbit: BX + TDC/30), arranged by key being a string identifier used to select the proper mean-timing eq to be solved 
VERBOSE   = 1     # set verbosity level
nchannels = 64    # numbers of channels per chamber (one FPGA maps 2 chanbers --> 128 channels per FPGA --> 2SLs)
xcell     = 42.   # cell width in mm
zcell     = 13.   # cell height in mm
zchamb    = 550.  # spacing betweeen chambers in mm
tDrift    = 15.6  # drift time in bx
vDrift    = xcell*0.5 / (tDrift*25.) # drift velocity in mm/ns 

#############################################
### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)

def map(chan):
  mod = chan%4
  if mod == 1:
    return chan, 1
  elif mod == 2:
    return chan, 3
  elif mod == 3:
    return chan+0.5, 2
  else: # mod == 0:
    return chan+0.5, 4
  
# cell grid - used for plotting
grid_b = []
grid_t = []
grid_l = []
grid_r = []
for lay in [1,2,3,4]:
  for cell in range(1,nchannels/4+1):
    grid_b.append( 4*zcell - lay * zcell )
    grid_t.append( grid_b[-1] + zcell )
    grid_l.append( (cell-1) * xcell)
    grid_r.append( grid_l[-1] + xcell )
    if lay%2 == 0:
      grid_l[-1]  += xcell/2.
      grid_r[-1] += xcell/2.

p_timebox_SL = {} # timebox
p_time0_SL = {} # t0
p_tdcchan_SL = {} # channel
p_tdcrate_SL = {} # channel
p_tdcmeas_SL = {} # tdc count
p_time0diff_SL = {} # difference between t0s 
p_time0mult_SL = {} # t0 multiplicity
p_hitsperorbit_SL = {} # nHits per orbit vs orbit number
p_hitsperorbitclean_SL = {} # nHits per orbit vs orbit number post-cleanup
p_hitsperorbitnumber_SL = {} # nHits per orbit vs orbit number
p_orbdiffperorbitnumber_SL = {} # hits orbit difference vs orbit number
p_occ_SL = {} # occupancy
p_pos_SL = {} # hit position in chamber
p_hitspositionincell_SL = {} # hit position in cell
p_angle_SL = {} # hit angle 

for SL in range(0,4):
  p_timebox_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="time - SL%d" % SL,
    y_axis_label="hits",
    x_axis_label="time (ns)",
    )

  p_time0_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="t0 - SL%d" % SL,
    y_axis_label="hits",
    x_axis_label="t0 within orbit (bx)",
    )

  p_tdcchan_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="channel - SL%d" % SL,
    y_axis_label="hits",
    x_axis_label="channel",
    )

  p_tdcrate_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="rate per channel - SL%d" % SL,
    y_axis_label="hits/s",
    x_axis_label="channel",
    )

  p_tdcmeas_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="TDC count - SL%d" % SL,
    y_axis_label="hits",
    x_axis_label="TDC count",
    )

  p_time0diff_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="t0 difference - SL%d" % SL,
    y_axis_label="hits",
    x_axis_label="t0 difference for multiple triplets (bx)",
    )

  p_time0mult_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="t0 multiplicity - SL%d" % SL,
    y_axis_label="hits",
    x_axis_label="multiplicity of t0 evaluated",
    )

  p_hitsperorbit_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="hits per orbit - SL%d" % SL,
    y_axis_label="multiplicity",
    x_axis_label="hits per orbit",
    )

  p_hitsperorbitclean_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="clean hits per orbit - SL%d" % SL,
    y_axis_label="multiplicity",
    x_axis_label="hits per orbit - cleaned",
    )

  p_hitsperorbitnumber_SL[SL] = figure(
    plot_width=900,
    plot_height=300,
    title="hits per orbit - SL%d" % SL,
    y_axis_label="hits",
    x_axis_label="orbit",
    output_backend="webgl",
    )
  p_hitsperorbitnumber_SL[SL].xaxis[0].formatter = formatters.PrintfTickFormatter(format="%d")

  p_orbdiffperorbitnumber_SL[SL] = figure(
    plot_width=900,
    plot_height=300,
    title="orbit difference per orbit - SL%d" % SL,
    y_axis_label="difference wrt previous orbit",
    x_axis_label="orbit",
    output_backend="webgl",
    )
  p_orbdiffperorbitnumber_SL[SL].xaxis[0].formatter = formatters.PrintfTickFormatter(format="%d")

  p_occ_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    y_range=[4.5,0.5],
    x_range=[-1,nchannels+1],
    title="occupancy - SL%d" % SL,
    y_axis_label="layer",
    x_axis_label="channel",
    )

  p_pos_SL[SL] = figure(
    plot_width=1800,
    plot_height=120,
    y_range=[0,60],
    x_range=[-xcell/2,xcell*(nchannels/4+1)],
    title="hit position - SL%d" % SL,
    y_axis_label="y (mm)",
    x_axis_label="x (mm)",
    )

  p_hitspositionincell_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="hits position - SL%d" % SL,
    y_axis_label="hits",
    x_axis_label="distance from wire (mm)",
    )

  p_angle_SL[SL] = figure(
    plot_width=450,
    plot_height=300,
    title="angle - SL%d" % SL,
    y_axis_label="hits",
    x_axis_label="angle (rad)",
    )


#############################################
### ANALYSIS
def thisfunction(SL_, allhits_):
  allhits_SL = allhits_[allhits_['SL']==SL_]
  dfhits = pd.DataFrame(columns=allhits_SL.dtypes.index)
  dfhits['TIME0'] = None
  dfhits['TIMENS'] = None
  dfhits['ANGLE'] = None
  dfhits['X_POS_LEFT'] = None
  dfhits['X_POS_RIGHT'] = None

  tzerodiff = []
  tzeromult = []
  hitperorbit = []
  hitperorbitclean = []

  # loop on orbit
  for orbits in allhits_SL.ORBIT_CNT.unique():

    # remove all hits not belonging to this orbit
    df = allhits_SL[allhits_SL.ORBIT_CNT == orbits]

    if VERBOSE > 1:
      print 'analyzing orbit', orbits
      print '# hits =',df['HEAD'].count()

    hitperorbit.append(df.count())

    # retain orbits with only 3 or more hits
    #if len(df.index)!=4: continue ### bkp for quadruplets
    if len(df.index)<3: continue

    hitperorbitclean.append(df.count())
    
    tzeros = []
    angles = []
    for permut in list(itertools.permutations(df.index,3)):
      chantriplet = df.loc[list(permut)]['TDC_CHANNEL_NORM'].tolist()
      timetriplet = df.loc[list(permut)]['TIME'].tolist()
      timediffs   = [ abs(x-y) for x,y in itertools.combinations(timetriplet,2) ]
      if VERBOSE > 1:
        print 'found triplet'
        print '   channels: ', chantriplet
        print '   times   : ', timetriplet
        print '   time difference between hits:', timediffs    
      if any(itime > tDrift for itime in timediffs): continue
      for patt in patterns:
        if chantriplet in patterns[patt]:
          if VERBOSE > 1:
            print '--> matching pattern'
            print '   ', df.loc[list(permut)][['TDC_CHANNEL_NORM','BX_COUNTER','TDC_MEAS']]
            print '   ', patt, meantimereq(patt,timetriplet) 
            print ''
          tzeros.append(meantimereq(patt,timetriplet)[0])
          angles.append(meantimereq(patt,timetriplet)[1])
      pass
    pass

    tzeromult.append(len(tzeros))

    # if more than 1 pattern is found, compare them
    #   if all within 1bx               -> assign the mean of them to tzero
    #   if any differ by more than 1bx  -> use min tzero
    tzero = -9e9 
    angle = -9e9 
    if len(tzeros)>0:
      tzero = min(tzeros)
      relativediffs = [ x-y for x,y in itertools.combinations(tzeros,2) ]
      tzerodiff += relativediffs
      if all(abs(i) < 0.1 for i in relativediffs):
        tzero = np.mean(tzeros)
        angle = np.mean(angles)

    # remove all orbits with no triplets in it 
    if tzero<0: continue

    # assign tzero
    df = df.assign(TIME0=tzero)

    # correct hits time for tzero and convert it to nx (assuming 1 BX = 25 ns)
    df['TIMENS']=(df['TIME']-df['TIME0'])*25
    df['ANGLE']=angle
    # assign hits position (left/right wrt wire)
    df['X_POS_LEFT']  = ((df['TDC_CHANNEL_NORM']-0.5).floordiv(4) + df['X_POSSHIFT'])*xcell + xcell/2 - df.TIMENS*vDrift
    df['X_POS_RIGHT'] = ((df['TDC_CHANNEL_NORM']-0.5).floordiv(4) + df['X_POSSHIFT'])*xcell + xcell/2 + df.TIMENS*vDrift

    # add all back to the dataframe of selected hits
    dfhits = dfhits.append(df,ignore_index=True)

    dfhits_out = dfhits[['SL','LAYER','WIRE_NUM','TDC_CHANNEL_NORM','TIMENS','TIME0','X_POS_LEFT','X_POS_RIGHT','Z_POS']]

    dfhits_out.to_csv('out_df_%d.csv'%SL_)

  pass
 
  if dfhits['HEAD'].count() == 0:
      print 'INFO --- No triplet found in this range'
      dfhits.fillna(method='ffill')
 
  # now plot

  deltat = float(allhits_SL['ORBIT_CNT'].max() - allhits_SL['ORBIT_CNT'].min()) * 25. * 3564. 

  print 'Delta-t =', deltat, 'ns'
  
  histbxns,    edgesbxns    = np.histogram(dfhits.TIMENS,           density=False, bins=100, range=(-200,800))
  histt0ns,    edgest0ns    = np.histogram(dfhits.TIME0,            density=False, bins=90,  range=(0,3600))
  histchan,    edgeschan    = np.histogram(allhits_SL.TDC_CHANNEL_NORM, density=False, bins=range(0,nchannels+2))
  histrate = [x / (deltat * 10**-9) for x in histchan]
  edgesrate = edgeschan 
  
  occchan = [map(c)[0] for c in range(0, nchannels+2)]
  occlay  = [map(c)[1] for c in range(0, nchannels+2)]
  occ     = []
  for c in range(0, nchannels+2):
      occ.append(allhits_SL['TDC_CHANNEL_NORM'][allhits_SL['TDC_CHANNEL_NORM']==c].count()/float(max(histchan)))
  
  somecolors = ["#%02x%02x%02x" % (int(255*(1-c)), int(255*(1-c)), int(255*(1-c))) for c in occ]  
  
  histtdc,     edgestdc     = np.histogram(allhits_SL.TDC_MEAS,         density=False, bins=range(0,32))
  histt0diff,  edgest0diff  = np.histogram(tzerodiff,               density=False, bins=150, range=(-5,5))
  histt0mult,  edgest0mult  = np.histogram(tzeromult,               density=False, bins=30,  range=(0,30))
  histhpo,     edgeshpo     = np.histogram(hitperorbit,             density=False, bins=30,  range=(0,30))
  histhpoc,    edgeshpoc    = np.histogram(hitperorbitclean,        density=False, bins=10,  range=(0,10))
  histposx,    edgesposx    = np.histogram(dfhits.TIMENS*vDrift,    density=False, bins=140, range=(-5,30))
  histangl,    edgesangl    = np.histogram(dfhits.ANGLE,            density=False, bins=100, range=(-0.1,0.1))
  '''
  histbxns,    edgesbxns    = np.histogram(allhits_SL.TDC_CHANNEL_NORM,           density=False, bins=100, range=(-200,800))
  histt0ns,    edgest0ns    = np.histogram(allhits_SL.TDC_CHANNEL_NORM,            density=False, bins=90,  range=(0,3600))
  histchan,    edgeschan    = np.histogram(allhits_SL.TDC_CHANNEL_NORM, density=False, bins=range(0,nchannels+2))
  histtdc,     edgestdc     = np.histogram(allhits_SL.TDC_MEAS,         density=False, bins=range(0,32))
  histt0diff,  edgest0diff  = np.histogram(tzerodiff,               density=False, bins=150, range=(-5,5))
  histt0mult,  edgest0mult  = np.histogram(tzeromult,               density=False, bins=30,  range=(0,30))
  histhpo,     edgeshpo     = np.histogram(hitperorbit,             density=False, bins=30,  range=(0,30))
  histhpoc,    edgeshpoc    = np.histogram(hitperorbitclean,        density=False, bins=10,  range=(0,10))
  histposx,    edgesposx    = np.histogram(allhits_SL.TDC_CHANNEL_NORM,    density=False, bins=140, range=(-5,30))
  histangl,    edgesangl    = np.histogram(allhits_SL.TDC_CHANNEL_NORM,            density=False, bins=100, range=(-0.1,0.1))
  '''

  p_timebox_SL[SL_].quad(top=histbxns,
              bottom=0,
              left=edgesbxns[:-1],
              right=edgesbxns[1:])

  p_time0_SL[SL_].quad(top=histt0ns,
              bottom=0,
              left=edgest0ns[:-1],
              right=edgest0ns[1:])

  p_tdcchan_SL[SL_].quad(top=histchan,
              bottom=0,
              left=edgeschan[:-1],
              right=edgeschan[1:])

  p_tdcrate_SL[SL_].quad(top=histrate,
              bottom=0,
              left=edgesrate[:-1],
              right=edgesrate[1:])

  p_tdcmeas_SL[SL_].quad(top=histtdc,
              bottom=0,
              left=edgestdc[:-1],
              right=edgestdc[1:])

  p_time0diff_SL[SL_].quad(top=histt0diff,
              bottom=0,
              left=edgest0diff[:-1],
              right=edgest0diff[1:])

  p_time0mult_SL[SL_].quad(top=histt0mult,
              bottom=0,
              left=edgest0mult[:-1],
              right=edgest0mult[1:])

  p_hitsperorbit_SL[SL_].quad(top=histhpo,
              bottom=0,
              left=edgeshpo[:-1],
              right=edgeshpo[1:])

  p_hitsperorbitclean_SL[SL_].quad(top=histhpoc,
              bottom=0,
              left=edgeshpoc[:-1],
              right=edgeshpoc[1:])

  p_hitsperorbitnumber_SL[SL_].square(
              x=(allhits_SL.groupby('ORBIT_CNT', as_index=False).count())['ORBIT_CNT'],
              y=(allhits_SL.groupby('ORBIT_CNT', as_index=False).count())['HEAD'],
              size=5,
              )

  p_orbdiffperorbitnumber_SL[SL_].square(
              x=allhits_SL.ORBIT_CNT.tolist(),
              y=allhits_SL.ORBIT_CNT.diff().tolist(),
              size=5,
              )

  p_hitspositionincell_SL[SL_].quad(top=histposx,
              bottom=0,
              left=edgesposx[:-1],
              right=edgesposx[1:])

  p_angle_SL[SL_].quad(top=histangl,
              bottom=0,
              left=edgesangl[:-1],
              right=edgesangl[1:])
  
  p_occ_SL[SL_].scatter(x=occchan,
            y=occlay,
            fill_color=somecolors,
            marker='square',
            size=12,
            line_color=somecolors,
           )

  p_pos_SL[SL_].quad(top=grid_t, 
            bottom=grid_b, 
            left=grid_l,
            right=grid_r, 
            fill_color='white',
            line_color='black',
            )
  p_pos_SL[SL_].scatter(x=dfhits.X_POS_RIGHT,
            y=dfhits.Z_POS,
            # alpha=0.1,
            marker='square',
            size=2,
           )
  p_pos_SL[SL_].scatter(x=dfhits.X_POS_LEFT,
            y=dfhits.Z_POS,
            # alpha=0.1,
            marker='square',
            size=2,
           )

  colors = ["red", "green", "yellow"]
  for iorbit in dfhits.ORBIT_CNT.unique()[-3:]:
    q = dfhits[(dfhits['ORBIT_CNT'] == iorbit)]
    p_occ_SL[SL_].scatter(x=q.TDC_CHANNEL_NORM+q.X_CHSHIFT,
              y=q.LAYER,
              # alpha=0.1,
              marker='square',
              size=12,
              line_color=colors[0],
              fill_color=colors[0],
             )
    p_pos_SL[SL_].scatter(x=q.X_POS_LEFT,
              y=q.Z_POS,
              # alpha=0.1,
              marker='square',
              line_color=colors[0],
              fill_color=colors[0],
              size=5,
             )
    p_pos_SL[SL_].scatter(x=q.X_POS_RIGHT,
              y=q.Z_POS,
              # alpha=0.1,
              marker='square',
              line_color=colors[0],
              fill_color=colors[0],
              size=5,
             )
    # minresidual = 9e9
    # bestfit     = None
    # for iii in range(0,len(q['X_POS_LEFT'].tolist())/2+1):
    #   xpos = q['X_POS_LEFT'].tolist()[iii:]+q['X_POS_RIGHT'].tolist()[:iii]
    #   ypos = q['Z_POS'].tolist()[iii:]+q['Z_POS'].tolist()[:iii]
    #   regression, residuals, _, _, _ = np.polyfit(ypos, xpos, 1, full=True)
    #   if residuals<minresidual:
    #     bestfit = regression
    #   if VERBOSE > 1:
    #     print q[['TDC_CHANNEL_NORM','TIMENS','X_POS_LEFT','X_POS_RIGHT','Z_POS', 'ANGLE']]
    #     print 'x = {}*y + {}'.format(regression[0],regression[1])
    # xlow  = bestfit[1]
    # xhigh = xlow + bestfit[0] * zcell*4


    # p_pos_SL[SL_].line([xlow, xhigh], 
    #            [0., zcell*4],
    #            color=colors[0], 
    #            # alpha=0.5, 
    #            line_width=4,
    #            )
    # p_pos_SL[SL_].line([xlow, xhigh], 
    #            [0., zcell*4],
    #            color=colors[0], 
    #            # alpha=0.5, 
    #            line_width=4,
    #            )

    colors.pop(0)

  pass

pass


#############################################
### MEANTIMER EQUATIONS
def meantimereq(tkey = '', timelist = []):
  if tkey in ['ABC','BCD']: 
    return [0.25 * (    timelist[0] + 2.*timelist[1] +    timelist[2] - 2*tDrift), math.atan(0.5 * (timelist[2] - timelist[0]) * vDrift / zcell)]
  elif tkey == 'ABD':
    return [0.25 * ( 2.*timelist[0] + 3.*timelist[1] -    timelist[2] - 2*tDrift), math.atan(0.5 * (timelist[1] - timelist[2]) * vDrift / zcell)]
  elif tkey == 'ACD':
    return [0.25 * (   -timelist[0] + 3.*timelist[1] + 2.*timelist[2] - 2*tDrift), math.atan(0.5 * (timelist[2] - timelist[0]) * vDrift / zcell)]
  return None
pass 

#############################################
### CELL PATTERNS FOR MEANTIMER PATTERN MATCHING 
patterns = {}
### 3 ABC RIGHT
patterns['ABC']  = [ [1+x, 3+x,   2+x] for x in range(0,nchannels,4) ]    
#A |1   o    |5   x    |9   o    |
#B     |3   o    |7   x    |
#C |2   o    |6   x    |10  o    |
#D     |4   o    |8   o    |
### 3 ABC LEFT
patterns['ABC'] += [ [1+x, -1+x,  2+x] for x in range(0,nchannels,4) ]
#A |1   o    |5   x    |9   o    |
#B     |3   x    |7   o    |
#C |2   o    |6   x    |10  o    |
#D     |4   o    |8   o    |

### 3 BCD RIGHT
patterns['BCD']  = [ [3+x, 6+x,  4+x] for x in range(0,nchannels,4) ]
#A |1   o    |5   o    |9   o    |
#B     |3   x    |7   o    |
#C |2   o    |6   x    |10  o    |
#D     |4   x    |8   o    |
### 3 BCD LEFT
patterns['BCD'] += [ [3+x, 2+x,  4+x] for x in range(0,nchannels,4) ]
#A |1   o    |5   o    |9   o    |
#B     |3   x    |7   o    |
#C |2   x    |6   o    |10  o    |
#D     |4   x    |8   o    |

### 3 ACD RIGHT
patterns['ACD']  = [ [1+x, 2+x,   4+x] for x in range(0,nchannels,4) ]
#A |1   o    |5   x    |9   o    |
#B     |3   o    |7   o    |
#C |2   o    |6   x    |10  o    |
#D     |4   o    |8   x    |
### 3 ACD LEFT
patterns['ACD'] += [ [1+x, 2+x,   x] for x in range(0,nchannels,4) ]
#A |1   o    |5   x    |9   o    |
#B     |3   o    |7   o    |
#C |2   o    |6   x    |10  o    |
#D     |4   x    |8   o    |

### 3 ABD RIGHT
patterns['ABD'] = [ [1+x, 3+x,   4+x] for x in range(0,nchannels,4) ]
#A |1   o    |5   x    |9   o    |
#B     |3   o    |7   x    |
#C |2   o    |6   o    |10  o    |
#D     |4   o    |8   x    |
### 3 ABD LEFT
patterns['ABD'] += [[1+x, x-1,   x] for x in range(0,nchannels,4) ]
#A |1   o    |5   x    |9   o    |
#B     |3   x    |7   o    |
#C |2   o    |6   o    |10  o    |
#D     |4   x    |8   o    |

#############################################
### INPUT ARGUMENTS 
import argparse
parser = argparse.ArgumentParser(description='Offline analysis of unpacked data. t0 id performed based on pattern matching.')
parser.add_argument('-i', '--input',  help='The unpacked input file to analyze')
parser.add_argument('-n', '--number', action='store', default=10000,  dest='number', type=int, help='Number of hits to analyze')
parser.add_argument('-s', '--skip',   action='store', default=131073, dest='skip',   type=int, help='Number of hits to skip at the top of the file')
args = parser.parse_args()
if not os.path.exists(os.path.expandvars(args.input)):
    print '--- ERROR ---'
    print '  \''+args.input+'\' file not found'
    print '  please point to the correct path to the file containing the unpacked data' 
    print 
    exit()

#############################################
### DATA INGESTION
# pandas dataframe from csv file
allhits=pd.read_csv(args.input,nrows=args.number,skiprows=range(1,args.skip))

# retain all words with HEAD=1
allhits=allhits[allhits.HEAD == 1]

# append columns depending on the TDC_CHANNEL value
#
# conditions  = TDC_CHANNEL % 4
# X_CHSHIFT  <- chanshift_x = channel shift in X with respect to TDC_CHANNEL, used to plot occupancy
# LAYER      <- layer_z     = layer
# Z_POS      <- pos_z       = geometrical wire position in z (assuming 13mm wire-to-wire distance)
# X_POSSHIFT <- posshift_x  = shift in x position (0.5 = half a cell to the right) to correct for staggering (assuming 42mm wire-to-wire distance)
conditions  = [ (allhits['TDC_CHANNEL'] % 4 == 1 ),  (allhits['TDC_CHANNEL'] % 4 == 2 ), (allhits['TDC_CHANNEL'] % 4 == 3 ), (allhits['TDC_CHANNEL'] % 4 == 0 ),]
chanshift_x = [                                  0,                                  -1,                                  0,                                 -1,]
layer_z     = [                                  1,                                   3,                                  2,                                  4,]
pos_z       = [                          zcell*3.5,                           zcell*1.5,                          zcell*2.5,                          zcell*0.5,]
posshift_x  = [                                  0,                                   0,                                0.5,                                0.5,]
allhits['LAYER']      = np.select(conditions, layer_z,      default=0)
allhits['X_CHSHIFT']  = np.select(conditions, chanshift_x,  default=0)
allhits['X_POSSHIFT'] = np.select(conditions, posshift_x,   default=0)
allhits['Z_POS']      = np.select(conditions, pos_z,        default=0)

# conditions  = FPGA number and TDC_CHANNEL in range
# SL         <- superlayer = chamber number from 0 to 3 (0,1 FPGA#0 --- 2,3 FPGA#1)
conditions_SL  = [ ((allhits['FPGA'] == 0) & (allhits['TDC_CHANNEL']<=nchannels )),  ((allhits['FPGA'] == 0) & (allhits['TDC_CHANNEL']>nchannels )), ((allhits['FPGA'] == 1) & (allhits['TDC_CHANNEL']<=nchannels )),  ((allhits['FPGA'] == 1) & (allhits['TDC_CHANNEL']>nchannels )),]
superlayer_SL  = [                                                              0,                                                              1,                                                              2,                                                              3,]
allhits['SL']         = np.select(conditions_SL, superlayer_SL,      default=-1)

# define time within the orbit (in bx) : BX + TDC/30
allhits['TIME'] = allhits['BX_COUNTER'] + allhits['TDC_MEAS']/30.

# define channel within SL
allhits['TDC_CHANNEL_NORM']  = allhits['TDC_CHANNEL']-nchannels*(allhits['SL']%2)
allhits['WIRE_NUM']  = (allhits['TDC_CHANNEL_NORM']-1).floordiv(4) + 1

###print allhits[(allhits['SL']==3) & (allhits['ORBIT_CNT']>400000000)]

#############################################
### DATA HANDLING 

if VERBOSE:
  print ''
  print 'dataframe size                   :', allhits['HEAD'].count()
  print ''

# remove the trigger words from computation
allhits = allhits[(allhits['TDC_CHANNEL'] != 139)]

if VERBOSE:
  print 'dataframe size (no trigger hits) :', allhits['HEAD'].count()
  print ''
  print 'min values in dataframe'
  print allhits[['TDC_CHANNEL','TDC_CHANNEL_NORM','TDC_MEAS','BX_COUNTER','ORBIT_CNT']].min()
  print ''
  print 'max values in dataframe'
  print allhits[['TDC_CHANNEL','TDC_CHANNEL_NORM','TDC_MEAS','BX_COUNTER','ORBIT_CNT']].max()
  print ''
  
jobs = []  

#for SL in range(4):
for SL in range(1):
  p = threading.Thread(target=thisfunction, args=(SL,allhits,))
  jobs.append(p)
  p.start()

for pj in jobs:
  pj.join()


print 'done looping over individual orbits'
print 'now plotting...'
print ''


### DEFINE FIGURE OUTPUT
output_file("offline_plots.html", mode="inline")

## SHOW OUTPUT IN BROWSER
show(gridplot([p_tdcchan_SL[0], p_tdcchan_SL[1], p_tdcchan_SL[2], p_tdcchan_SL[3]],               # channel multiplicity per SL
              [p_tdcrate_SL[0], p_tdcrate_SL[1], p_tdcrate_SL[2], p_tdcrate_SL[3]],               # hit rate per channel per SL in s
              [p_tdcmeas_SL[0], p_tdcmeas_SL[1], p_tdcmeas_SL[2], p_tdcmeas_SL[3]],               # TDC meas multiplicity per SL
              [p_occ_SL[0], p_occ_SL[1], p_occ_SL[2], p_occ_SL[3]],                               # occupancy per SL
              [p_timebox_SL[0], p_timebox_SL[1], p_timebox_SL[2], p_timebox_SL[3]],               # timebox per SL
              [p_time0mult_SL[0], p_time0mult_SL[1], p_time0mult_SL[2], p_time0mult_SL[3]],       # meantimer solution (t0) multiplicity per orbit 
              [p_time0diff_SL[0], p_time0diff_SL[1], p_time0diff_SL[2], p_time0diff_SL[3]],       # difference of meantimer solution (t0) in case of multiple solutions  
              [p_hitsperorbitnumber_SL[0], p_hitsperorbitnumber_SL[1],],
              [p_hitsperorbitnumber_SL[2], p_hitsperorbitnumber_SL[3],],                          # multiplicity of hits per orbit
              [p_orbdiffperorbitnumber_SL[0], p_orbdiffperorbitnumber_SL[1],],
              [p_orbdiffperorbitnumber_SL[2], p_orbdiffperorbitnumber_SL[3],],                    # orbit difference between hits
              [p_pos_SL[0],],
              [p_pos_SL[1],],
              [p_pos_SL[2],],
              [p_pos_SL[3],],                                                                     # hits position

              ),
      browser='firefox')

print 'all done'
print ''



