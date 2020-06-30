#!/usr/bin/env python
import json
from kafka import KafkaConsumer
import math
import numpy as np
import pandas as pd
import itertools
import random

from multiprocessing import Pool

from bokeh.io import curdoc, reset_output
from bokeh.layouts import row, gridplot, widgetbox
from bokeh.client import push_session
from bokeh.document import Document
from bokeh.models import ColumnDataSource, HoverTool, CrosshairTool

from packages.plots import *
from packages.config import *
from packages.patterns import *

import argparse
parser = argparse.ArgumentParser(description='Online analysis of unpacked data.')
parser.add_argument('-i', '--internal_trig', action='store_true', default=False, dest='USE_INTTRIG', help='Use bit 139 to estimate tzero')
parser.add_argument('-r', '--read_time',     action='store',      default=8.0,   dest='READ_TIME',   type=float, help='Time window corresponding to the spark batch')
args = parser.parse_args()

### UPDATE TIME --- MATCHING THE SPARK CONSUMER ###
READ_TIME  = args.READ_TIME
USE_INTTRIG = args.USE_INTTRIG

def meantimer_results(df_hits, verbose=False):
    """Run meantimer over the group of hits"""
    sl = df_hits['SL'].iloc[0]
    # Getting a TIME column as a Series with TDC_CHANNEL_NORM as index
    df_time = df_hits.loc[:, ['TDC_CHANNEL_NORM', 'TIME_ABS', 'LAYER']]
    df_time.sort_values('TIME_ABS', inplace=True)
    # Split hits in groups where time difference is larger than maximum event duration
    grp = df_time['TIME_ABS'].diff().fillna(0)
    event_width_max = 1.1*TDRIFT
    grp[grp <= event_width_max] = 0
    grp[grp > 0] = 1
    grp = grp.cumsum().astype(np.uint16)
    df_time['grp'] = grp
    # Removing groups with less than 3 unique hits
    df_time = df_time[df_time.groupby('grp')['TDC_CHANNEL_NORM'].transform('nunique') >= 3]
    # Determining the TIME0 using triplets [no external trigger]
    tzeros = []
    angles = []
    # Processing each group of hits
    patterns = PATTERN_NAMES.keys()
    for grp, df_grp in df_time.groupby('grp'):
        df_grp.set_index('TDC_CHANNEL_NORM', inplace=True)
        # Selecting only triplets present among physically meaningful hit patterns
        channels = set(df_grp.index.astype(np.int16))
        triplets = set(itertools.permutations(channels, 3))
        triplets = triplets.intersection(patterns)
        # Grouping hits by the channel for quick triplet retrieval
        times = df_grp.groupby(df_grp.index)['TIME_ABS']
        # Analysing each triplet
        for triplet in triplets:
            triplet_times = [times.get_group(ch).values for ch in triplet]
            for t1 in triplet_times[0]:
                for t2 in triplet_times[1]:
                    for t3 in triplet_times[2]:
                        timetriplet = (t1, t2, t3)
                        if max(timetriplet) - min(timetriplet) > 1.1*TDRIFT:
                            continue
                        pattern = PATTERN_NAMES[triplet]
                        mean_time, angle = meantimereq(pattern, timetriplet)
                        if verbose:
                            print('{4:d} {0:s}: {1:.0f}  {2:+.2f}  {3}'.format(pattern, mean_time, angle, triplet, sl))
                        if not MEANTIMER_ANGLES[sl][0] < angle < MEANTIMER_ANGLES[sl][1]:
                            continue
                        tzeros.append(mean_time)
                        angles.append(angle)

    return tzeros, angles

