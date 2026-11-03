#!/usr/bin/env python3
"""Rebuild metadata/DT overlay and export a same-run, checked bit/XSA into an offline firmware tree."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from bitstream_pairing import check_pairing

ROOT=Path(__file__).resolve().parents[1]
APP='aura-visual-servo-b4096-wide-v1'
BASE_SHA='22516e08c2c862dfe3ee999a962ff62ed7830ad8e1183e36432cd22acde77762'
SECTIONS=ROOT/'src/fpga/xrt_metadata'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read_json(path):
    return json.loads(path.read_bytes())
def json_out(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def executable(name,explicit):
    found=explicit or shutil.which(name)
    if not found:raise ValueError('Missing '+name+'; set its command-line option or PATH')
    return str(Path(found).resolve())

def fdt(raw):
    if len(raw)<40:raise ValueError('Truncated FDT')
    magic,total,off,strings,_,_,_,_,ssz,dsz=struct.unpack_from('>10I',raw,0)
    if magic!=0xd00dfeed or total>len(raw) or max(off+dsz,strings+ssz)>total:raise ValueError('Invalid FDT header')
    end=off+dsz;stack=[];nodes={}
    while off+4<=end:
        tag,=struct.unpack_from('>I',raw,off);off+=4
        if tag==1:
            nul=raw.index(b'\0',off,end);stack.append(raw[off:nul].decode());off=(nul+4)&~3
            path='/'.join(stack) or '/';nodes[path]={}
        elif tag==2:
            if not stack:raise ValueError('Invalid FDT nesting')
            stack.pop()
        elif tag==3:
            length,idx=struct.unpack_from('>II',raw,off);off+=8
            if not stack or idx>=ssz or off+length>end:raise ValueError('Invalid FDT property')
            key=raw[strings+idx:raw.index(b'\0',strings+idx,strings+ssz)].decode()
            nodes['/'.join(stack) or '/'][key]=raw[off:off+length];off=(off+length+3)&~3
        elif tag==4:continue
        elif tag==9:
            if stack:raise ValueError('Unbalanced FDT')
            return nodes
        else:raise ValueError('Invalid FDT token '+str(tag))
    raise ValueError('Missing FDT end')
def string(raw):return raw.rstrip(b'\0').decode()
def number(raw):
    if len(raw)!=4:raise ValueError('Expected one FDT cell')
    return struct.unpack('>I',raw)[0]
def interfaces(hwh):
    root=ET.fromstring(hwh); expected=read_json(ROOT/'src/fpga/bd/address_map.json')['interfaces']
    actual={}
    for name,contract in expected.items():
        matches=[m for m in root.iter('MODULE') if m.get('INSTANCE')==name]
        if len(matches)!=1:raise ValueError('Missing or duplicate module '+name)
        mod=matches[0]
        actual[name]={'vlnv':mod.get('VLNV'),'clocks_hz':{x.get('NAME'):int(x.get('CLKFREQUENCY')) for x in mod.findall('PORTS/PORT') if x.get('CLKFREQUENCY')},
                      'addresses':[[int(x.get('BASEVALUE'),0),int(x.get('HIGHVALUE'),0)] for x in root.iter('MEMRANGE') if x.get('INSTANCE')==name],
                      'parameters':{x.get('NAME'):int(x.get('VALUE'),0) for x in mod.findall('PARAMETERS/PARAMETER') if x.get('NAME') in contract['parameters']}}
        if actual[name]!=contract:raise ValueError('Hardware interface differs for '+name+': '+str(actual[name]))
    return actual

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--metadata-only',action='store_true')
    p.add_argument('--bit',type=Path);p.add_argument('--xsa',type=Path)
    p.add_argument('--base-dtb',type=Path,help='Optional actual target base FDT, checked against the documented digest')
    p.add_argument('--xclbin',type=Path,help='Optional exact frozen reference instead of rebuilding eight sections')
    for name in ['dtc','fdtoverlay','xclbinutil','bootgen']:p.add_argument('--'+name)
    a=p.parse_args()
    if not a.metadata_only and not (a.bit and a.xsa):p.error('--bit and --xsa required for full export')
    out=a.out.resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('Choose a fresh external output directory')
    out.mkdir(parents=True,exist_ok=False)
    logs=out/'logs';logs.mkdir()
    payload=out/APP;payload.mkdir()
    commands=[]
    def run(label,cmd):
        log=logs/(label+'.log')
        with log.open('xb') as f:r=subprocess.run([str(c) for c in cmd],cwd=out,stdout=f,stderr=subprocess.STDOUT)
        commands.append({'label':label,'argv':[str(c) for c in cmd],'exit_code':r.returncode,'log_sha256':sha(log)})
        json_out(out/'commands.json',commands)
        if r.returncode:raise RuntimeError(label+' failed; see '+str(log))
        return log.read_text(errors='replace')
    dtc=executable('dtc',a.dtc);merge=executable('fdtoverlay',a.fdtoverlay);xrt=executable('xclbinutil',a.xclbinutil)
    overlay=payload/(APP+'.dtbo')
    run('compile_overlay',[dtc,'-I','dts','-O','dtb','-o',overlay,ROOT/'src/fpga/overlay/aura-visual-servo.dtsi'])
    base=a.base_dtb
    if base:
        base=base.resolve()
        if sha(base)!=BASE_SHA:raise ValueError('Unexpected reference target base DTB digest')
    else:
        base=out/'validation-base.dtb'
        run('compile_base_fixture',[dtc,'-I','dts','-O','dtb','-o',base,ROOT/'board/system/validation_base.dts'])
    merged=out/'merged.dtb';run('merge_target_tree',[merge,'-i',base,'-o',merged,overlay])
    tree=fdt(merged.read_bytes());symbols=tree['/__symbols__']
    fpga=tree[string(symbols['fpga_full'])]
    if string(fpga['firmware-name'])!=APP+'.bit.bin' or 'fpga-config-from-dmabuf' not in fpga:raise ValueError('Merged FPGA firmware contract differs')
    clocks={n:number(tree[string(symbols[n])]['assigned-clock-rates']) for n in ['clocking0','clocking1']}
    if any(v!=0x5f5dd19 for v in clocks.values()):raise ValueError('Merged fabric clock differs')
    zocl=tree[string(symbols['zocl'])]
    if b'zocl' not in zocl['compatible'] or number(zocl['interrupt-parent']) in (0,0xffffffff):raise ValueError('Merged ZOCL is not bound to its interrupt parent')
    for sym in ['zynqmp_dpsub','zynqmp_dp_snd_pcm0','zynqmp_dp_snd_pcm1','zynqmp_dp_snd_card0','zynqmp_dp_snd_codec0']:
        if string(tree[string(symbols[sym])]['status'])!='okay':raise ValueError('Missing enabled target '+sym)
    spec=read_json(SECTIONS/'sections.json')
    xc=payload/(APP+'.xclbin')
    if a.xclbin:
        if sha(a.xclbin)!=spec['reference_xclbin_sha256']:raise ValueError('Incorrect frozen XCLBIN')
        shutil.copyfile(str(a.xclbin),str(xc))
    else:
        cmd=[xrt,'--target','hw','--key-value','SYS:PlatformVBNV:'+spec['vbnv']]
        for name,s in spec['sections'].items():
            src=SECTIONS/s['file']
            if sha(src)!=s['sha256']:raise ValueError('XRT input changed: '+name)
            cmd+=['--add-section',name+':'+s['format']+':'+str(src)]
        run('rebuild_xclbin',cmd+['--output',xc])
    info=run('inspect_xclbin',[xrt,'--input',xc,'--info'])
    if spec['vbnv'] not in info or 'DPUCZDX8G' not in info:raise ValueError('XRT platform/CU mismatch')
    uuid=re.search(r'UUID \(xclbin\):\s*([a-fA-F0-9-]+)',info)
    if not uuid:raise ValueError('Missing XCLBIN UUID')
    dump=out/'xrt_readback';dump.mkdir()
    for name,s in spec['sections'].items():
        dest=dump/s['file'];run('read_'+name,[xrt,'--input',xc,'--dump-section',name+':'+s['format']+':'+str(dest)])
        expected=SECTIONS/s['file']
        if a.xclbin and name in ('BUILD_METADATA','SYSTEM_METADATA'):
            if sha(dest)!=s['source_sha256']:raise ValueError('Original metadata changed: '+name)
        elif name=='EMBEDDED_METADATA':
            if dest.read_bytes()!=expected.read_bytes():raise ValueError('Embedded kernel XML differs')
        elif read_json(dest)!=read_json(expected):raise ValueError('Rebuilt XRT section differs: '+name)
    shutil.copyfile(str(ROOT/'src/fpga/overlay/shell.json'),str(payload/'shell.json'))
    details={'mode':'metadata-only' if a.metadata_only else 'full-export','board_verified':False,'base_dtb_sha256':sha(base),
             'base_kind':'actual_saved_target' if a.base_dtb else 'sanitized_topology_fixture','merged_dtb_sha256':sha(merged),'firmware_name':string(fpga['firmware-name']),
             'merged_clocks_hz':clocks,'xclbin_route':'fixed' if a.xclbin else 'rebuilt_eight_sections','xclbin_uuid':uuid.group(1),'sections_checked':list(spec['sections'])}
    if not a.metadata_only:
        bootgen=executable('bootgen',a.bootgen)
        with zipfile.ZipFile(a.xsa) as z:
            bits=[n for n in z.namelist() if n.endswith('.bit')]
            hw=[n for n in z.namelist() if n.rsplit('/',1)[-1]=='kv260_ispMipiRx_vcu_DP.hwh']
            if len(bits)!=1 or len(hw)!=1:raise ValueError('Expected one bitstream and one design HWH')
            bit=z.read(bits[0]);details['hwh_interfaces']=interfaces(z.read(hw[0]))
        details['bit_xsa_pairing']=check_pairing(a.bit.read_bytes(),bit)
        (out/'visual_servo_paired.bit').write_bytes(bit)
        bif=out/'full_pl.bif';bif.write_text('all:\n{\n [destination_device=pl] visual_servo_paired.bit\n}\n')
        run('bootgen',[bootgen,'-arch','zynqmp','-image',bif,'-o',payload/(APP+'.bit.bin')])
        details.update({'xsa_sha256':sha(a.xsa),'bit_sha256':sha(a.bit)})
    details['payload_sha256']={q.name:sha(q) for q in sorted(payload.iterdir()) if q.is_file()}
    details['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    details['status']='PASS'
    json_out(out/'firmware_result.json',details)
    print('PASS',details['mode'],len(spec['sections']),'XRT sections, merged DT, output',out)
if __name__=='__main__':main()

