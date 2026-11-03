#!/usr/bin/env python3
"""Prepare bounded M3 commands; all UART actions remain separately reviewable."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
REPAIR = Path('/home/ghmd/kv260-overlay-repair-20261002')
PREVIOUS = REPAIR / 'evidence/board_validation_20261003T005805Z'
M3 = Path('/home/ghmd/kv260-m3-axilite-20261002')
OFFICIAL = 'kv260-benchmark-b4096'
CANDIDATE = 'kv260-benchmark-b4096-m3'
ORIGINAL = '0991D1B457855C8987936E6'
PATCHED = '9BDC942A6014BCCBD1DCB78'
MODULE_SHA = '5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def phase_ok(run, phase):
    rows = [json.loads(line) for line in (run / (phase+'.results.jsonl')).read_text().splitlines()]
    commands = [row for row in rows if row.get('type')=='command']
    manifest = json.loads((run / (phase+'.commands.json')).read_text())
    assert [row['command'] for row in commands] == [row['command'] for row in manifest]
    assert [row['id'] for row in commands] == [row['id'] for row in manifest]
    for row in commands:
        assert row['complete'] and row['exit_code']==0
        assert sha(run/(phase+'.'+row['id']+'.output'))==row['integrity_sha256']


def main():
    run = Path(sys.argv[1]).resolve()
    for phase in ['01-preflight','02-state','03-capabilities']:
        phase_ok(run, phase)
    assert (run/'01-preflight.kernel_config.output').read_bytes()==(REPAIR/'evidence/image_files/kernel.config').read_bytes()
    state = json.loads((run/'02-state.drivers_and_parameters.output').read_text())
    caps = json.loads((run/'03-capabilities.capabilities.output').read_text())
    assert state['root_device']=='mmcblk1p2' and state['loaded_srcversion']==ORIGINAL
    assert state['zocl_parameters']=={'enable_xgq_ert':'1'}
    assert state['fpga_state']=='operating' and state['firmware_name']==OFFICIAL+'.bit.bin'
    assert not caps['m3_target_exists'] and caps['root_free_bytes']>134217728
    assert caps['devmem_applet'] and caps['dev_mem_character_device']
    assert caps['prior_repaired_module_sha256']==MODULE_SHA
    old_hashes = {row['path']:row['sha256'] for row in
                  map(json.loads,(PREVIOUS/'r5-final-state.baseline_hashes.output').read_text().splitlines())}
    new_hashes = {row['path']:row['sha256'] for row in
                  map(json.loads,(run/'02-state.baseline_hashes.output').read_text().splitlines())}
    assert old_hashes==new_hashes
    identity = (run/'01-preflight.identity_runtime.output').read_text()
    for line in identity.splitlines():
        if line.startswith('{"path":'):
            row=json.loads(line)
            assert row['sha256']==sha(REPAIR/'evidence/image_files'/Path(row['path']).name)
    meta=json.loads((run/'run.json').read_text())
    work=meta['board_work_directory']
    old_guard=PREVIOUS/'board_guard.py'
    guard_sha=sha(old_guard)
    old_board_guard='/home/root/kv260-zocl-repair-20261003T005805Z/baseline/board_guard.py'
    sources=run/'action_sources';sources.mkdir(exist_ok=False)
    (sources/'guard_reference.py').write_bytes(old_guard.read_bytes())
    hash_payload=json.dumps(new_hashes,sort_keys=True)
    hash_sha=hashlib.sha256(hash_payload.encode()).hexdigest()

    def loader(path):
        return "import hashlib\nfrom pathlib import Path\np=Path(%r)\nG=p.read_bytes()\nassert hashlib.sha256(G).hexdigest()==%r,'Guard source changed'\nexec(compile(G,str(p),'exec'))\nWORK=Path(%r)\n" % (path,guard_sha,work)

    bootstrap=loader(old_board_guard)
    prefix=loader(work+'/baseline/guard_reference.py')+r'''def baseline_hashes():
 p=WORK/'baseline/runtime-hashes.json'
 assert digest(p)==%r,'Saved manifest changed'
 for path,expected in json.loads(p.read_text()).items():
  assert digest(path)==expected,'Baseline file changed: '+path
def gate(expected,app):
 guard(expected,app)
 baseline_hashes()
 if app is not None:
  assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
  assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==app+'.bit.bin'
def capture(label):
 snapshot(label)
 print(label+'_MANAGER_JOURNAL_BEGIN',flush=True)
 r=subprocess.run(['journalctl','-u','dfx-mgrd','--no-pager','-n','200','-o','short-monotonic'])
 print(label+'_MANAGER_JOURNAL_RC '+str(r.returncode),flush=True)
 print(label+'_MANAGER_JOURNAL_END',flush=True)
''' % hash_sha

    def command(code):
        compile(code,'board_action','exec')
        encoded=base64.b64encode(gzip.compress(code.encode(),mtime=0)).decode()
        result='python3 -B -c '+shlex.quote('import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(encoded)+')))')
        assert len(result.encode())*4/3+850<3900, 'UART command too long: '+str(len(result))
        return result

    def save(phase, entries):
        manifest=[]
        for entry in entries:
            source_path=sources/(phase+'.'+entry['id']+'.py')
            source_path.write_text(entry['code'])
            manifest.append({'id':entry['id'],'command':command(entry['code']),'timeout':entry.get('timeout',180)})
        path=run/(phase+'.commands.json')
        assert not path.exists()
        path.write_text(json.dumps(manifest,indent=2)+'\n')

    def one(phase, body, pre=prefix, timeout=180):
        save(phase,[{'id':phase.split('-',1)[1],'code':pre+body,'timeout':timeout}])

    backup='''guard(%r,%r)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r
assert not Path('/lib/firmware/xilinx/%s').exists()
WORK.mkdir(exist_ok=False);b=WORK/'baseline';b.mkdir()
for src,name in [('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko','original-zocl.ko'),('/proc/config.gz','config.gz'),('/etc/vart.conf','vart.conf'),('/sys/firmware/fdt','boot-fdt.dtb')]:
 (b/name).write_bytes(Path(src).read_bytes())
(b/'guard_reference.py').write_bytes(G)
(b/'runtime-hashes.json').write_text(%r)
(b/'dmesg-before.output').write_bytes(subprocess.check_output(['dmesg']))
(b/'state.json').write_text(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'parameters':PARAMS,'active':active_packages(),'uptime':Path('/proc/uptime').read_text().strip()},indent=2))
candidate=Path(%r)
assert digest(candidate)==%r
(WORK/'repaired-zocl.ko').write_bytes(candidate.read_bytes())
assert digest(WORK/'repaired-zocl.ko')==%r
print(json.dumps({'backup':str(b),'original_module_sha256':digest(b/'original-zocl.ko'),'candidate_sha256':digest(WORK/'repaired-zocl.ko')},indent=2))
''' % (ORIGINAL,OFFICIAL,caps['boot_id'],CANDIDATE,hash_payload,meta['prior_repaired_module'],MODULE_SHA,MODULE_SHA)
    one('04-save-baseline',backup,pre=bootstrap)
    one('04b-save-snapshots','''gate(%r,%r)
import tarfile
b=WORK/'baseline'
with tarfile.open(str(b/'official-firmware.tar.gz'),'x:gz') as tar:
 for p in sorted(Path('/lib/firmware/xilinx/%s').iterdir()):
  assert p.is_file() and not p.is_symlink()
  tar.add(str(p),arcname=p.name,recursive=False)
with tarfile.open(str(b/'live-device-tree.tar.gz'),'x:gz') as tar:
 base=Path('/proc/device-tree').resolve()
 for p in sorted(base.rglob('*')):
  if p.is_file() and not p.is_symlink():tar.add(str(p),arcname=str(p.relative_to(base)),recursive=False)
capture('AFTER')
records={p.name:digest(p) for p in b.iterdir() if p.is_file()}
(b/'manifest.json').write_text(json.dumps(records,indent=2))
print('BACKUP_HASHES '+json.dumps(records),flush=True)
''' % (ORIGINAL,OFFICIAL,OFFICIAL))

    def samples(phase, previous, expected, app, performance=False):
        entries=[]
        for row in json.loads((PREVIOUS/(previous+'.commands.json')).read_text()):
            shell=row['command'].replace('/'+OFFICIAL+'/'+OFFICIAL+'.xclbin','/'+app+'/'+app+'.xclbin')
            body="gate(%r,%r)\nsubprocess.run(%r,shell=True,check=True)\ngate(%r,%r)\n" % (expected,app,shell,expected,app)
            entries.append({'id':row['id'],'code':prefix+body,'timeout':row['timeout']+30})
        save(phase,entries)

    samples('05-official-functional','03-baseline-functional',ORIGINAL,OFFICIAL)
    samples('06-official-performance','04-baseline-performance',ORIGINAL,OFFICIAL,True)
    archive=json.loads((M3/'evidence/m3_bundle_review/archive_manifest.json').read_text())['archives'][1]
    assert sha(M3/archive['path'])==archive['sha256']
    one('08-unpack-bundle','''gate(%r,%r)
import tarfile
p=WORK/'m3-bundle.tar.gz';assert digest(p)==%r
stage=WORK/'m3-stage';stage.mkdir(exist_ok=False)
with tarfile.open(str(p),'r:gz') as tar:
 members=tar.getmembers()
 assert len(members)==26 and sorted(m.name for m in members)==sorted(%r)
 for m in members:
  parts=Path(m.name).parts
  assert m.isfile() and not m.name.startswith('/') and '..' not in parts
  target=stage/m.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as out:out.write(tar.extractfile(m).read())
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=str(stage),check=True)
print('STAGE_READY '+str(stage),flush=True)
''' % (ORIGINAL,OFFICIAL,archive['sha256'],archive['member_names']))
    manifest=M3/'test_bundle/provenance/runtime_manifest.json'
    tool=M3/'board/m3_board_check.py'
    assert sha(tool)==sha(M3/'test_bundle/board/m3_board_check.py')
    manifest_sha=sha(manifest);tool_sha=sha(tool)
    runtime=json.loads(manifest.read_text())
    one('09-install-independent-app','''gate(%r,%r)
stage=WORK/'m3-stage';p=stage/'provenance/runtime_manifest.json'
assert digest(p)==%r
manifest=json.loads(p.read_text());assert manifest['application']==%r and len(manifest['runtime_files'])==4
target=Path('/lib/firmware/xilinx/%s');target.mkdir(exist_ok=False)
for item in manifest['runtime_files']:
 rel=Path(item['path']);assert rel.parent==Path('lib/firmware/xilinx/%s')
 src=stage/rel;assert src.is_file() and not src.is_symlink() and digest(src)==item['sha256']
 with (target/rel.name).open('xb') as out:out.write(src.read_bytes())
 assert digest(target/rel.name)==item['sha256']
 print('INSTALLED_HASH '+json.dumps({'path':str(target/rel.name),'sha256':item['sha256']}),flush=True)
text=subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True);print(text,flush=True)
assert any(line.split() and line.split()[0]==%r for line in text.splitlines()),'M3 package not registered'
gate(%r,%r)
''' % (ORIGINAL,OFFICIAL,manifest_sha,CANDIDATE,CANDIDATE,CANDIDATE,CANDIDATE,ORIGINAL,OFFICIAL))

    def remove(phase, expected, app):
        one(phase,"gate(%r,%r)\ncapture('BEFORE')\nsubprocess.run(['dfx-mgr-client','-remove'],check=True)\ngate(%r,None)\nassert not Path('/sys/bus/platform/devices/axi:zyxclmm_drm').exists()\ncapture('AFTER')\n" % (expected,app,expected))

    remove('10-remove-original-app',ORIGINAL,OFFICIAL)
    one('11-unload-original-module',"gate(%r,None)\ncapture('BEFORE')\nsubprocess.run(['rmmod','zocl'],check=True)\ngate(None,None)\ncapture('AFTER')\n" % ORIGINAL)
    one('12-load-repaired-module',"gate(None,None)\ncapture('BEFORE')\np=WORK/'repaired-zocl.ko';assert digest(p)==%r\nsubprocess.run(['insmod',str(p),'enable_xgq_ert=1'],check=True)\ngate(%r,None)\ncapture('AFTER')\n" % (MODULE_SHA,PATCHED))
    one('13-load-m3',"gate(%r,None)\ncapture('BEFORE')\np=WORK/'m3-stage/provenance/runtime_manifest.json';assert digest(p)==%r\nfor item in json.loads(p.read_text())['runtime_files']:assert digest('/'+item['path'])==item['sha256']\nsubprocess.run(['dfx-mgr-client','-load',%r],check=True)\ngate(%r,%r)\ncapture('AFTER')\n" % (PATCHED,manifest_sha,CANDIDATE,PATCHED,CANDIDATE))
    firmware='/lib/firmware/xilinx/'+CANDIDATE+'/'+CANDIDATE+'.xclbin'
    save('14-m3-query',[
        {'id':'dpu_query','code':prefix+"gate(%r,%r)\nsubprocess.run(['env',%r,'xdputil','query'],check=True)\ngate(%r,%r)\n" % (PATCHED,CANDIDATE,'XLNX_VART_FIRMWARE='+firmware,PATCHED,CANDIDATE)},
        {'id':'metadata_after_query','code':prefix+"gate(%r,%r)\ncapture('AFTER')\n" % (PATCHED,CANDIDATE)}])
    def register_check(phase, stage):
        one(phase,"gate(%r,%r)\nbase=WORK/'m3-stage';p=base/'board/m3_board_check.py';assert digest(p)==%r\nsubprocess.run(['python3','-B',str(p),%r,'--bundle-root',str(base)],check=True)\ngate(%r,%r)\n" % (PATCHED,CANDIDATE,tool_sha,stage,PATCHED,CANDIDATE))
    register_check('15-m3-identity','identity')
    register_check('16-m3-scratch','scratch')
    samples('17-m3-functional','03-baseline-functional',PATCHED,CANDIDATE)
    samples('18-m3-performance','04-baseline-performance',PATCHED,CANDIDATE,True)
    one('19-m3-post-check','''gate(%r,%r)
import importlib.util
base=WORK/'m3-stage';p=base/'board/m3_board_check.py';assert digest(p)==%r
spec=importlib.util.spec_from_file_location('m3check',str(p));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result=module.preflight();busybox=module.candidate_gate(base,result)
values=tuple(module.read32(busybox,offset) for offset in (0,4,8))
assert values==module.EXPECTED_ID
scratch=module.read32(busybox,12)
print('POST_CHECK '+json.dumps({'identity':list(values),'scratch':'0x%%08x'%%scratch}),flush=True)
gate(%r,%r)
capture('AFTER')
''' % (PATCHED,CANDIDATE,tool_sha,PATCHED,CANDIDATE))
    remove('20-remove-m3',PATCHED,CANDIDATE)
    one('21-unload-repaired-module',"gate(%r,None)\ncapture('BEFORE')\nsubprocess.run(['rmmod','zocl'],check=True)\ngate(None,None)\ncapture('AFTER')\n" % PATCHED)
    one('22-restore-original-module',"gate(None,None)\ncapture('BEFORE')\nassert digest(WORK/'baseline/original-zocl.ko')==ORIGINAL_SHA\nsubprocess.run(['modprobe','zocl','enable_xgq_ert=1'],check=True)\ngate(%r,None)\ncapture('AFTER')\n" % ORIGINAL)
    one('23-restore-official-app',"gate(%r,None)\ncapture('BEFORE')\nsubprocess.run(['dfx-mgr-client','-load',%r],check=True)\ngate(%r,%r)\ncapture('AFTER')\n" % (ORIGINAL,OFFICIAL,ORIGINAL,OFFICIAL))
    samples('24-restored-functional','03-baseline-functional',ORIGINAL,OFFICIAL)
    final=[]
    for row in json.loads((PREVIOUS/'02-state.commands.json').read_text()):
        final.append({'id':row['id'],'code':prefix+"gate(%r,%r)\nsubprocess.run(%r,shell=True,check=True)\n" % (ORIGINAL,OFFICIAL,row['command']),'timeout':row['timeout']+30})
    final.append({'id':'final_kernel','code':prefix+"gate(%r,%r)\ncapture('AFTER')\n" % (ORIGINAL,OFFICIAL)})
    save('25-final-state',final)

    sender_tree=ast.parse((PREVIOUS/'transfer_candidate.py').read_text())
    constants={node.targets[0].id:ast.literal_eval(node.value) for node in sender_tree.body
               if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
               and node.targets[0].id in ('SOURCE','BOARD')}
    sender=constants['SOURCE']
    sender=sender.replace(str(REPAIR/'bundle/kv260-zocl-reference-repair-20261002.tar.gz'),str(M3/archive['path']))
    sender=sender.replace('3126707fe3c9165fd743dcbcc1408247337b538524e8b4de6c4edaa4e997cfef',archive['sha256'])
    sender=sender.replace('/home/root/kv260-zocl-repair-20261003T005805Z/candidate.tar.gz',work+'/m3-bundle.tar.gz')
    sender=sender.replace('06-candidate-transfer','07-transfer-bundle').replace('sealed driver archive','sealed M3 test bundle')
    sender=sender.replace('Transfer the fixed JPEG to an independent board directory using acknowledged UART frames.', 'Transfer the fixed M3 test bundle using acknowledged UART frames.')
    receiver=constants['BOARD']
    receiver=receiver.replace("fd=sys.stdin.fileno();", "saved=__import__('json').loads((p.parent/'baseline/state.json').read_text())\nassert saved['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()\nassert hashlib.sha256(Path('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko').read_bytes()).hexdigest()=='215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d'\nfd=sys.stdin.fileno();")
    (run/'uart_sender_source.py').write_text(sender)
    (sources/'07-transfer_receiver.py').write_text(receiver)
    wrapper="import ast,hashlib\nfrom pathlib import Path\nR=Path(__file__).resolve().parent\ns=(R/'uart_sender_source.py').read_bytes();assert hashlib.sha256(s).hexdigest()==%r\nb=(R/'action_sources/07-transfer_receiver.py').read_bytes();assert hashlib.sha256(b).hexdigest()==%r\ntree=ast.parse(s.decode())\nfor node in tree.body:\n if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='board_code' for target in node.targets):node.value=ast.copy_location(ast.Str(s=b.decode()),node.value)\nexec(compile(tree,'reviewed_m3_uart_sender','exec'))\n" % (sha(run/'uart_sender_source.py'),sha(sources/'07-transfer_receiver.py'))
    (run/'transfer_bundle.py').write_text(wrapper)
    ordered=['04-save-baseline','04b-save-snapshots','05-official-functional','06-official-performance','07-transfer-bundle','08-unpack-bundle','09-install-independent-app','10-remove-original-app','11-unload-original-module','12-load-repaired-module','13-load-m3','14-m3-query','15-m3-identity','16-m3-scratch','17-m3-functional','18-m3-performance','19-m3-post-check','20-remove-m3','21-unload-repaired-module','22-restore-original-module','23-restore-official-app','24-restored-functional','25-final-state']
    preparation={'ordered_phases':ordered,'baseline_hashes_match_prior_run':True,'preflight_kernel_config_matches':True,
                 'guard_reference_sha256':guard_sha,'runtime_manifest_sha256':manifest_sha,'board_tool_sha256':tool_sha,
                 'test_archive':archive,'candidate_runtime':runtime,
                 'source_hashes':{str(p.relative_to(run)):sha(p) for p in sorted(sources.glob('*.py'))},
                 'manifest_hashes':{p.name:sha(p) for p in sorted(run.glob('*.commands.json'))}}
    (run/'preparation.json').write_text(json.dumps(preparation,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'prepared_phases':len(ordered),'sources':len(preparation['source_hashes']),'preflight_passed':True,'runtime_archive_bytes':archive['bytes']}))


if __name__=='__main__':
    main()
