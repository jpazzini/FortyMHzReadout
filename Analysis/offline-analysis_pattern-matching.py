from bokeh.io import show, output_file, curdoc
from bokeh.models import ColumnDataSource, BoxAnnotation
from bokeh.plotting import figure
from bokeh.layouts import gridplot, column
from bokeh.transform import jitter
from bokeh.models import formatters
import math
import numpy as np
import pandas as pd
import itertools
import os

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
nchannels = 120   # arbitrary. max numbers of channels to be considered for building patterns
tDrift    = 15.6  # in bx
xcell     = 42.   # cell width in mm
ycell     = 13.   # cell height in mm
vDrift    = xcell*0.5 / (tDrift*25.) # in mm/ns 

# meantime equations
def meantimereq(tkey = '', timelist = []):
  if tkey in ['ABC','BCD']: 
    return [0.25 * (    timelist[0] + 2.*timelist[1] +    timelist[2] - 2*tDrift), math.atan(0.5 * (timelist[2] - timelist[0]) * vDrift / ycell)]
  elif tkey == 'ABD':
    return [0.25 * ( 2.*timelist[0] + 3.*timelist[1] -    timelist[2] - 2*tDrift), math.atan(0.5 * (timelist[1] - timelist[2]) * vDrift / ycell)]
  elif tkey == 'ACD':
    return [0.25 * (   -timelist[0] + 3.*timelist[1] + 2.*timelist[2] - 2*tDrift), math.atan(0.5 * (timelist[2] - timelist[0]) * vDrift / ycell)]
  return None
pass 


# cell patterns for triplet matching
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






import argparse

parser = argparse.ArgumentParser(description='Offline analysis of unpacked data. t0 id performed based on pattern matching.')
parser.add_argument('-i', '--input',  help='the unpacked input file to analyze')
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
### DATA INGESTION (AND ENHANCEMENT)
# pandas dataframe from csv file
allhits=pd.read_csv(args.input,nrows=args.number,skiprows=range(1,args.skip))



# retain all words with HEAD=1
allhits=allhits[allhits.HEAD == 1]


# append columns depending on the TDC_CHANNEL value
#
# conditions  = TDC_CHANNEL % 4
# X_CHSHIFT  <- chanshift_x = channel shift in X with respect to TDC_CHANNEL, used to plot occupancy
# LAYER      <- layer_y     = layer
# Y_POS      <- pos_y       = geometrical wire position in y (assuming 13mm wire-to-wire distance)
# X_POSSHIFT <- posshift_x  = shift in x position (0.5 = half a cell to the right) to correct for staggering (assuming 42mm wire-to-wire distance)
conditions  = [ (allhits['TDC_CHANNEL'] % 4 == 1 ),  (allhits['TDC_CHANNEL'] % 4 == 2 ), (allhits['TDC_CHANNEL'] % 4 == 3 ), (allhits['TDC_CHANNEL'] % 4 == 0 ),]
chanshift_x = [                                  0,                                  -1,                                  0,                                 -1,]
layer_y     = [                                  1,                                   3,                                  2,                                  4,]
pos_y       = [                          ycell*3.5,                           ycell*1.5,                          ycell*2.5,                          ycell*0.5,]
posshift_x  = [                                  0,                                   0,                                0.5,                                0.5,]
allhits['LAYER']      = np.select(conditions, layer_y,      default=0)
allhits['X_CHSHIFT']  = np.select(conditions, chanshift_x,  default=0)
allhits['X_POSSHIFT'] = np.select(conditions, posshift_x,   default=0)
allhits['Y_POS']      = np.select(conditions, pos_y,        default=0)

# define time within the orbit (in bx) : BX + TDC/30
allhits['TIME'] = allhits['BX_COUNTER'] + allhits['TDC_MEAS']/30.


#############################################
### DATA HANDLING 

# create empty dataframe for storing cleaned hits only
dfhits = pd.DataFrame(columns=allhits.dtypes.index)

tzerodiff = []
tzeromult = []
hitperorbit = []
hitperorbitclean = []

if VERBOSE:
  print ''
  print 'dataframe size                   :', allhits['HEAD'].count()
  print ''

# remove the trigger words
allhits = allhits[(allhits['TDC_CHANNEL'] != 139)]

#allhits = allhits[(allhits['ORBIT_CNT'] == 510869385)]

