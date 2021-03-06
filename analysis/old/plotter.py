#!/usr/bin/env python
import json
from kafka import KafkaConsumer
import math
import numpy as np
import pandas as pd
import itertools

from bokeh.io import curdoc, reset_output
from bokeh.layouts import row, gridplot
from bokeh.client import push_session
from bokeh.document import Document
from bokeh.models import ColumnDataSource

from packages.plots import *
from packages.config import *
from packages.patterns import *

### UPDATE TIME --- MATCHING THE SPARK CONSUMER ###
READ_TIME  = 1.000 # sec.
USE_AUTOTRIG = True

def occupancy(message):
        zipped = dict(zip(message.value['TDC_CHANNEL'], message.value['COUNT']))
        thecolors = {}
        for theSL in range(NSL):
            thecolors[theSL]=[]
            thedict = {k: zipped[k] for k in zipped.keys() if k in range(NCHANNELS*theSL+1, NCHANNELS*(theSL+1)+1)}
            maxcount = float(max(thedict.values())) if len(thedict)>0 else 0
            for c in range(1, NCHANNELS+1):
                cur_c = c+(NCHANNELS*theSL)
                cval = 0.
                if cur_c in zipped:
                   cval = zipped[cur_c]/maxcount if maxcount>0 else zipped[cur_c]
                thecolors[theSL].append("#%02x%02x%02x" % (int(255*(1-cval)), int(255*(1-cval)), int(255*(1-cval))) if cval>0 else '#ffffff')
        chan_ds.data.update(**dict(thex=zipped.keys(), they=[x/READ_TIME for x in zipped.values()]))
        occ_ds.data.update (**dict(occchan=CHANNELS, occlay=LAYERS, somecolors_0=thecolors[0], somecolors_1=thecolors[1]))

def meantimer(message):
            allhits = pd.DataFrame(message.value)
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
	    allhits['LAYER']      	= np.select(conditions, layer_z,      default=0).astype(np.uint8)
	    allhits['X_CHSHIFT']  	= np.select(conditions, chanshift_x,  default=0).astype(np.int8)
	    allhits['X_POSSHIFT'] 	= np.select(conditions, posshift_x,   default=0).astype(np.float16)
	    allhits['Z_POS']      	= np.select(conditions, pos_z,        default=0).astype(np.float16)
	    allhits['SL'] 	  	= np.select(conditions_SL, [0, 1, 2, 3], default=-1).astype(np.int8)
            allhits['TDC_CHANNEL_NORM'] = (allhits['TDC_CHANNEL'] - NCHANNELS * (allhits['SL']%2)).astype(np.uint8)
            allhits['TIME0'] 		= -1
            allhits['TIME_ABS'] 	= (allhits['ORBIT_CNT'].astype(np.float64)*DURATION['orbit'] +
                                   	   allhits['BX_COUNTER'].astype(np.float64)*DURATION['bx']   +
	                                   allhits['TDC_MEANS'].astype(np.float64)*DURATION['tdc']).astype(np.float64)

	    # group events by checking on orbit counter
            events = allhits.groupby('ORBIT_CNT')
	    for event, df in events:
              if USE_AUTOTRIG:
	        timezero = df.loc[df['TDC_CHANNEL']==139,'TIME_ABS'].values[0]
		allhits.loc[allhits['ORBIT_CNT']==event,'TIME0'] = timezero
  	      else:
                df = df.loc[(df['TDC_CHANNEL']!=139)]
	        tzerodiff = []
	        tzeromult = []

	    # Selecting only hits that are from events with TIME0 properly estimated
            idx = allhits['TIME0'] > 0
	    # correct hits time for tzero
	    allhits.loc[idx, 'TIMENS'] = allhits['TIME_ABS'] - allhits['TIME0']
	    # assign hits position (left/right wrt wire)






	    # correct hits time by tzero
	    allhits['TIMENS'] 	   = allhits['TIME_ABS'] -allhits['TIME0']    
	    allhits['X_POS_LEFT']  = ((allhits['TDC_CHANNEL_NORM']-0.5).floordiv(4) + allhits['X_POSSHIFT'])*XCELL + XCELL/2 - np.maximum(allhits['TIMENS'], 0)*VDRIFT
	    allhits['X_POS_RIGHT'] = ((allhits['TDC_CHANNEL_NORM']-0.5).floordiv(4) + allhits['X_POSSHIFT'])*XCELL + XCELL/2 + np.maximum(allhits['TIMENS'], 0)*VDRIFT

            # drop all trigger hits 
	    allhits = allhits.loc[(allhits['TDC_CHANNEL']!=139)]

            # push data 
            timens_h, timens_e = np.histogram(allhits.TIMENS, density=False, bins=100, range=(-1000,1000))
            posx_h, posx_e = np.histogram(allhits.TIMENS*VDRIFT, density=False, bins=140, range=(-5,30))

            tmb_ds.data.update (**dict(timens_hist=timens_h,timens_ledge=timens_e[:-1],timens_redge=timens_e[1:]))
            posx_ds.data.update(**dict(posx_hist=posx_h,posx_redge=posx_e[:-1],posx_ledge=posx_e[1:]))
            posg_ds.data.update(**dict(xpos_r=allhits['X_POS_RIGHT'].tolist(), xpos_l=allhits['X_POS_LEFT'].tolist(), zpos=allhits['Z_POS'].tolist()))


