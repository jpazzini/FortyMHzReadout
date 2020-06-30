#!/bin/sh
vivado_lab -mode batch -source no_event.tcl -tclargs $1 $2