def occupancy(message):
        #print message.value
        allhits = pd.DataFrame(message.value)
        thecolors = {}
        zipped = {}

        for theVIRTEX in range(NVIRTEX):
            zipped[theVIRTEX] = dict(zip(allhits[allhits.FPGA==theVIRTEX].TDC_CHANNEL, allhits[allhits.FPGA==theVIRTEX].COUNT))
	    chan_ds[theVIRTEX].data.update(**dict(thex=zipped[theVIRTEX].keys(), they=[x/READ_TIME for x in zipped[theVIRTEX].values()]))

        for theSL in range(NSL):
            thecolors[theSL]=[]
            theVIRTEX = 0 if theSL<2 else 1
            zipped[theSL] = dict(zip(allhits[(allhits.FPGA==theVIRTEX) & (allhits.TDC_CHANNEL>NCHANNELS*(theSL%2)) & (allhits.TDC_CHANNEL<=NCHANNELS*(theSL%2+1))].TDC_CHANNEL, 
			             allhits[(allhits.FPGA==theVIRTEX) & (allhits.TDC_CHANNEL>NCHANNELS*(theSL%2)) & (allhits.TDC_CHANNEL<=NCHANNELS*(theSL%2+1))].COUNT))

            maxcount = float(max(zipped[theSL].values())) if len(zipped[theSL])>0 else 0
            for c in range(1, NCHANNELS+1):
                real_c = c+NCHANNELS if theSL%2 else c
                cval = 0.
                if real_c in zipped[theSL]:
                   cval = zipped[theSL][real_c]/maxcount if maxcount>0 else zipped[theSL][real_c]
                thecolors[theSL].append("#%02x%02x%02x" % (int(255*(1-cval)), int(255*(1-cval)), int(255*(1-cval))) if cval>0 else '#ffffff')
	    occ_ds[theSL].data.update (**dict(occchan=CHANNELS, occlay=LAYERS, somecolors=thecolors[theSL]))
  