if VERBOSE:
  print 'dataframe size (no trigger hits) :', allhits['HEAD'].count()
  print ''
  print 'sanity checks'
  print ''
  print 'min values in dataframe'
  print allhits[['TDC_CHANNEL','TDC_MEAS','BX_COUNTER','ORBIT_CNT']].min()
  print ''
  print 'max values in dataframe'
  print allhits[['TDC_CHANNEL','TDC_MEAS','BX_COUNTER','ORBIT_CNT']].max()
  print ''

# loop on orbit
for orbits in allhits.ORBIT_CNT.unique():

  # remove all hits not belonging to this orbit
  df = allhits[allhits.ORBIT_CNT == orbits]

  if VERBOSE > 1:
    print 'analyzing orbit', orbits
    print '# hits =',df['HEAD'].count()

  hitperorbit.append(df.count())

  # retain orbits with only 3 or more hits (kill extreme cases with 50 or more hits to avoid overflow in plots)
  # if len(df.index)!=4: continue
  if len(df.index)<3: continue

  hitperorbitclean.append(df.count())
  
  tzeros = []
  angles = []
  for permut in list(itertools.permutations(df.index,3)):
    chantriplet = df.loc[list(permut)]['TDC_CHANNEL'].tolist()
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
          print '   ', df.loc[list(permut)][['TDC_CHANNEL','BX_COUNTER','TDC_MEAS']]
          print '   ', patt, meantimereq(patt,timetriplet) 
          print ''
        tzeros.append(meantimereq(patt,timetriplet)[0])
        angles.append(meantimereq(patt,timetriplet)[1])

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
  df['X_POS_LEFT']  = ((df['TDC_CHANNEL']-0.5).floordiv(4) + df['X_POSSHIFT'])*xcell + xcell/2 - df.TIMENS*vDrift
  df['X_POS_RIGHT'] = ((df['TDC_CHANNEL']-0.5).floordiv(4) + df['X_POSSHIFT'])*xcell + xcell/2 + df.TIMENS*vDrift

  # add all back to the dataframe of selected hits
  dfhits = dfhits.append(df,ignore_index=True)

print 'done looping over individual orbits'
print 'now plotting...'
print ''


#############################################
### DEFINE BOKEH FIGURE (CANVAS EQUIVALENT)


# cell grid - used for plotting
grid_b = []
grid_t = []
grid_l = []
grid_r = []
for lay in [1,2,3,4]:
  for cell in range(1,21):
    grid_b.append( 4*ycell - lay * ycell )
    grid_t.append( grid_b[-1] + ycell )
    grid_l.append( (cell-1) * xcell)
    grid_r.append( grid_l[-1] + xcell )
    if lay%2 == 0:
      grid_l[-1]  += xcell/2.
      grid_r[-1] += xcell/2.

p_timebox = figure(
  plot_width=600,
  plot_height=400,
  title="time",
  y_axis_label="hits",
  x_axis_label="time (ns)",
  )

p_time0 = figure(
  plot_width=600,
  plot_height=400,
  title="t0",
  y_axis_label="hits",
  x_axis_label="t0 within orbit (bx)",
  )

p_tdcchan = figure(
  plot_width=600,
  plot_height=400,
  title="channel",
  y_axis_label="hits",
  x_axis_label="channel",
  )

p_tdcmeas = figure(
  plot_width=600,
  plot_height=400,
  title="TDC count",
  y_axis_label="hits",
  x_axis_label="TDC count",
  )

p_time0diff = figure(
  plot_width=600,
  plot_height=400,
  title="t0 difference",
  y_axis_label="hits",
  x_axis_label="t0 difference for multiple triplets (bx)",
  )

p_time0mult = figure(
  plot_width=600,
  plot_height=400,
  title="t0 multiplicity",
  y_axis_label="hits",
  x_axis_label="multiplicity of t0 evaluated",
  )

p_hitsperorbit = figure(
  plot_width=600,
  plot_height=400,
  title="hits per orbit",
  y_axis_label="multiplicity",
  x_axis_label="hits per orbit",
  )

p_hitsperorbitclean = figure(
  plot_width=600,
  plot_height=400,
  title="clean hits per orbit",
  y_axis_label="multiplicity",
  x_axis_label="hits per orbit - cleaned",
  )

