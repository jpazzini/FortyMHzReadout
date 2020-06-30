#!/bin/sh
vivado_lab -mode batch -source mask.tcl -tclargs $1 $2
