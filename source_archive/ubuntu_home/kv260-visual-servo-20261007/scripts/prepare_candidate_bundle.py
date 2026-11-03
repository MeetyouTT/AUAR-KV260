#!/usr/bin/env python3
"""Seal a host review bundle. This script never installs or activates firmware."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
M3=Path('/home/ghmd/kv260-m3-axilite-20261002/test_bundle_attempt02')
TOOLS=Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin')
FDT=Path('/home/ghmd/petalinux/2022.2/components/yocto/buildtools_extended/sysroots/x86_64-petalinux-linux/usr/bin')
DTC172=Path('/home/ghmd/kv260-dpu41-control-20261001/dependencies/dtc-1.7.2')
APP='aura-visual-servo-b4096-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source_mode=sys.argv[1:]==['--source-platform']
    assert not sys.argv[1:] or source_mode
    build=json.loads((ROOT/('CURRENT_SOURCE_IMPLEMENTATION.json' if source_mode else 'CURRENT_BUILD.json')).read_text())
    audit=json.loads((ROOT/('CURRENT_SOURCE_FINAL_AUDIT.json' if source_mode else 'CURRENT_AUDIT.json')).read_text())
    stage=json.loads((ROOT/'CURRENT_SOURCE_PLATFORM.json').read_text())
    handoff=json.loads((ROOT/'CURRENT_SOURCE_PLATFORM_AUDIT.json').read_text())
    assert (build['implementation_passed'] if source_mode else build['implementation_complete']) and audit['offline_checkpoint_passed']
    assert audit['implementation']==build['evidence'] and audit['build_id']==build['build_id']
    assert stage['generation_passed'] and handoff['generated_handoff_checks_passed']
    assert stage['build_id']==build['build_id']
    for name,digest in build['source_sha256'].items():
        assert sha(ROOT/name)==digest,'Source changed since implementation: '+name
    for name,digest in audit['input_sha256'].items():
        assert sha(Path(name))==digest,'Input changed since independent audit: '+name
    source_root=Path(stage['evidence'])
    xsa=Path(build['evidence'])/'visual_servo_source_implemented.xsa' if source_mode else source_root/'visual_servo_source.xsa'
    assert xsa.is_file()
    with zipfile.ZipFile(xsa) as z:
        descriptions=[n for n in z.namelist() if Path(n).name=='kv260_ispMipiRx_vcu_DP.hwh']
        assert len(descriptions)==1
        exported=ET.fromstring(z.read(descriptions[0]))
        assert z.read(descriptions[0])==Path(handoff['generated_hwh']).read_bytes()
        motion=next(m for m in exported.iter('MODULE') if m.get('INSTANCE')=='aura_m3_regs_0')
        assert 'servo_pwm' in [p.get('NAME') for p in motion.findall('./PORTS/PORT')]
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out=ROOT/'evidence'/(stamp+'-candidate-bundle');out.mkdir()
    runtime=out/'bundle/lib/firmware/xilinx'/APP;runtime.mkdir(parents=True)
    prov=out/'bundle/provenance';prov.mkdir()
    commands=[]
    env=dict(os.environ,LD_LIBRARY_PATH=str(DTC172/'libfdt'))
    def run(argv,name,custom_env=None,cwd=None):
        p=subprocess.run([str(a) for a in argv],cwd=cwd or out,env=custom_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (out/(name+'.stdout')).write_bytes(p.stdout)
        (out/(name+'.stderr')).write_bytes(p.stderr)
        commands.append(dict(argv=[str(a) for a in argv],rc=p.returncode))
        assert p.returncode==0,(name,p.stderr.decode(errors='replace')[-1000:])
        return p.stdout
    bit=Path(build['evidence'])/('visual_servo_source.bit' if source_mode else 'visual_servo_joint.bit')
    assert audit['input_sha256'][str(bit)]==sha(bit)
    if source_mode:assert audit['input_sha256'][str(xsa)]==sha(xsa)
    bif=out/'full_pl.bif'
    bif.write_text('all:\n{\n  [destination_device=pl] '+str(bit)+'\n}\n')
    binary=runtime/(APP+'.bit.bin')
    run([TOOLS/'bootgen','-arch','zynqmp','-image',bif,'-o',binary],'bootgen')
    baseline=Path('/home/ghmd/kv260-dpu41-control-20261001/evidence/baseline-kv260-benchmark-b4096.bit.bin')
    assert binary.read_bytes()[:64]==baseline.read_bytes()[:64]
    dtbo=runtime/(APP+'.dtbo')
    original=M3/'provenance/baseline-kv260-benchmark-b4096.dtbo'
    shutil.copy2(original,dtbo)
    run([FDT/'fdtput','-t','s',dtbo,'/fragment@0/__overlay__','firmware-name',APP+'.bit.bin'],'firmware_name')
    before=run([TOOLS/'dtc','-I','dtb','-O','dts',original],'baseline_dt')
    after=run([TOOLS/'dtc','-I','dtb','-O','dts',dtbo],'candidate_dt')
    assert before.replace(b'kv260-benchmark-b4096.bit.bin',(APP+'.bit.bin').encode())==after
    (prov/'candidate.dts').write_bytes(after)
    roundtrip=prov/'roundtrip.dtbo'
    run([TOOLS/'dtc','-I','dts','-O','dtb','-o',roundtrip,prov/'candidate.dts'],'dt_roundtrip')
    assert run([TOOLS/'dtc','-I','dtb','-O','dts',roundtrip],'dt_roundtrip_read')==after
    merged=prov/'host-merged-system.dtb'
    board_dt=None
    if source_mode:
        board_dt=json.loads((ROOT/'CURRENT_BOARD_DT.json').read_text())
        base=Path(board_dt['path'])
        assert board_dt['read_only'] and board_dt['export_rc']==0 and sha(base)==board_dt['sha256']
        shutil.copy2(base,prov/'current-base.dtb')
        shutil.copy2(ROOT/'CURRENT_BOARD_DT.json',prov/'CURRENT_BOARD_DT.json')
    else:
        base=M3/'provenance/baseline-system.dtb'
    run([DTC172/'fdtoverlay','-i',base,'-o',merged,dtbo],'merge_dt',env)
    merged_dts=run([TOOLS/'dtc','-I','dtb','-O','dts',merged],'merged_dt')
    (prov/'host-merged-system.dts').write_bytes(merged_dts)
    assert not any(t in merged_dts for t in (b'xlnx,i2s',b'xlnx,audio-formatter',b'i2s_receiver',b'i2s_transmitter'))
    assert run([FDT/'fdtget','-t','s',merged,'/fpga-full','firmware-name'],'merged_firmware').strip()==(APP+'.bit.bin').encode()
    xclbin=runtime/(APP+'.xclbin')
    shutil.copy2(M3/'lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin',xclbin)
    assert sha(xclbin)=='875ca912d87b2c993716f4c353265a9cf403b0c9890442610e64291787caafc3'
    (runtime/'shell.json').write_text(json.dumps(dict(shell_type='XRT_FLAT',num_slots='1'))+'\n')
    for source in [Path(handoff['generated_bd']),Path(handoff['generated_hwh']),xsa,source_root/'pin.xdc']:
        shutil.copy2(source,prov/source.name)
    for name in [('CURRENT_SOURCE_IMPLEMENTATION.json' if source_mode else 'CURRENT_BUILD.json'),('CURRENT_SOURCE_FINAL_AUDIT.json' if source_mode else 'CURRENT_AUDIT.json'),'CURRENT_SOURCE_PLATFORM.json','CURRENT_SOURCE_PLATFORM_AUDIT.json']:
        shutil.copy2(ROOT/name,prov/name)
    manifest=dict(application=APP,build_id=build['build_id'],axi_base='0x80080000',axi_range='0x1000',
                  register_identity={'id':'0x56535256','abi':1,'build_id':build['build_id']},
                  source_handoff_generated=True,offline_netlist_audited=True,dt_host_merge_passed=True,
                  implementation_built_from_generated_project=source_mode,source_netlist_equivalence_verified=False,
                  bitstream_and_handoff_from_same_project=source_mode,
                  board_test_ready=source_mode,deployable=False,board_accessed=False,
                  qualification_scope='controlled_bench_candidate',
                  timing= audit.get('timing'),external_timing_gaps=audit.get('external_timing_gaps'),
                  implementation_critical_warning_count=len(audit.get('implementation_critical_warnings',[])),
                  physical_actuation_enabled=False,
                  remaining=([] if source_mode else ['Source-project implementation or source/netlist equivalence check'])+[
                             'Single-writer transport and measured submission budget',
                             'Current board DT verification and exact identity/STOP/PWM/coexistence tests',
                             'Current-position pulse/polarity/fixed-camera anchors',
                             'External timing constraints and retained platform warnings before formal release'],
                  runtime_files={str(p.relative_to(out/'bundle')):sha(p) for p in sorted(runtime.iterdir())},
                  source_bitstream_sha256=sha(bit),source_project_evidence=str(source_root),
                  dt_base_sha256=sha(base),dt_export_boot_id=board_dt['boot_id'] if board_dt else None,
                  generated_handoff_audit=handoff['evidence'],commands=commands,evidence=str(out))
    (prov/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'bundle/README.md').write_text('# 视觉与舵机联合候选审阅包\n\n'+('位流和硬件描述来自同一个完成实现的源工程，独立主机检查通过。板端身份、共存、PWM 和停止验证尚未完成，真实动作禁止启用。\n' if source_mode else '主机生成的描述和电路工件已封存。源工程实现/等价性及板测尚缺；本包不能直接安装或启用真实动作。\n')+'\nXSA 不嵌入位流；位流单独封存并记录哈希。详情见 provenance/manifest.json。\n')
    files=sorted(p for p in (out/'bundle').rglob('*') if p.is_file())
    (out/'bundle/SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(out/'bundle'))+'\n' for p in files))
    run(['sha256sum','-c','SHA256SUMS'],'bundle_sha_check',cwd=out/'bundle')
    (ROOT/'CURRENT_CANDIDATE_BUNDLE.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':
    main()