def meantimer(message):
      #print message.value
      allhits = pd.DataFrame(message.value)
      #print allhits.head(10)
      conditions  = [
      (allhits['TDC_CHANNEL'] % 4 == 1 ),
      (allhits['TDC_CHANNEL'] % 4 == 2 ),
      (allhits['TDC_CHANNEL'] % 4 == 3 ),
      (allhits['TDC_CHANNEL'] % 4 == 0 ),
      ]
      conditions_SL = [
          ((allhits['FPGA'] == 0) & (allhits['TDC_CHANNEL'] <= NCHANNELS )),
          ((allhits['FPGA'] == 0) & (allhits['TDC_CHANNEL'] > NCHANNELS ) & (allhits['TDC_CHANNEL'] <= 2*NCHANNELS )),
          ((allhits['FPGA'] == 1) & (allhits['TDC_CHANNEL'] <= NCHANNELS )),
          ((allhits['FPGA'] == 1) & (allhits['TDC_CHANNEL'] > NCHANNELS ) & (allhits['TDC_CHANNEL'] <= 2*NCHANNELS )),
      ]
      layer_z     = [  1,            3,            2,            4,         ]
      chanshift_x = [  0,            -1,           0,            -1,        ]
      pos_z       = [  ZCELL*3.5,    ZCELL*1.5,    ZCELL*2.5,    ZCELL*0.5, ]
      posshift_x  = [  0,            0,            0.5,          0.5,       ]

      # Adding columns
      allhits['LAYER']        = np.select(conditions, layer_z,      default=0).astype(np.uint8)
      allhits['X_CHSHIFT']    = np.select(conditions, chanshift_x,  default=0).astype(np.int8)
      allhits['X_POSSHIFT']   = np.select(conditions, posshift_x,   default=0).astype(np.float16)
      allhits['Z_POS']        = np.select(conditions, pos_z,        default=0).astype(np.float16)
      allhits['SL']           = np.select(conditions_SL, [0, 1, 2, 3], default=-1).astype(np.int8)
      allhits['TDC_CHANNEL_NORM'] = (allhits['TDC_CHANNEL'] - NCHANNELS * (allhits['SL']%2)).astype(np.uint8)
      allhits['TIME0']        = -1
      allhits['TIME_ABS']     = (allhits['ORBIT_CNT'].astype(np.float64)*DURATION['orbit'] +
                                 allhits['BX_COUNTER'].astype(np.float64)*DURATION['bx']   +
                                 allhits['TDC_MEANS'].astype(np.float64)*DURATION['tdc']).astype(np.float64)

      # group events by checking on orbit counter
      events = allhits.groupby('ORBIT_CNT')
      for event, df in events:       
        # Remove dataframes with only trigger hit
        if df.shape[0] < 4: 
          continue
        if USE_INTTRIG:
          timezero = df.loc[df['TDC_CHANNEL']==139,'TIME_ABS'].values[0] - 14.5*DURATION['bx']
          allhits.loc[allhits['ORBIT_CNT']==event,'TIME0'] = timezero 
        else:
          df = df.loc[(df['TDC_CHANNEL']!=139)]
          tzeros = meantimer_results(df.loc[(df['TDC_CHANNEL']!=139)])[0] 
          if len(tzeros) > 0:
            allhits.loc[allhits['ORBIT_CNT']==event,'TIME0'] = np.mean(tzeros)


      # Selecting only hits that are from events with TIME0 properly estimated
      idx = allhits['TIME0'] > 0
      # correct hits time for tzero
      allhits.loc[idx, 'TIMENS'] = allhits['TIME_ABS'] - allhits['TIME0'] 
      allhits = allhits.loc[(allhits['TDC_CHANNEL']!=139)]
      allhits = allhits.loc[allhits['TIMENS'].between(TIME_WINDOW[0], TIME_WINDOW[1], inclusive=False)]

      # assign hits position (left/right wrt wire)
      allhits['X_POS_LEFT']  = ((allhits['TDC_CHANNEL_NORM']-0.5).floordiv(4) + allhits['X_POSSHIFT'])*XCELL + XCELL/2 - np.maximum(allhits['TIMENS'], 0)*VDRIFT
      allhits['X_POS_RIGHT'] = ((allhits['TDC_CHANNEL_NORM']-0.5).floordiv(4) + allhits['X_POSSHIFT'])*XCELL + XCELL/2 + np.maximum(allhits['TIMENS'], 0)*VDRIFT

      #allhits.to_csv('boh.txt')
      #print 'saved'

      # drop all trigger hits 
      allhits = allhits.loc[(allhits['TDC_CHANNEL']!=139)]

      for theSL in range(NSL):
        # push data 
        timens_h, timens_e = np.histogram(allhits[allhits.SL==theSL].TIMENS, density=False, bins=100, range=(-200,800))
        posx_h, posx_e = np.histogram(allhits[allhits.SL==theSL].TIMENS*VDRIFT, density=False, bins=70, range=(-5,30))
        tdcc_h, tdcc_e = np.histogram(allhits[allhits.SL==theSL].TDC_CHANNEL_NORM, density=False, bins=NCHANNELS, range=(1,NCHANNELS+1))

        tmb_ds[theSL].data.update (**dict(timens_hist=timens_h,timens_ledge=timens_e[:-1],timens_redge=timens_e[1:]))
        posx_ds[theSL].data.update(**dict(posx_hist=posx_h,posx_redge=posx_e[:-1],posx_ledge=posx_e[1:]))
        posg_ds[theSL].data.update(**dict(xpos_r=allhits[allhits.SL==theSL]['X_POS_RIGHT'].tolist(), xpos_l=allhits[allhits.SL==theSL]['X_POS_LEFT'].tolist(), zpos=allhits[allhits.SL==theSL]['Z_POS'].tolist()))
	tdcc_ds[theSL].data.update(**dict(hist=tdcc_h,ledge=tdcc_e[:-1],redge=tdcc_e[1:]))

def update(consumer):
    # consume all messages from Kafka
    print 'subscribed topics:', consumer.subscription()
    print ""
    print ""
    for message in consumer:
        if message.topic == 'occupancyPlot': 
		occupancy(message)
		print 'occ'
        if message.topic == 'eventsDataframe': 
		meantimer(message)
		print 'df'

### KAFKA CONSUMER ###
consumer = KafkaConsumer(bootstrap_servers='10.64.22.40:9092,10.64.22.41:9092,10.64.22.42:9092',
                           auto_offset_reset='latest',
                           enable_auto_commit=False,
                           value_deserializer=lambda m: json.loads(m.decode('ascii')))

consumer.subscribe(['occupancyPlot','eventsDataframe'])

print ""
print ""
print "Read time            =",READ_TIME,"s"
print "Use internal trigger =",USE_INTTRIG
print ""
print ""

### DEFINE AND UPDATE DOCUMENT ###
doc = curdoc()
doc.add_root(tabs)
session = push_session(document=doc,session_id='daq')#,url='http://10.64.22.10:5006/')
doc.add_periodic_callback(update(consumer), 1.)

