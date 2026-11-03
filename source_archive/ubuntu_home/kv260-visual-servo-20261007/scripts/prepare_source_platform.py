#!/usr/bin/env python3
"""Generate an isolated Vivado platform from sources; never touch the board."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
M3 = Path('/home/ghmd/kv260-m3-axilite-20261002')
ADAPT = Path('/home/ghmd/kv260-adaptation-check-20261006')
PRJ = M3/'src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj'
BD = PRJ/'prj.srcs/sources_1/bd/kv260_ispMipiRx_vcu_DP/kv260_ispMipiRx_vcu_DP.bd'
XDC = PRJ/'prj.srcs/constrs_1/imports/xdc/pin.xdc'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def annotated_audio(source):
    # Interface declarations only; every executable RTL statement is unchanged.
    buses = {
        'm_axi_mm2s_audio': ('AXI4', 'READ_ONLY', 'm_axi_aclk'),
        'm_axi_s2mm_audio': ('AXI4', 'WRITE_ONLY', 'm_axi_aclk'),
        's_axi_ctrl_i2s_rx': ('AXI4LITE', 'READ_WRITE', 'ACLK'),
        's_axi_ctrl_i2s_tx': ('AXI4LITE', 'READ_WRITE', 'ACLK'),
        's_axi_lite_audio_fmt': ('AXI4LITE', 'READ_WRITE', 'ACLK'),
    }
    seen = set()
    def declaration(match):
        line, port = match.group(0), match.group(1)
        attrs = []
        for bus, (protocol, mode, _) in buses.items():
            if port.startswith(bus+'_'):
                signal = port[len(bus)+1:].upper()
                attrs.append(f'X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 {bus} {signal}"')
                if bus not in seen:
                    seen.add(bus)
                    attrs.append(f'X_INTERFACE_PARAMETER = "PROTOCOL {protocol}, READ_WRITE_MODE {mode}"')
        if port in ('ACLK', 'm_axi_aclk'):
            reset = 'ARESETN' if port == 'ACLK' else 'm_axi_aresetn'
            associated = ':'.join(b for b, (_, _, c) in buses.items() if c == port)
            attrs.extend([f'X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 {port} CLK"',
                          f'X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF {associated}, ASSOCIATED_RESET {reset}"'])
        if port in ('ARESETN', 'm_axi_aresetn'):
            attrs.extend([f'X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 {port} RST"',
                          'X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW"'])
        return ''.join(f'    (* {a} *)\n' for a in attrs)+line
    annotated = re.sub(r'^    (?:input|output) wire[^;]*?\b(\w+);$', declaration, source, flags=re.M)
    assert seen == set(buses)
    # Removing the added annotations must recover the source byte for byte.
    assert re.sub(r'^    \(\* X_INTERFACE_[^\n]*\n', '', annotated, flags=re.M) == source
    return annotated

def main():
    out = ROOT/'evidence'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-source-platform')
    out.mkdir()
    sources = [BD, XDC, ROOT/'rtl/visual_servo.sv', ADAPT/'fpga/rtl/disabled_audio.sv',
               ROOT/'scripts/prepare_source_platform.tcl', Path(__file__).resolve()]
    hashes = {str(p): sha(p) for p in sources}
    (out/'inputs/bd').mkdir(parents=True)
    (out/'inputs/bd'/BD.name).write_bytes(BD.read_bytes())
    shutil.copytree(BD.parent/'ip', out/'inputs/bd/ip')
    xdc = re.sub(r'\blrclk_tx\b', 'servo_pwm', XDC.read_text())
    xdc = xdc.replace('DRIVE 4 [get_ports servo_pwm]', 'DRIVE 8 [get_ports servo_pwm]')
    assert 'DRIVE 8 [get_ports servo_pwm]' in xdc
    (out/'pin.xdc').write_text(xdc)
    (out/'visual_servo.sv').write_bytes((ROOT/'rtl/visual_servo.sv').read_bytes())
    (out/'disabled_audio.sv').write_text(annotated_audio((ADAPT/'fpga/rtl/disabled_audio.sv').read_text()))
    (out/'prepare_source_platform.tcl').write_bytes((ROOT/'scripts/prepare_source_platform.tcl').read_bytes())
    repos = [PRJ/'../../../int/xo/ip_repo/xilinx_com_RTLKernel_DPUCZDX8G_1_0',
             PRJ/'../.local/hw_platform/iprepo', PRJ/'../.local/hw_platform/ipcache',
             Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/data/ip')]
    (out/'repos.txt').write_text('\n'.join(str(p.resolve()) for p in repos)+'\n')
    build = json.loads((ROOT/'CURRENT_BUILD.json').read_text())
    status = dict(state='running', evidence=str(out), source_sha256=hashes,
                  build_id=build['build_id'], board_accessed=False, deployable=False)
    def save():
        data=json.dumps(status, indent=2)+'\n'
        (out/'status.json').write_text(data)
        (ROOT/'CURRENT_SOURCE_PLATFORM.json').write_text(data)
    save()
    env = dict(os.environ, AURA_PLATFORM_OUT=str(out), AURA_PLATFORM_BUILD_ID=str(int(build['build_id'], 16)))
    argv=['bash','--noprofile','--norc','-c',
          'source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh; exec vivado -mode batch -source "$1" -log "$2" -journal "$3"',
          'aura-source-platform',str(out/'prepare_source_platform.tcl'),str(out/'vivado.log'),str(out/'vivado.jou')]
    print(json.dumps(status), flush=True)
    with (out/'console.txt').open('wb') as log:
        proc=subprocess.Popen(argv, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
        status['pid']=proc.pid;save()
        rc=proc.wait()
    changed=[name for name,value in hashes.items() if sha(Path(name)) != value]
    status.update(state='finished', rc=rc, input_files_changed=changed,
                  finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    status['generation_passed']=rc == 0 and not changed and 'AURA_SOURCE_PLATFORM_GENERATED' in (out/'console.txt').read_text(errors='replace')
    save()
    print(json.dumps(status), flush=True)
    return 0 if status['generation_passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