def update(consumer):
    # consume all messages from Kafka
    print consumer.topics()
    print consumer.subscription()
    for message in consumer:
        if message.topic == 'occupancyPlot': occupancy(message)
        if message.topic == 'eventsDataframe': meantimer(message)
        continue
        zipped = dict(zip(message.value['TDC_CHANNEL'], message.value['COUNT']))
        thecolors = {}
        for theSL in range(NSL):
            thecolors[theSL]=[]
            thedict = {k: zipped[k] for k in zipped.keys() if k in range(NCHANNELS*theSL+1, NCHANNELS*(theSL+1)+1)}
            maxcount = float(max(thedict.values())) if len(thedict)>0 else 0
            for c in range(1, NCHANNELS+1):
                cur_c = c+(NCHANNELS*theSL)
                cval = 0.
                if cur_c in zipped:
                   cval = zipped[cur_c]/maxcount if maxcount>0 else zipped[cur_c]
                thecolors[theSL].append("#%02x%02x%02x" % (int(255*(1-cval)), int(255*(1-cval)), int(255*(1-cval))) if cval>0 else '#ffffff')
        chan_ds.data.update(**dict(thex=zipped.keys(), they=[x/READ_TIME for x in zipped.values()]))
        occ_ds.data.update (**dict(occchan=CHANNELS, occlay=LAYERS, somecolors_0=thecolors[0], somecolors_1=thecolors[1]))
        tmb_ds.data.update (**dict(timens_hist=[],timens_ledge=[],timens_redge=[]))
        posx_ds.data.update(**dict(posx_hist=[],posx_ledge=[],posx_redge=[]))
        posg_ds.data.update(**dict(xpos_r=[], xpos_l=[], zpos=[]))

### KAFKA CONSUMER ###
consumer = KafkaConsumer(bootstrap_servers='10.64.22.40:9092,10.64.22.41:9092,10.64.22.42:9092',
                           auto_offset_reset='latest',
                           enable_auto_commit=False,
                           value_deserializer=lambda m: json.loads(m.decode('ascii')))

consumer.subscribe(['occupancyPlot','eventsDataframe'])

### DEFINE AND UPDATE DOCUMENT ###
doc = Document()
doc.add_root(tabs)
session = push_session(document=doc,session_id='daq')
### UNCOMMENT TO OPEN THE WEBPAGE AUTOMATICALLY ###
# session.show()
doc.add_periodic_callback(update(consumer), READ_TIME)


