#!/usr/bin/env python3
"""Compare existing source-platform handoff with the new offline PWM candidate."""
import datetime
import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
prior = Path('/home/ghmd/kv260-m3-axilite-20261002/src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj')
bd = prior/'prj.srcs/sources_1/bd/kv260_ispMipiRx_vcu_DP/kv260_ispMipiRx_vcu_DP.bd'
hwh = prior/'prj.gen/sources_1/bd/kv260_ispMipiRx_vcu_DP/hw_handoff/kv260_ispMipiRx_vcu_DP.hwh'
dt = Path('/home/ghmd/kv260-m3-axilite-20261002/test_bundle_attempt02/provenance/candidate.decompiled.dts')
merged = dt.parent/'host-merged-system.dtb'
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = root/'evidence'/(stamp+'-metadata-audit');out.mkdir()
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build = json.loads((root/'CURRENT_BUILD.json').read_text())
handoff = ET.parse(hwh).getroot()
ports = [p.get('NAME') for p in handoff.findall('./EXTERNALPORTS/PORT')]
modules = handoff.findall('.//MODULE')
motion = next(m for m in modules if m.get('INSTANCE')=='aura_m3_regs_0')
motion_ports = [p.get('NAME') for p in motion.findall('./PORTS/PORT')]
audio = [m.get('INSTANCE') for m in modules if str(m.get('INSTANCE')).startswith('audio_ss_0_')]
ranges = [m.attrib for m in handoff.findall('.//MEMRANGE') if m.get('INSTANCE')=='aura_m3_regs_0']
design = json.loads(bd.read_text())['design']
bd_ports = list(design['ports'])
dt_text = dt.read_text()
retired_dt_nodes = [line.strip() for line in dt_text.splitlines() if any(x in line for x in ['audio_formatter','i2s_receiver','i2s_transmitter','xlnx,i2s','xlnx,audio'])]
def retired_nodes(path):
    data=path.read_bytes();header=struct.unpack_from('>10I',data)
    magic,total,offset,strings_offset,_,version,_,_,strings_size,structure_size=header
    assert magic==0xd00dfeed and version>=17 and total==len(data)
    strings=data[strings_offset:strings_offset+strings_size]
    end=offset+structure_size;assert end<=total
    stack=[];nodes=[]
    while offset<end:
        tag=struct.unpack_from('>I',data,offset)[0];offset+=4
        if tag==1:
            finish=data.index(b'\0',offset,end);name=data[offset:finish].decode()
            stack.append({'name':name,'path':'/'+('/'.join(n['name'] for n in stack[1:])+('/' if len(stack)>1 else '')+name),'properties':{}})
            offset=(finish+4)&~3
        elif tag==2:
            assert stack;nodes.append(stack.pop())
        elif tag==3:
            length,name_offset=struct.unpack_from('>II',data,offset);offset+=8
            assert stack and offset+length<=end
            name=strings[name_offset:strings.index(b'\0',name_offset)].decode()
            stack[-1]['properties'][name]=data[offset:offset+length]
            offset=(offset+length+3)&~3
        elif tag==4:continue
        elif tag==9:
            assert not stack;break
        else:raise ValueError('Invalid DTB tag')
    result=[]
    for node in nodes:
        props=node['properties'];compatible=props.get('compatible',b'').decode(errors='replace')
        if any(x in (node['path']+' '+compatible).lower() for x in ['audio_formatter','i2s_receiver','i2s_transmitter','xlnx,i2s','xlnx,audio']):
            result.append(dict(path=node['path'],compatible=compatible.rstrip('\0'),status=props.get('status',b'okay\0').decode().rstrip('\0')))
    return result
merged_audio=retired_nodes(merged)
checks = dict(hwh_servo_port='servo_pwm' in ports,hwh_motion_servo_port='servo_pwm' in motion_ports,
              hwh_legacy_audio_removed=not audio,bd_servo_port='servo_pwm' in bd_ports,
              bd_legacy_lrclk_removed='lrclk_tx' not in bd_ports,
              inspected_merged_dt_legacy_audio_inactive=all(n['status']=='disabled' for n in merged_audio))
result = dict(build_id=build['build_id'],metadata_matched=all(checks.values()),deployable=False,
              board_accessed=False,checks=checks,evidence=str(out),
              inspected_metadata_kind='EXISTING_SOURCE_PLATFORM_NOT_NEW_RELEASE',
              input_sha256={str(p):sha(p) for p in [bd,hwh,dt,merged,Path(__file__).resolve()]},
              hwh_external_ports=ports,hwh_motion_ports=motion_ports,legacy_audio_modules=audio,
              bd_external_ports=bd_ports,legacy_audio_dt_lines=retired_dt_nodes,
              inspected_merged_dt_audio_nodes=merged_audio,
              dt_verified_for_new_candidate=False,
              inherited_address_ranges=ranges,address_verified_for_new_candidate=False,
              limits=['Existing metadata only; not a new HWH/BD/DT generation',
                      'Current-position pulse and left/right mapping remain unmeasured'])
for p in [bd,hwh,dt,merged,Path(__file__).resolve()]:(out/p.name).write_bytes(p.read_bytes())
data=json.dumps(result,indent=2)+'\n';(out/'result.json').write_text(data)
(root/'CURRENT_METADATA_AUDIT.json').write_text(data)
print(json.dumps({k:result[k] for k in ['metadata_matched','deployable','checks','evidence','board_accessed']},indent=2))
