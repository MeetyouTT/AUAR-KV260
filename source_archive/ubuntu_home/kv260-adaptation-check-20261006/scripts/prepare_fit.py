#!/usr/bin/env python3
"""Preserve the proven AXI port declarations; insert the capacity-test body."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
old=Path('/home/ghmd/kv260-m3-axilite-20261002/rtl/aura_m3_regs.v')
data=old.read_text()
ports=data[data.index('module aura_m3_regs ('):data.index('    localparam [31:0] IP_ID')]
ports=ports.replace('input wire s_axi_rready\n','input wire s_axi_rready,\n    output wire servo_pwm\n')
body=(ROOT/'fpga/rtl/body.sv.in').read_text()
dest=ROOT/'fpga/rtl/motion_fit.sv'
dest.write_text('// Experimental single-axis capacity ABI; not the formal motion ABI.\n`timescale 1ns/1ps\n'+ports+body)
(ROOT/'fpga/source_manifest.json').write_text(json.dumps({'axi_source':str(old),'axi_source_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'motion_fit_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},indent=2)+'\n')
