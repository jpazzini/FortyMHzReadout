#!/usr/bin/env python
import json
from kafka import KafkaConsumer
import numpy as np
from bokeh.io import curdoc, reset_output
from bokeh.layouts import row, gridplot
from bokeh.client import push_session
from bokeh.document import Document
from bokeh.models import ColumnDataSource
from packages.plots import *
from packages.config import *

### UPDATE TIME --- MATCHING THE SPARK CONSUMER ###
READ_TIME  = 0.700 # sec.

### UPDATE LOGIC ###
def update(consumer):
    # consume all messages from Kafka
    for message in consumer:
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
consumer.subscribe(['occupancyPlot'])

### DEFINE AND UPDATE DOCUMENT ###
doc = Document()
doc.add_root(tabs)
session = push_session(document=doc,session_id='daq')
### UNCOMMENT TO OPEN THE WEBPAGE AUTOMATICALLY ###
# session.show()
doc.add_periodic_callback(update(consumer), READ_TIME)