p_hitsperorbitnumber = figure(
  plot_width=1800,
  plot_height=400,
  title="hits per orbit",
  y_axis_label="hits",
  x_axis_label="orbit",
  output_backend="webgl",
  )
p_hitsperorbitnumber.xaxis[0].formatter = formatters.PrintfTickFormatter(format="%d")


p_orbdiffperorbitnumber = figure(
  plot_width=1800,
  plot_height=400,
  title="orbit difference per orbit",
  y_axis_label="difference wrt previous orbit",
  x_axis_label="orbit",
  output_backend="webgl",
  )
p_orbdiffperorbitnumber.xaxis[0].formatter = formatters.PrintfTickFormatter(format="%d")


p_occ = figure(
  plot_width=600,
  plot_height=400,
  y_range=[4.5,0.5],
  x_range=[-1,81],
  title="occupancy",
  y_axis_label="layer",
  x_axis_label="channel",
  )

p_pos = figure(
  plot_width=1800,
  plot_height=120,
  y_range=[0,60],
  x_range=[0,900],
  title="hit position",
  y_axis_label="y (mm)",
  x_axis_label="x (mm)",
  )

p_hitspositionincell = figure(
  plot_width=600,
  plot_height=400,
  title="hits position",
  y_axis_label="hits",
  x_axis_label="distance from wire (mm)",
  )

p_angle = figure(
  plot_width=600,
  plot_height=400,
  title="angle",
  y_axis_label="hits",
  x_axis_label="angle (rad)",
  )


# # #############################################
# # ### FILL BOKEH FIGURE (CANVAS EQUIVALENT)

histbxns,    edgesbxns    = np.histogram(dfhits.TIMENS,           density=False, bins=100, range=(-200,800))
histt0ns,    edgest0ns    = np.histogram(dfhits.TIME0,            density=False, bins=90,  range=(0,3600))
histchan,    edgeschan    = np.histogram(dfhits.TDC_CHANNEL,      density=False, bins=range(0,85))
histtdc,     edgestdc     = np.histogram(dfhits.TDC_MEAS,         density=False, bins=range(0,32))
histt0diff,  edgest0diff  = np.histogram(tzerodiff,               density=False, bins=150, range=(-5,5))
histt0mult,  edgest0mult  = np.histogram(tzeromult,               density=False, bins=30,  range=(0,30))
histhpo,     edgeshpo     = np.histogram(hitperorbit,             density=False, bins=30,  range=(0,30))
histhpoc,    edgeshpoc    = np.histogram(hitperorbitclean,        density=False, bins=10,  range=(0,10))
histposx,    edgesposx    = np.histogram(dfhits.TIMENS*vDrift,    density=False, bins=140, range=(-5,30))
histangl,    edgesangl    = np.histogram(dfhits.ANGLE,            density=False, bins=100, range=(-0.1,0.1))

p_timebox.quad(top=histbxns,
            bottom=0,
            left=edgesbxns[:-1],
            right=edgesbxns[1:])



p_time0.quad(top=histt0ns,
            bottom=0,
            left=edgest0ns[:-1],
            right=edgest0ns[1:])



p_tdcchan.quad(top=histchan,
            bottom=0,
            left=edgeschan[:-1],
            right=edgeschan[1:])



p_tdcmeas.quad(top=histtdc,
            bottom=0,
            left=edgestdc[:-1],
            right=edgestdc[1:])



p_time0diff.quad(top=histt0diff,
            bottom=0,
            left=edgest0diff[:-1],
            right=edgest0diff[1:])



p_time0mult.quad(top=histt0mult,
            bottom=0,
            left=edgest0mult[:-1],
            right=edgest0mult[1:])



p_hitsperorbit.quad(top=histhpo,
            bottom=0,
            left=edgeshpo[:-1],
            right=edgeshpo[1:])



p_hitsperorbitclean.quad(top=histhpoc,
            bottom=0,
            left=edgeshpoc[:-1],
            right=edgeshpoc[1:])





p_hitsperorbitnumber.square(
            x=(allhits.groupby('ORBIT_CNT', as_index=False).count())['ORBIT_CNT'],
            y=(allhits.groupby('ORBIT_CNT', as_index=False).count())['HEAD'],
            size=5,
            )



p_orbdiffperorbitnumber.square(
            x=allhits['ORBIT_CNT'].tolist(),
            y=allhits['ORBIT_CNT'].diff().tolist(),
            size=5,
            )


