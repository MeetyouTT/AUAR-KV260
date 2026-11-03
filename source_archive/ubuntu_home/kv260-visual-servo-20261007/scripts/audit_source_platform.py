#!/usr/bin/env python3
"""Audit generated source handoff, not the old HWH or an assumed board state."""
import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def parameters(component):
    return {k: v.get('value') for k,v in component.get('parameters',{}).items()}

def component_diff(old, new, path=''):
    changes=[]
    for name, previous in old.items():
        current=new.get(name)
        here=f'{path}/{name}'
        if here in ('/audio_ss_0','/aura_m3_regs_0'):
            continue
        if current is None:
            changes.append(dict(component=here,kind='removed'));continue
        if previous.get('vlnv') != current.get('vlnv'):
            changes.append(dict(component=here,kind='vlnv',old=previous.get('vlnv'),new=current.get('vlnv')))
        a,b=parameters(previous),parameters(current)
        for key,value in a.items():
            if b.get(key) != value:
                changes.append(dict(component=here,kind='parameter',name=key,old=value,new=b.get(key)))
        changes.extend(component_diff(previous.get('components',{}),current.get('components',{}),here))
    return changes

def main():
    stage=json.loads((ROOT/'CURRENT_SOURCE_PLATFORM.json').read_text())
    assert stage['generation_passed'] and not stage['input_files_changed']
    base=Path(stage['evidence'])
    bds=list((base/'platform/platform.srcs').rglob('*.bd'))
    hwhs=list((base/'platform/platform.gen').rglob('kv260_ispMipiRx_vcu_DP.hwh'))
    assert len(bds)==len(hwhs)==1,(bds,hwhs)
    bd,hwh=bds[0],hwhs[0]
    old=json.loads((base/'inputs/bd/kv260_ispMipiRx_vcu_DP.bd').read_text())['design']
    new=json.loads(bd.read_text())['design']
    xml=ET.parse(hwh).getroot()
    modules={m.get('INSTANCE'):m for m in xml.iter('MODULE')}
    motion=modules['aura_m3_regs_0']
    external={p.get('NAME'):p.attrib for p in xml.findall('./EXTERNALPORTS/PORT')}
    motion_ports={p.get('NAME'):p.attrib for p in motion.findall('./PORTS/PORT')}
    clock_port=motion.find("./PORTS/PORT[@NAME='s_axi_aclk']")
    reset_port=motion.find("./PORTS/PORT[@NAME='s_axi_aresetn']")
    motion_params={p.get('NAME'):p.get('VALUE') for p in motion.iter('PARAMETER')}
    ranges=[m.attrib for m in xml.iter('MEMRANGE') if m.get('INSTANCE')=='aura_m3_regs_0']
    build=int(stage['build_id'],16)
    encoded_build=motion_params.get('BUILD_ID','')
    changes=component_diff(old['components'],new['components'])
    old_nets={frozenset(v['ports']) for v in old['nets'].values()}
    old_nets.discard(frozenset(('audio_ss_0/lrclk_tx','lrclk_tx')))
    expected_nets=old_nets|{frozenset(('aura_m3_regs_0/servo_pwm','servo_pwm'))}
    actual_nets={frozenset(v['ports']) for v in new['nets'].values() if v.get('ports')}
    old_intfs={frozenset(v['interface_ports']) for v in old['interface_nets'].values()}
    new_intfs={frozenset(v['interface_ports']) for v in new['interface_nets'].values()}
    checks={
        'generated_bd_servo_output':new['ports'].get('servo_pwm',{}).get('direction')=='O' and 'lrclk_tx' not in new['ports'],
        'generated_hwh_servo_output':'servo_pwm' in external and 'lrclk_tx' not in external,
        'motion_has_servo_output':'servo_pwm' in motion_ports,
        'motion_clock_connection':clock_port is not None and clock_port.get('SIGNAME')=='clk_wiz_0_clk_100M' and 99990000<=int(clock_port.get('CLKFREQUENCY','0'))<=100010000 and any(c.get('INSTANCE')=='clk_wiz_0' and c.get('PORT')=='clk_100M' for c in clock_port.findall('./CONNECTIONS/CONNECTION')),
        'motion_reset_connection':reset_port is not None and reset_port.get('POLARITY')=='ACTIVE_LOW' and any(c.get('INSTANCE')=='proc_sys_reset_100MHz' and c.get('PORT')=='peripheral_aresetn' for c in reset_port.findall('./CONNECTIONS/CONNECTION')),
        'exact_build_id':int(encoded_build,0)==build,
        'motion_address':any(int(r['BASEVALUE'],0)==0x80080000 and int(r['HIGHVALUE'],0)==0x80080fff for r in ranges),
        'audio_is_disabled_stub':new['components']['audio_ss_0'].get('vlnv')=='aura.local:user:aura_disabled_audio:1.0',
        'legacy_audio_children_removed':not any(n.startswith('audio_ss_0_') and not n.endswith('_stub') for n in modules),
        'retained_components_unchanged':not changes,
        'scalar_connections_match_expected':actual_nets==expected_nets,
        'axi_connections_preserved':old_intfs==new_intfs,
        'motion_rtl_matches_candidate':sha(base/'ip_repo/aura_visual_servo/src/visual_servo.sv')==sha(ROOT/'rtl/visual_servo.sv'),
    }
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out=ROOT/'evidence'/(stamp+'-source-platform-audit');out.mkdir()
    result=dict(evidence=str(out),source_platform_evidence=str(base),generated_handoff_checks_passed=all(checks.values()),
                checks=checks,board_accessed=False,deployable=False,
                implementation_built_from_generated_project=False,
                generated_bd=str(bd),generated_hwh=str(hwh),build_id=stage['build_id'],
                source_sha256={str(p):sha(p) for p in [bd,hwh,base/'pin.xdc',Path(__file__).resolve()]},
                motion_parameters=motion_params,motion_clock=motion_ports.get('s_axi_aclk'),motion_reset=motion_ports.get('s_axi_aresetn'),motion_address_ranges=ranges,retained_component_changes=changes,
                scalar_nets_missing=[sorted(n) for n in expected_nets-actual_nets],
                scalar_nets_extra=[sorted(n) for n in actual_nets-expected_nets])
    data=json.dumps(result,indent=2)+'\n'
    (out/'result.json').write_text(data)
    (ROOT/'CURRENT_SOURCE_PLATFORM_AUDIT.json').write_text(data)
    print(json.dumps({k:result[k] for k in ['evidence','generated_handoff_checks_passed','checks','retained_component_changes','scalar_nets_missing','scalar_nets_extra']},indent=2))
    return 0 if all(checks.values()) else 1

if __name__ == '__main__':
    raise SystemExit(main())
