#!/usr/bin/env python3
"""Retire unused PL I2S, preserving control-bus completion and VCU interconnect."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=Path('/home/ghmd/kv260-m3-axilite-20261002/src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj/prj.gen/sources_1/bd/kv260_ispMipiRx_vcu_DP/synth/kv260_ispMipiRx_vcu_DP.v')
s=source.read_text(); start=s.index('module audio_ss_0_imp_'); end=s.index('\nendmodule',start)
parser=argparse.ArgumentParser()
parser.add_argument('--alias-map',type=Path)
parser.add_argument('--output',type=Path)
args=parser.parse_args()
aliases=[]
if args.alias_map:
    for line in args.alias_map.read_text().splitlines():
        alias,expression,parity=line.split('\t')
        assert re.fullmatch(r'[\w\[\]]+',alias)
        assert re.fullmatch(r'[\w\[\]]+',expression)
        assert parity in ['0','1']
        aliases.append((alias,expression,int(parity)))
chunk=s[start:end]
ports=re.findall(r'^  (input|output)\s*(\[[^\]]+\])?\s*(\w+);',chunk,re.M)
assert len(ports)>100
lines=['// Experimental USB-audio capacity profile. Legacy PL audio returns DECERR.',
       'module aura_disabled_audio ('+', '.join([p[2] for p in ports]+['\\'+a+' ' for a,_,_ in aliases])+');']
lines += [f'    {direction} wire {width} {name};' for direction,width,name in ports]
for alias,expression,parity in aliases:
    lines.append('    output wire \\'+alias+' ;')
    lines.append('    assign \\'+alias+' = '+('~' if parity else '')+expression+';')
prefixes=['s_axi_ctrl_i2s_rx','s_axi_ctrl_i2s_tx','s_axi_lite_audio_fmt']
for prefix in prefixes:
    lines.append('    aura_audio_decerr '+prefix+'_stub(.clk(ACLK),.resetn(ARESETN),')
    signals=['awvalid','awready','wvalid','wready','bvalid','bready','bresp','arvalid','arready','rvalid','rready','rresp','rdata']
    lines.append('        '+', '.join('.'+sig+'('+prefix+'_'+sig+')' for sig in signals)+');')
for direction,width,name in ports:
    if direction=='output' and not any(name.startswith(p+'_') for p in prefixes):
        lines.append(f"    assign {name} = '0;")
lines.append('endmodule\n')
lines.append((ROOT/'fpga/rtl/audio_decerr.sv').read_text())
target=(args.output or (ROOT/'fpga/rtl/disabled_audio.sv')).resolve()
assert ROOT in target.parents
target.write_text('\n'.join(lines))
(ROOT/'fpga/audio_ports.tcl').write_text('set audio_port_names [list '+' '.join(p[2] for p in ports)+']\n')
manifest={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'disabled_audio_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
          'ports':len(ports),'alias_outputs':len(aliases),'profile':'USB_AUDIO_NO_PL_I2S','vcu_interconnect_preserved':True}
manifest_path=target.parent/'audio_source_manifest.json'
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