p_hitspositionincell.quad(top=histposx,
            bottom=0,
            left=edgesposx[:-1],
            right=edgesposx[1:])


p_angle.quad(top=histangl,
            bottom=0,
            left=edgesangl[:-1],
            right=edgesangl[1:])


p_occ.scatter(x=dfhits.TDC_CHANNEL+dfhits.X_CHSHIFT,
          y=(dfhits.FPGA-1)*4+(dfhits.LAYER),
# p_occ.scatter(x=allhits.TDC_CHANNEL+allhits.X_CHSHIFT,
#           y=(allhits.FPGA-1)*4+(allhits.LAYER),
          # alpha=0.1,
          marker='square',
          size=20,
          line_color='navy',
          fill_color='navy',
         )


p_pos.quad(top=grid_t, 
          bottom=grid_b, 
          left=grid_l,
          right=grid_r, 
          fill_color='white',
          line_color='black',
          )
p_pos.scatter(x=dfhits.X_POS_RIGHT,
          y=dfhits.Y_POS,
          # alpha=0.1,
          marker='square',
          size=2,
         )
p_pos.scatter(x=dfhits.X_POS_LEFT,
          y=dfhits.Y_POS,
          # alpha=0.1,
          marker='square',
          size=2,
         )



colors = ["red", "green", "yellow"]
for iorbit in dfhits.ORBIT_CNT.unique()[-3:]:
  q = dfhits[(dfhits['ORBIT_CNT'] == iorbit)]
  p_occ.scatter(x=q.TDC_CHANNEL+q.X_CHSHIFT,
            y=(q.FPGA-1)*4+(q.LAYER),
            # alpha=0.1,
            marker='square',
            size=20,
            line_color=colors[0],
            fill_color=colors[0],
           )
  p_pos.scatter(x=q.X_POS_LEFT,
            y=q.Y_POS,
            # alpha=0.1,
            marker='square',
            line_color=colors[0],
            fill_color=colors[0],
            size=5,
           )
  
  minresidual = 9e9
  bestfit     = None
  for iii in range(0,len(q['X_POS_LEFT'].tolist())/2+1):
    xpos = q['X_POS_LEFT'].tolist()[iii:]+q['X_POS_RIGHT'].tolist()[:iii]
    ypos = q['Y_POS'].tolist()[iii:]+q['Y_POS'].tolist()[:iii]
    regression, residuals, _, _, _ = np.polyfit(ypos, xpos, 1, full=True)
    if residuals<minresidual:
      bestfit = regression
    if VERBOSE > 1:
      print q[['TDC_CHANNEL','TIMENS','X_POS_LEFT','X_POS_RIGHT','Y_POS', 'ANGLE']]
      print 'x = {}*y + {}'.format(regression[0],regression[1])
  xlow  = bestfit[1]
  xhigh = xlow + bestfit[0] * ycell*4

  p_pos.scatter(x=q.X_POS_RIGHT,
            y=q.Y_POS,
            # alpha=0.1,
            marker='square',
            line_color=colors[0],
            fill_color=colors[0],
            size=5,
           )
  # p_pos.line([xlow, xhigh], 
  #            [0., ycell*4],
  #            color=colors[0], 
  #            # alpha=0.5, 
  #            line_width=4,
  #            )
  # p_pos.line([xlow, xhigh], 
  #            [0., ycell*4],
  #            color=colors[0], 
  #            # alpha=0.5, 
  #            line_width=4,
  #            )

  colors.pop(0)


### DEFINE FIGURE OUTPUT
output_file("plots_pattern.html")

## SHOW OUTPUT IN BROWSER
show(gridplot([p_timebox,             p_occ,                p_time0diff             ],
              [p_tdcchan,             p_tdcmeas,            p_time0                 ],
              [p_time0mult,           p_hitsperorbit,       p_hitsperorbitclean     ],
              [p_hitspositionincell,  p_angle,              None                    ],
              [p_hitsperorbitnumber                                                 ],
              [p_orbdiffperorbitnumber                                              ],
              [p_pos                                                                ],
              ))
# show(gridplot([p_hitsperorbitnumber                                                 ],
#               [p_orbdiffperorbitnumber                                              ],
#               ))

print 'all done'
print ''



