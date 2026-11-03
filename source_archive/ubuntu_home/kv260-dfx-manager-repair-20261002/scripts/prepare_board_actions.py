#!/usr/bin/env python3
"""Freeze the reversible candidate validation, bundle and separate UART phases."""
import base64
import datetime
import gzip
import hashlib
import json
import shlex
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = Path('/home/ghmd/kv260-m3-boardtest-20261002/evidence/20261003T021012Z')
ORIGINAL = '0991D1B457855C8987936E6'
REPAIRED = '9BDC942A6014BCCBD1DCB78'
MODULE_SHA = '5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412'
OFFICIAL = 'kv260-benchmark-b4096'
M3 = 'kv260-benchmark-b4096-m3'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wire(code):
    compile(code, 'reviewed_action', 'exec')
    encoded = base64.b64encode(gzip.compress(code.encode(), mtime=0)).decode()
    text = 'python3 -B -c ' + shlex.quote('import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(encoded) + ')))')
    assert len(text) * 4 / 3 + 850 < 3900, 'UART line too long: ' + str(len(text))
    return text


def main():
    preflight = Path((ROOT / 'evidence/BOARD_PREFLIGHT_RUN').read_text().strip())
    rows = [json.loads(line) for line in (preflight / '01-readonly.results.jsonl').read_text().splitlines()]
    for row in rows:
        if row.get('type') == 'command':
            assert row['complete'] and row['exit_code'] == 0
            assert sha(preflight / ('01-readonly.' + row['id'] + '.output')) == row['integrity_sha256']
    inventory = json.loads((preflight / '01-readonly.identity_manager.output').read_text())
    runtime = [json.loads(p.read_text()) for p in ROOT.glob('evidence/*-runtime-review/status.json')]
    good = [r for r in runtime if r['passed']]
    assert len(good) == 1
    candidate = [b for b in good[0]['binaries'] if b['phase'] == 'patched' and Path(b['path']).name == 'dfx-mgrd'][0]
    for lib in good[0]['image_libraries']:
        assert inventory['files'][lib['image_path']]['sha256'] == lib['sha256']
    assert inventory['files']['/usr/bin/dfx-mgrd']['sha256'] == sha(Path('/home/ghmd/kv260-overlay-repair-20261002/evidence/image_files/dfx-mgrd'))
    inputs = {p: item['sha256'] for p, item in inventory['files'].items()}
    inputs.update({r['path']: r['sha256'] for r in map(json.loads, (OLD / '02-state.baseline_hashes.output').read_text().splitlines())})
    installed_m3 = map(json.loads, (OLD / '26-post-review.installed_hashes.output').read_text().splitlines())
    inputs.update({item['path']: item['sha256'] for item in installed_m3})
    inputs['/etc/dfx-mgrd/default_firmware'] = hashlib.sha256(inventory['config']['/etc/dfx-mgrd/default_firmware'].encode()).hexdigest()
    inputs['/lib/systemd/system/dfx-mgr.service'] = sha(ROOT / 'evidence/image-dfx-mgr.service')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run = ROOT / 'evidence' / (stamp + '-board-validation')
    run.mkdir(parents=True, exist_ok=False)
    sources = run / 'action_sources'; sources.mkdir()
    work = '/home/root/kv260-dfx-manager-repair-' + stamp
    override = '/run/systemd/system/dfx-mgr.service.d/kv260-watchtest-' + stamp + '.conf'
    guard_reference = (OLD / 'action_sources/guard_reference.py').read_text()
    guard_sha = hashlib.sha256(guard_reference.encode()).hexdigest()
    bootstrap = "import hashlib\nfrom pathlib import Path\np=Path('/home/root/kv260-zocl-repair-20261003T005805Z/baseline/board_guard.py')\ns=p.read_bytes()\nassert hashlib.sha256(s).hexdigest()==%r\nexec(compile(s,str(p),'exec'))\nWORK=Path(%r)\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r\n" % (guard_sha, work, inventory['boot_id'])
    guard = guard_reference + "\nWORK=Path(%r)\nINPUTS=%r\nCANDIDATE_SHA=%r\nOVERRIDE=Path(%r)\n" % (work, inputs, candidate['sha256'], override)
    guard += '''def files_guard():
 for path,expected in INPUTS.items():
  if path!='/etc/vart.conf':assert digest(path)==expected,'Original file changed: '+path
def gate(driver,app):
 guard(driver,app)
 files_guard()
 if app is not None:
  assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
  assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\\0').decode()==app+'.bit.bin'
  assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/'+app+'/'+app+'.xclbin\\n'
def manager_pid():
 return int(subprocess.check_output(['systemctl','show','dfx-mgr.service','--property=MainPID','--value'],text=True))
def manager_guard(candidate):
 pid=manager_pid();assert pid>0 and subprocess.check_output(['systemctl','is-active','dfx-mgr.service'],text=True).strip()=='active'
 path=str(WORK/'candidate-stage/dfx-mgrd') if candidate else '/usr/bin/dfx-mgrd'
 assert os.readlink('/proc/%d/exe'%pid)==path,'Unexpected manager executable'
 assert digest(path)==(CANDIDATE_SHA if candidate else INPUTS['/usr/bin/dfx-mgrd'])
 if candidate:assert not manager_errors(),'Candidate manager error; inspect full log'
def manager_errors():
 p=WORK/'candidate-manager.log'
 return [s for s in p.read_text(errors='replace').splitlines() if 'ERROR:' in s] if p.exists() else []
def watches():
 total=0
 for p in (Path('/proc')/str(manager_pid())/'fdinfo').iterdir():
  try:total+=p.read_text().count('inotify wd:')
  except FileNotFoundError:pass
 return total
def wait_manager(candidate):
 import socket,time
 for unused in range(100):
  pid=manager_pid()
  if pid>0:
   s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
   ret=s.connect_ex('/tmp/dfx-mgrd.socket');s.close()
   if ret==0:manager_guard(candidate);return
  time.sleep(.1)
 raise RuntimeError('Manager startup did not become ready')
'''
    bundle = ROOT / 'bundle-v2'; bundle.mkdir(exist_ok=False)
    payload = bundle / 'kv260-dfx-watch-candidate'; payload.mkdir()
    shutil.copy2(str(ROOT / candidate['path']), str(payload / 'dfx-mgrd'))
    (payload / 'board_guard.py').write_text(guard)
    (payload / 'runtime-input-hashes.json').write_text(json.dumps(inputs, sort_keys=True, indent=2) + '\n')
    shutil.copy2(str(ROOT / 'artifacts/watch-dedup.patch'), str(payload / 'watch-dedup.patch'))
    members = {p.name: sha(p) for p in sorted(payload.iterdir())}
    (payload / 'SHA256SUMS').write_text(''.join(d + '  ' + n + '\n' for n, d in sorted(members.items())))
    archive = bundle / 'kv260-dfx-watch-candidate.tar.gz'
    with tarfile.open(str(archive), 'w:gz') as tar:
        for p in sorted(payload.iterdir()): tar.add(str(p), arcname=payload.name + '/' + p.name, recursive=False)
    archive_sha = sha(archive)
    (bundle / 'archive_manifest.json').write_text(json.dumps({'bytes': archive.stat().st_size, 'sha256': archive_sha,
        'member_hashes': {p.name: sha(p) for p in sorted(payload.iterdir())}}, indent=2) + '\n')
    shutil.copy2(str(OLD / 'collect_serial.py'), str(run / 'collect_serial.py'))
    new_guard_sha = sha(payload / 'board_guard.py')
    prefix = "import hashlib\nfrom pathlib import Path\np=Path(%r)\ns=p.read_bytes()\nassert hashlib.sha256(s).hexdigest()==%r\nexec(compile(s,str(p),'exec'))\n" % (work + '/candidate-stage/board_guard.py', new_guard_sha)
    ordered = []

    def save(phase, bodies, pre=prefix, timeout=180):
        manifest = []
        for name, body in bodies:
            code = pre + body
            (sources / (phase + '.' + name + '.py')).write_text(code)
            manifest.append({'id': name, 'command': wire(code), 'timeout': timeout})
        (run / (phase + '.commands.json')).write_text(json.dumps(manifest, indent=2) + '\n')
        ordered.append(phase)

    backup = '''guard(%r,%r)
import shutil
WORK.mkdir(exist_ok=False);b=WORK/'baseline';b.mkdir()
paths=['/usr/bin/dfx-mgrd','/usr/bin/dfx-mgr-client','/lib/systemd/system/dfx-mgr.service','/etc/dfx-mgrd/daemon.conf','/etc/dfx-mgrd/default_firmware','/etc/vart.conf','/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko']
for p in paths:shutil.copy2(p,str(b/Path(p).name))
ko=Path('/home/root/kv260-m3-boardtest-20261003T021012Z/repaired-zocl.ko')
assert digest(ko)==%r
shutil.copy2(str(ko),str(WORK/'repaired-zocl.ko'))
(b/'state.json').write_text(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'parameters':PARAMS,'active':active_packages()}))
hashes={p:digest(p) for p in paths}
(b/'file-hashes.json').write_text(json.dumps(hashes,indent=2))
print('BACKUP '+json.dumps({'directory':str(b),'files':hashes}),flush=True)
snapshot('AFTER')
''' % (ORIGINAL, OFFICIAL, MODULE_SHA)
    save('02-backup', [('backup', backup)], pre=bootstrap)
    ordered.append('03-transfer')
    unpack = '''guard(%r,%r)
import tarfile
p=WORK/'candidate.tar.gz';assert digest(p)==%r
stage=WORK/'candidate-stage';stage.mkdir(exist_ok=False)
with tarfile.open(str(p),'r:gz') as tar:
 ms=tar.getmembers();assert len(ms)==5
 for m in ms:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  ps=Path(m.name).parts;assert len(ps)==2 and ps[0]=='kv260-dfx-watch-candidate'
  with (stage/ps[1]).open('xb') as f:f.write(tar.extractfile(m).read())
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=str(stage),check=True)
(stage/'dfx-mgrd').chmod(0o755)
assert digest(stage/'board_guard.py')==%r
exec(compile((stage/'board_guard.py').read_bytes(),'guard','exec'))
gate(%r,%r);manager_guard(False)
assert not OVERRIDE.exists() and not Path('/run/systemd/system/dfx-mgr.service.d').exists()
print('CANDIDATE_STAGE '+str(stage),flush=True)
''' % (ORIGINAL, OFFICIAL, archive_sha, new_guard_sha, ORIGINAL, OFFICIAL)
    save('04-unpack', [('unpack', unpack)], pre=bootstrap)
    save('05-remove-original', [('remove', "gate(%r,%r);manager_guard(False)\nsnapshot('BEFORE')\nsubprocess.run(['dfx-mgr-client','-remove'],check=True)\ngate(%r,None)\nassert not Path('/sys/bus/platform/devices/axi:zyxclmm_drm').exists()\nsnapshot('AFTER')\n" % (ORIGINAL, OFFICIAL, ORIGINAL))])
    dropin = '[Service]\nExecStart=\nExecStart=' + work + '/candidate-stage/dfx-mgrd\nExecStartPre=\nStandardOutput=file:' + work + '/candidate-manager.log\nStandardError=inherit\n'
    dropin_sha = hashlib.sha256(dropin.encode()).hexdigest()
    start = '''gate(%r,None);manager_guard(False)
snapshot('BEFORE')
subprocess.run(['rmmod','zocl'],check=True)
guard(None,None)
assert digest(WORK/'repaired-zocl.ko')==%r
subprocess.run(['insmod',str(WORK/'repaired-zocl.ko'),'enable_xgq_ert=1'],check=True)
gate(%r,None)
subprocess.run(['systemctl','stop','dfx-mgr.service'],check=True)
assert manager_pid()==0
assert not OVERRIDE.exists() and not OVERRIDE.parent.exists()
OVERRIDE.parent.mkdir()
with OVERRIDE.open('x') as f:f.write(%r)
assert digest(OVERRIDE)==%r
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start','dfx-mgr.service'],check=True)
wait_manager(True);gate(%r,%r)
assert watches()==5
print('CANDIDATE_STARTED '+json.dumps({'pid':manager_pid(),'exe':os.readlink('/proc/%%d/exe'%%manager_pid()),'kernel_watches':watches()}),flush=True)
snapshot('AFTER')
''' % (ORIGINAL, MODULE_SHA, REPAIRED, dropin, dropin_sha, REPAIRED, OFFICIAL)
    save('06-start-candidate', [('start', start)])

    def functional(phase, driver, app, candidate_manager):
        common = "gate(%r,%r);manager_guard(%r)\n" % (driver, app, candidate_manager)
        query = common + "subprocess.run(['env','XLNX_VART_FIRMWARE=/lib/firmware/xilinx/%s/%s.xclbin','xdputil','query'],check=True)\n" % (app, app)
        jpeg = common + "subprocess.run(['env','XLNX_VART_FIRMWARE=/lib/firmware/xilinx/%s/%s.xclbin','/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification','resnet18','/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'],cwd='/home/root/kv260-test-20261001',check=True)\n" % (app, app)
        save(phase, [('dpu_query', query), ('classification', jpeg)])

    functional('07-official-functional', REPAIRED, OFFICIAL, True)
    rescan = '''gate(%r,%r);manager_guard(True)
import time
before=watches();assert before==5
samples=[]
for i in range(1000):
 assert active_packages()==[(%r,0)]
 if (i+1) in (1,125,250,500,750,1000):
  n=watches();assert n==5;samples.append({'queries':i+1,'watches':n})
 time.sleep(.02)
manager_guard(True);gate(%r,%r)
print('QUERY_STRESS '+json.dumps({'queries':1000,'samples':samples,'manager_errors':manager_errors(),'log_bytes':(WORK/'candidate-manager.log').stat().st_size}),flush=True)
''' % (REPAIRED, OFFICIAL, OFFICIAL, REPAIRED, OFFICIAL)
    save('08-query-stress', [('queries', rescan)], timeout=300)
    directory = '''gate(%r,%r);manager_guard(True)
import time
probe=Path('/lib/firmware/xilinx/watch-probe-%s')
assert not probe.exists()
def listing():return subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True)
for i in range(50):
 probe.mkdir();(probe/'shell.json').write_text('{"shell_type":"PL_FLAT","num_pl_slots":1,"num_aie_slots":0}\\n')
 time.sleep(.05)
 assert probe.name in listing() and watches()==6
 assert active_packages()==[(%r,0)]
 (probe/'shell.json').unlink();probe.rmdir()
 time.sleep(.05)
 assert probe.name not in listing() and watches()==5
manager_guard(True);gate(%r,%r)
print('DIRECTORY_STRESS '+json.dumps({'cycles':50,'probe':str(probe),'probe_absent':not probe.exists(),'kernel_watches':watches(),'manager_errors':manager_errors()}),flush=True)
''' % (REPAIRED, OFFICIAL, stamp, OFFICIAL, REPAIRED, OFFICIAL)
    save('09-directory-stress', [('directories', directory)], timeout=240)
    cycle = '''gate(%r,%r);manager_guard(True)
snapshot('BEFORE')
for i in range(3):
 subprocess.run(['dfx-mgr-client','-remove'],check=True);gate(%r,None)
 subprocess.run(['dfx-mgr-client','-load',%r],check=True);gate(%r,%r)
 manager_guard(True)
 print('OFFICIAL_CYCLE '+json.dumps({'cycle':i+1,'active':active_packages(),'watches':watches()}),flush=True)
snapshot('AFTER')
''' % (REPAIRED, OFFICIAL, REPAIRED, OFFICIAL, REPAIRED, OFFICIAL)
    save('10-official-cycles', [('cycles', cycle)], timeout=300)
    functional('11-official-after-cycles', REPAIRED, OFFICIAL, True)
    m3 = "gate(%r,%r);manager_guard(True)\nsnapshot('BEFORE')\nsubprocess.run(['dfx-mgr-client','-remove'],check=True);gate(%r,None)\nsubprocess.run(['dfx-mgr-client','-load',%r],check=True);gate(%r,%r)\nmanager_guard(True)\nsnapshot('AFTER')\n" % (REPAIRED, OFFICIAL, REPAIRED, M3, REPAIRED, M3)
    save('12-load-m3', [('load', m3)])
    functional('13-m3-functional', REPAIRED, M3, True)
    restore_service = '''gate(%r,%r);manager_guard(True)
snapshot('BEFORE')
subprocess.run(['dfx-mgr-client','-remove'],check=True);gate(%r,None)
assert not manager_errors()
subprocess.run(['systemctl','stop','dfx-mgr.service'],check=True);assert manager_pid()==0
assert digest(OVERRIDE)==%r
assert [p.name for p in OVERRIDE.parent.iterdir()]==[OVERRIDE.name]
OVERRIDE.unlink();OVERRIDE.parent.rmdir()
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start','dfx-mgr.service'],check=True)
wait_manager(False);gate(%r,%r)
assert not manager_errors()
print('ORIGINAL_SERVICE_RESTORED '+json.dumps({'pid':manager_pid(),'candidate_log_bytes':(WORK/'candidate-manager.log').stat().st_size,'candidate_log_sha256':digest(WORK/'candidate-manager.log')}),flush=True)
snapshot('AFTER')
''' % (REPAIRED, M3, REPAIRED, dropin_sha, REPAIRED, OFFICIAL)
    save('14-restore-service', [('restore', restore_service)])
    restore_driver = '''gate(%r,%r);manager_guard(False)
snapshot('BEFORE')
subprocess.run(['dfx-mgr-client','-remove'],check=True);gate(%r,None)
subprocess.run(['rmmod','zocl'],check=True);guard(None,None)
subprocess.run(['modprobe','zocl','enable_xgq_ert=1'],check=True);gate(%r,None)
subprocess.run(['dfx-mgr-client','-load',%r],check=True);gate(%r,%r)
manager_guard(False)
snapshot('AFTER')
''' % (REPAIRED, OFFICIAL, REPAIRED, ORIGINAL, OFFICIAL, ORIGINAL, OFFICIAL)
    save('15-restore-driver', [('restore', restore_driver)])
    functional('16-restored-functional', ORIGINAL, OFFICIAL, False)
    final = '''gate(%r,%r);manager_guard(False)
assert not OVERRIDE.exists() and not OVERRIDE.parent.exists()
assert not manager_errors()
print('FINAL '+json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'active':active_packages(),'driver':Path('/sys/module/zocl/srcversion').read_text().strip(),'parameters':PARAMS,'manager_pid':manager_pid(),'manager_exe':os.readlink('/proc/%%d/exe'%%manager_pid()),'kernel_watches':watches(),'original_files':{p:digest(p) for p in INPUTS},'candidate_log_bytes':(WORK/'candidate-manager.log').stat().st_size,'candidate_log_sha256':digest(WORK/'candidate-manager.log')}),flush=True)
snapshot('AFTER')
''' % (ORIGINAL, OFFICIAL)
    save('17-final-state', [('state', final)])
    save('18-candidate-log', [('log', "gate(%r,%r);manager_guard(False)\nsubprocess.run(['cat',str(WORK/'candidate-manager.log')],check=True)\n" % (ORIGINAL, OFFICIAL))], timeout=600)
    sender = (OLD / 'uart_sender_source.py').read_text()
    replacements = {
        "source = Path('/home/ghmd/kv260-m3-axilite-20261002/downloads/kv260-benchmark-b4096-m3-test-bundle.tar.gz')": 'source = Path(%r)' % str(archive),
        "expected = '589e971480d4cdd2a697c8f33253a7ada4acc38cf800c3424b385061a5244702'": 'expected = %r' % archive_sha,
        "dest = '/home/root/kv260-m3-boardtest-20261003T021012Z/m3-bundle.tar.gz'": 'dest = %r' % (work + '/candidate.tar.gz'),
        "'07-transfer-bundle.serial.raw'": "'03-transfer.serial.raw'",
        "'07-transfer-bundle.result.json'": "'03-transfer.result.json'",
        "tmp=p.with_suffix('.jpg.partial')": "tmp=p.with_suffix('.tar.gz.partial')",
        'Board receiver ready; transferring sealed M3 test bundle': 'Board receiver ready; transferring reviewed DFX candidate bundle',
    }
    for old, new in replacements.items():
        assert sender.count(old) == 1, repr(old)
        sender = sender.replace(old, new)
    begin = sender.index(" listing=p.parent/'samoyed.list'")
    end = sender.index(" os.write(1,('REPAIR_PACKAGE_DONE", begin)
    sender = sender[:begin] + sender[end:]
    compile(sender, 'sender', 'exec')
    (run / 'transfer_candidate.py').write_text(sender)
    manifest_hashes = {p.name: sha(p) for p in run.glob('*.commands.json')}
    source_hashes = {str(p.relative_to(run)): sha(p) for p in sources.iterdir()}
    prepared = {'run': str(run), 'board_work_directory': work, 'override_path': override,
        'override_sha256': dropin_sha, 'ordered_phases': ordered, 'manifest_hashes': manifest_hashes,
        'source_hashes': source_hashes, 'collector_sha256': sha(run / 'collect_serial.py'),
        'transfer_sha256': sha(run / 'transfer_candidate.py'), 'test_archive': {'path': str(archive), 'sha256': archive_sha, 'bytes': archive.stat().st_size},
        'candidate': candidate, 'input_hashes': inputs, 'boot_id': inventory['boot_id']}
    (run / 'preparation.json').write_text(json.dumps(prepared, indent=2) + '\n')
    (ROOT / 'evidence/BOARD_VALIDATION_RUN').write_text(str(run) + '\n')
    print(json.dumps({'run': str(run), 'archive_bytes': archive.stat().st_size, 'archive_sha256': archive_sha, 'phases': len(ordered)}))


if __name__ == '__main__':
    main()
