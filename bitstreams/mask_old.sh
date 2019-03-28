#!/bin/sh
vivado_lab -mode batch -source mask_old.tcl -tclargs $1 $2
