"""CELL PATTERNS FOR MEANTIMER PATTERN MATCHING
patterns  =  dictionary of patterns (list of triplets of hits time in bx relative to orbit: BX + TDC/30), arranged by key being a string identifier used to select the proper mean-timing eq to be solved 
"""

import math
import numpy as np
import pandas as pd
from config import NCHANNELS, TDRIFT, VDRIFT, ZCELL, MEANTIMER_CLUSTER_SIZE, MEANTIMER_SL_MULT_MIN


############################################# MEANTIMER EQUATIONS
def meantimereq(pattern, timelist):
    """Function returning the expected t0 out of hits triples. None by default 
    tkey is the identifier of the univoque equation to be used given the pattern of hits in the triplet
    timelist is a len=3 list of hits time
    """
    patt = pattern[:-1]
    if patt in ('ABC','BCD'): 
        tzero = 0.25 * ( timelist[0] + 2*timelist[1] + timelist[2] - 2*TDRIFT)
        angle = math.atan(0.5 * (timelist[0] - timelist[2]) * VDRIFT / ZCELL)
    elif patt == 'ABD':
        tzero = 0.25 * ( 3*timelist[1] + 2*timelist[0] - timelist[2] - 2*TDRIFT)
        angle = math.atan(0.5 * (timelist[2] - timelist[1]) * VDRIFT / ZCELL)
    elif patt == 'ACD':
        tzero = 0.25 * ( 3*timelist[1] + 2*timelist[2] - timelist[0] - 2*TDRIFT)
        angle = math.atan(0.5 * (timelist[0] - timelist[1]) * VDRIFT / ZCELL)
    else:
        return None
    # Inverting angle if this is a left-side pattern
    if pattern[-1] == 'l':
        angle *= -1
    return tzero, angle



############################################# POSSIBLE HIT PATTERNS
PATTERNS = {}
### 3 ABC RIGHT
PATTERNS['ABCr']  = [ (1+x, 3+x,  2+x) for x in range(0, NCHANNELS, 4) ]
#A |1   x    |5   o    |9   o    |
#B     |3   x    |7   o    |
#C |2   x    |6   o    |10  o    |
#D     |4   o    |8   o    |
### 3 ABC LEFT
PATTERNS['ABCl'] = [ (5+x, 3+x,  6+x) for x in range(0, NCHANNELS, 4)[:-1] ]
#A |1   o    |5   x    |9   o    |
#B     |3   x    |7   o    |
#C |2   o    |6   x    |10  o    |
#D     |4   o    |8   o    |

### 3 BCD RIGHT
PATTERNS['BCDr']  = [ (3+x, 6+x,  4+x) for x in range(0, NCHANNELS, 4)[:-1] ]
#A |1   o    |5   o    |9   o    |
#B     |3   x    |7   o    |
#C |2   o    |6   x    |10  o    |
#D     |4   x    |8   o    |
### 3 BCD LEFT
PATTERNS['BCDl'] = [ (3+x, 2+x,  4+x) for x in range(0, NCHANNELS, 4) ]
#A |1   o    |5   o    |9   o    |
#B     |3   x    |7   o    |
#C |2   x    |6   o    |10  o    |
#D     |4   x    |8   o    |

### 3 ACD RIGHT
PATTERNS['ACDr']  = [ (1+x, 2+x,  4+x) for x in range(0, NCHANNELS, 4) ]
#A |1   x    |5   o    |9   o    |
#B     |3   o    |7   o    |
#C |2   x    |6   o    |10  o    |
#D     |4   x    |8   o    |
### 3 ACD LEFT
PATTERNS['ACDl'] = [ (5+x, 6+x,  4+x) for x in range(0, NCHANNELS, 4)[:-1] ]
#A |1   o    |5   x    |9   o    |
#B     |3   o    |7   o    |
#C |2   o    |6   x    |10  o    |
#D     |4   x    |8   o    |

### 3 ABD RIGHT
PATTERNS['ABDr']  = [ (1+x, 3+x,  4+x) for x in range(0, NCHANNELS, 4) ]
#A |1   x    |5   o    |9   o    |
#B     |3   x    |7   o    |
#C |2   o    |6   o    |10  o    |
#D     |4   x    |8   o    |
### 3 ABD LEFT
PATTERNS['ABDl'] = [ (5+x, 3+x,  4+x) for x in range(0, NCHANNELS, 4)[:-1] ]
#A |1   o    |5   x    |9   o    |
#B     |3   x    |7   o    |
#C |2   o    |6   o    |10  o    |
#D     |4   x    |8   o    |


PATTERN_NAMES = {}
for name, patterns in PATTERNS.items():
    for pattern in patterns:
        PATTERN_NAMES[pattern] = name


