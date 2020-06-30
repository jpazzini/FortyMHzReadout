#!/bin/sh
vivado_lab -mode batch -source event_i_mask.tcl -tclargs $1 $2
