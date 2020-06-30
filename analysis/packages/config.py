"""Configuration for the analysis"""

import numpy as np

### CHAMBER CONFIGURATION ###
NCHANNELS  = 64    # channels per SL
NSL        = 4     # number of SL
NVIRTEX    = 2     # number of V7

### Virtual (FPGA, TDC_CHANNEL) pairs containing event/trigger information
EVENT_NR_CHANNELS = [(1,138), (1,137), (0,138), (0,137)]
CHANNELS_TRIGGER = [(0, 130), (0, 129), (1, 129)]
CHANNEL_TRIGGER = CHANNELS_TRIGGER[2]
### Cell parameters
XCELL     = 42.                      # cell width in mm
ZCELL     = 13.                      # cell height in mm
ZCHAMB    = 550.                     # spacing betweeen chambers in mm
DURATION = {                         # duration in ns of different periods
    'orbit:bx': 3564,
    'orbit': 3564*25,
    'bx': 25.,
    'tdc': 25./30
}
TDRIFT    = 15.6*DURATION['bx']    # drift time in ns
VDRIFT    = XCELL*0.5 / TDRIFT     # drift velocity in mm/ns 
TRIGGER_TIME_ARRAY = np.array([DURATION['orbit'], DURATION['bx'], DURATION['tdc']])
### Minimum time [bx] between groups of hits with EVENT_NR to be considered as belonging to separate events
EVENT_TIME_GAP = 1000/DURATION['bx']
### Criteria for input hits for meantimer
NHITS_SL = (1, 10)  # (min, max) number of hits in a superlayer to be considered in the event
# MEANTIMER_ANGLES = [(-0.1, -0.02), (-0.1, -0.03), (0.01, 0.07), (0.02, 0.08)]
# MEANTIMER_ANGLES = [(-0.53, 0.53)] * 4
MEANTIMER_ANGLES = [(-0.2, 0.1), (-0.2, 0.1), (-0.1, 0.2), (-0.1, 0.2)]
MEANTIMER_CLUSTER_SIZE = 2  # minimum number of meantimer solutions in a cluster to calculate mean t0
MEANTIMER_SL_MULT_MIN = 2  # minimum number of different SLs in a cluster of meantimer solutions


# Parameters of the DAQ signals [must be optimised according to the exact setup performance]
TIME_OFFSET = [-1045, -1193, -1382]         # synchronization w.r.t trigger (ttrig) - RUN <=293 , RUN >293, RUN >=440
TIME_WINDOW = (-50, 500)             # time window (lower, higher) edge, after synchronization
# TIME_OFFSET_SL = [3, 8, 1, 2]   # original
# TIME_OFFSET_SL = [3, 7, 1, 3]   # Run258
# TIME_OFFSET_SL = [-2, 2, 1, 1]   # Run335/331/353
TIME_OFFSET_SL = [0, 5, 9, 14]   # Run532/529
# TIME_OFFSET_SL = [3, 7, 13, 14]   # Run503
# TIME_OFFSET_SL = [0, 0, 0, 0]   # original
# TIME_OFFSET_SL = [2, 7, 2, 0]

### MAPPING CHANNEL NUMBER - OCCUPANCY ###
def map(chan):
  mod = chan%4
  if mod == 1:    return chan, 1
  elif mod == 2:  return chan-1., 3
  elif mod == 3:  return chan-0., 2
  else:           return chan-1., 4
CHANNELS = [map(c)[0] for c in range(1, NCHANNELS+1)]
LAYERS   = [map(c)[1] for c in range(1, NCHANNELS+1)]

### MAPPING CHANNEL NUMBER - GEOMETRY ###
grid_b = []
grid_t = []
grid_l = []
grid_r = []
for lay in [1,2,3,4]:
    for cell in range(1,NCHANNELS/4+1):
        grid_b.append( 4*ZCELL - lay * ZCELL )
        grid_t.append( grid_b[-1] + ZCELL )
        grid_l.append( (cell-1) * XCELL)
        grid_r.append( grid_l[-1] + XCELL )
        if lay%2 == 0:
            grid_l[-1]  += XCELL/2.
            grid_r[-1] += XCELL/2.
