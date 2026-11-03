#!/usr/bin/env python3
"""Install and load the reviewed standalone PWM image, verify idle; never START."""
import base64
import datetime
import gzip
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
from connector_mapping import audit

preparation = json.loads((ROOT / 'PREPARATION_STATUS.json').read_text())
pin_review = audit()
if not pin_review['passed']:
    raise SystemExit('Connector mapping rejected: intended ' +
                     pin_review['intended_physical_pin'] + ' requires ' +
                     pin_review['expected_fpga_pin'] + '; built pins ' +
                     repr(pin_review['built_fpga_pins']) + ' map to ' +
                     repr(pin_review['actual_physical_pins']))
if not preparation['ready_for_upload']:
    raise SystemExit('Diagnostic package is not ready for deployment')
physical = json.loads((ROOT / 'PHYSICAL_CONNECTION.json').read_text())
if physical['pin'] != pin_review['intended_physical_pin'] or not physical['confirmed']:
    raise SystemExit('The intended connector pin has not been confirmed')
if physical['connection'] not in ('empty', 'measurement_only'):
    raise SystemExit('The intended pin must be unloaded or connected only to measuring instruments')
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
stage = json.loads((ROOT / 'CURRENT_BOARD_STAGE.json').read_text())
assert stage['complete'] and not stage['pl_loaded'] and not stage['start_sent']
archive = stage['destination']
expected_hash = stage['sha256']
COMMON = r'''
import base64,hashlib,json,os,re,shutil,subprocess,sys,tarfile,time
from pathlib import Path
archive=Path(sys.argv[1]);expected_hash=sys.argv[2];package=archive.parent/'unpacked'
APP='aura-pin3-pwm';OFFICIAL='kv260-benchmark-b4096';FW='aura_pin3_pwm.bit.bin'
def run(argv,timeout=45):
 p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(str(argv)+': '+p.stdout)
 return p.stdout
def rows():
 result={}
 for line in run(['xmutil','listapps'],12).splitlines():
  f=line.split()
  if len(f)==6 and f[1] in ('XRT_FLAT','PL_FLAT'):
   result[f[0]]={'type':f[1],'slot':f[-1]}
 return result
def active():return [k for k,v in rows().items() if v['slot'].rstrip(',')=='0']
def fw():return Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
def state():return Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()
def guard():
 assert os.uname().machine=='aarch64' and os.geteuid()==0
 assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
 assert any(x.split()[:2]==['/dev/mmcblk1p2','/'] for x in Path('/proc/mounts').read_text().splitlines())
 assert run(['systemctl','is-active','dfx-mgr']).strip()=='active'
def no_clients():
 assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0','ZOCL has clients'
 for p in Path('/sys/kernel/debug/dri').glob('*/clients'):
  if p.parent.name!='0':assert len(p.read_text().splitlines())<=1,'Accelerator DRM client present'
def check_official_hashes():
 original=json.loads((archive.parent/'original-state.json').read_text())
 for p,h in original['firmware_hashes'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
 return original
guard()
'''
PREPARE = r'''
assert active()==[OFFICIAL] and fw()==OFFICIAL+'.bit.bin' and state()=='operating'
no_clients()
assert archive.is_file() and hashlib.sha256(archive.read_bytes()).hexdigest()==expected_hash
files=sorted(Path('/lib/firmware/xilinx/'+OFFICIAL).iterdir())
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
assert hashes['/lib/firmware/xilinx/'+OFFICIAL+'/'+OFFICIAL+'.bit.bin']=='7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f'
result={'active':active(),'firmware':fw(),'fpga_state':state(),'firmware_hashes':hashes,
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'vart_conf_b64':base64.b64encode(Path('/etc/vart.conf').read_bytes()).decode(),
 'all_dt_firmware_names':[p.read_bytes().rstrip(b'\0').decode() for p in Path('/proc/device-tree').rglob('firmware-name')]}
with (archive.parent/'original-state.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
'''
EXTRACT = r'''
assert active()==[OFFICIAL] and fw()==OFFICIAL+'.bit.bin'
check_official_hashes()
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected_hash
with tarfile.open(archive,'r:gz') as tar:
 entries=tar.getmembers();names=[x.name for x in entries]
 assert len(names)==len(set(names))==8
 manifest=json.loads(tar.extractfile('manifest.json').read())
 assert set(names)==set(manifest)|{'manifest.json'} and len(manifest)==7
 package.mkdir(exist_ok=False)
 for entry in entries:
  rel=Path(entry.name)
  assert entry.isfile() and not rel.is_absolute() and '..' not in rel.parts
  data=tar.extractfile(entry).read()
  if entry.name!='manifest.json':
   meta=manifest[entry.name]
   assert len(data)==meta['bytes'] and hashlib.sha256(data).hexdigest()==meta['sha256']
  p=package/rel;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(data)
  p.chmod(0o755 if entry.name=='board/mmio32' else 0o644)
identity=json.loads((package/'evidence/accessor_identity.json').read_text())
assert hashlib.sha256((package/'board/mmio32').read_bytes()).hexdigest()==identity['binary_sha256']
p=subprocess.run([str(package/'board/mmio32')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5)
assert p.returncode==2 and p.stderr.strip()=='usage: mmio32 inspect|start|stop|scratch',p.stderr
print(json.dumps({'unpacked':str(package),'files_verified':len(manifest),'accessor_runtime_without_MMIO':True}))
'''
INSTALL = r'''
assert active()==[OFFICIAL] and fw()==OFFICIAL+'.bit.bin'
check_official_hashes()
manifest=json.loads((package/'manifest.json').read_text())
src=package/'lib/firmware/xilinx'/APP;dest=Path('/lib/firmware/xilinx')/APP
assert set(p.name for p in src.iterdir())=={FW,'aura_pin3_pwm.dtbo','shell.json'}
assert json.loads((src/'shell.json').read_text())=={'shell_type':'PL_FLAT','num_pl_slots':1}
reuse=dest.exists()
if not reuse:dest.mkdir(exist_ok=False)
for name in [FW,'aura_pin3_pwm.dtbo','shell.json']:
 data=(src/name).read_bytes()
 if not reuse:
  with (dest/name).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  (dest/name).chmod(0o644)
 assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==manifest['lib/firmware/xilinx/'+APP+'/'+name]['sha256']
deadline=time.monotonic()+5
while APP not in rows() and time.monotonic()<deadline:time.sleep(.1)
assert rows()[APP]['type']=='PL_FLAT' and rows()[APP]['slot']=='-1'
assert active()==[OFFICIAL]
print(json.dumps({'installed':str(dest),'files_verified':3,'package':str(package),'active':active()}))
'''
UNLOAD = r'''
assert active()==[OFFICIAL] and fw()==OFFICIAL+'.bit.bin'
check_official_hashes();no_clients()
output=run(['xmutil','unloadapp'])
assert re.search(r'returns:\s*0\s*\(Ok\)',output),output
assert active()==[]
assert not list(Path('/sys/kernel/config/device-tree/overlays').iterdir())
assert not list(Path('/dev/dri').glob('renderD*'))
print(json.dumps({'official_unloaded':True,'output':output}))
'''
LOAD = r'''
assert active()==[] and rows()[APP]['type']=='PL_FLAT'
output=run(['xmutil','loadapp',APP])
assert 'loaded to slot 0' in output and 'Error' not in output,output
assert active()==[APP] and fw()==FW and state()=='operating'
assert len(list(Path('/sys/kernel/config/device-tree/overlays').iterdir()))==1
summary=Path('/sys/kernel/debug/clk/clk_summary').read_text()
clock_rows=[line.split() for line in summary.splitlines() if line.split() and line.split()[0]=='pl0_ref']
assert len(clock_rows)==1 and int(clock_rows[0][1])>0
rate=int(clock_rows[0][4]);assert abs(rate-99999001)<=99999001*.001
text=run(['python3','-B',str(package/'board/probe.py')],10);registers=json.loads(text)
expected={'ip_id':'0x50574d54','abi':'0x10000','build_id':'BUILD_ID_PLACEHOLDER','status':4,
 'period_ticks':1999980,'pulse_ticks':149999,'frames_left':0,'clock_hz':99999001,'run_frames':0,'pulse_us':1500}
assert registers==expected,registers
result={'active':active(),'firmware':fw(),'fpga_state':state(),'pl0_actual_hz':rate,
 'mode':'continuous','duty_percent':7.5,
 'registers':registers,'start_sent':False,'output_register_low':True,'load_output':output}
(archive.parent/'loaded-idle.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
'''
RESTORE = r'''
current=active()
assert current in ([],[APP],[OFFICIAL]),current
if current==[APP]:
 output=run(['xmutil','unloadapp'])
 assert re.search(r'returns:\s*0\s*\(Ok\)',output),output
 assert active()==[]
if active()==[]:
 output=run(['xmutil','loadapp',OFFICIAL])
 assert 'loaded to slot 0' in output and 'Error' not in output,output
assert active()==[OFFICIAL] and fw()==OFFICIAL+'.bit.bin' and state()=='operating'
original=check_official_hashes()
assert Path('/etc/vart.conf').read_bytes()==base64.b64decode(original['vart_conf_b64'])
print(json.dumps({'restored':True,'active':active(),'firmware':fw(),'fpga_state':state()}))
'''

tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT / 'evidence' / (tag + '-uart-load-idle')
out.mkdir(parents=True, exist_ok=False)
status = {'phase': 'uart-load-idle', 'complete': False, 'evidence': str(out),
          'physical_state': 'J2.3 diagnostic; external connection must be confirmed before loading; physical probe placement unverified',
          'archive': archive, 'commands': [], 'start_sent': False,
          'external_waveform_verified': False, 'candidate_active': False}
spec = importlib.util.spec_from_file_location('reviewed_uart', TRANSPORT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def execute(uart, label, source, timeout=60):
    source = COMMON + source
    build_id = json.loads((ROOT / 'evidence/source_identity.json').read_text())['build_id']
    source = source.replace('BUILD_ID_PLACEHOLDER', hex(int(build_id, 16)))
    (out / (label + '.py')).write_text(source)
    payload = base64.b64encode(gzip.compress(source.encode(), mtime=0)).decode()
    code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(payload) + ')))'
    command = 'python3 -B -c ' + shlex.quote(code) + ' ' + shlex.quote(archive) + ' ' + shlex.quote(expected_hash)
    rc, data, digest = uart.command(command, 'PWM_LOAD_' + label.upper(), timeout)
    (out / (label + '.output')).write_bytes(data)
    status['commands'].append({'label': label, 'rc': rc, 'sha256': digest})
    if rc:
        raise RuntimeError(label + ' failed: ' + data.decode(errors='replace'))
    print(json.dumps({'step': label, 'passed': True}), flush=True)
    return json.loads(data)


try:
    with (out / 'uart.raw').open('wb') as raw:
        uart = module.UART(raw)
        unload_started = False
        try:
            uart.connect()
            execute(uart, 'prepare', PREPARE)
            execute(uart, 'extract', EXTRACT)
            execute(uart, 'install', INSTALL)
            unload_started = True
            execute(uart, 'unload', UNLOAD)
            status['loaded_idle'] = execute(uart, 'load', LOAD)
            status['candidate_active'] = True
            status['complete'] = True
        except Exception:
            if unload_started and uart.shell_ready:
                status['restore_after_error'] = execute(uart, 'restore', RESTORE)
            raise
        finally:
            status['console_echo_restored'] = uart.close()
except Exception as exc:
    status['error'] = str(exc)
    raise
finally:
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    (ROOT / 'CURRENT_BENCH.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2))
