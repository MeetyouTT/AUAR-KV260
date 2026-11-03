"""Archive the exact stale audit temp and start the unchanged, unconsumed owner once."""
import fcntl,hashlib,json,os,subprocess
from pathlib import Path
BOOT='e004cfbf-fdde-433d-b372-c8e420db2699'
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
ROOT=Path('/home/root/aura-hdmi-camera-recovery-20261029')/BOOT
STALE=OPS/'pan-face-edge-v5/native-operator-v1/recovery-audit-1332.json.1332'
SHA='880000de0c1b36754a1386b3e368d4096b20ed5fe4913cb9122306a75bce3f8c'
MARKERS=Path('/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9/state/kernel-history')
CP=Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def props(unit):
    t=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus','-p','ExecMainPID'],text=True,timeout=3)
    return dict(v.split('=',1) for v in t.splitlines() if '=' in v)
def save(name,d):
    with (ROOT/name).open('x') as f:json.dump(d,f,indent=2);f.flush();os.fsync(f.fileno())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
op=(OPS/'operation.lock').open('a+');fcntl.flock(op,fcntl.LOCK_EX|fcntl.LOCK_NB)
c=props('aura-camera-ui.service');g=props('aura-avatar-ui.service');x=props('xserver-nodm.service')
assert c['MainPID']=='0' and c['ActiveState']=='failed' and c['ExecMainPID']=='1332' and c['ExecMainStatus']=='1'
assert g['MainPID']=='1294' and x['MainPID']=='1075'
assert not Path('/proc/1332').exists() and Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
assert not (MARKERS/('kernel-boot-'+BOOT+'.consumed')).exists()
assert not (OPS/('native-run-'+BOOT+'-1332')/'UNSAFE_OWNER_RETAINED.json').exists()
assert digest(CP)=='5405e52f8e12d5eb1c47a0707bab6b0a340823e8384611dc6f731698261ce548'
assert digest(OPS/'pan-face-edge-v5/native-operator-v1/identity_recovery.py')=='64831498d8497c2087b3bb1543367e8cc1917ca131694000884f2d58e60990f7'
assert STALE.is_file() and not STALE.is_symlink() and digest(STALE)==SHA
with open('/run/aura-person-dpu.lock','r') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    destination=ROOT/STALE.name
    save('before.json',{'boot':BOOT,'service':c,'source':str(STALE),'sha256':SHA,'checkpoint_sha256':digest(CP),'current_boot_consumed':False,'unsealed_previous_boot':'50b4fef1-9748-43c7-92bf-3040db8c994e','history_limit':'No final checkpoint was captured for that abrupt power loss; retained checkpoint comes from c006a771. No counters invented or removed.'})
    os.link(STALE,destination,follow_symlinks=False)
    assert digest(destination)==SHA and STALE.stat().st_ino==destination.stat().st_ino
    STALE.unlink()
    for folder in [ROOT,STALE.parent]:
        fd=os.open(str(folder),os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    save('archived.json',{'archive':str(destination),'sha256':SHA,'old_path_absent':not STALE.exists(),'checkpoint_unchanged':digest(CP)=='5405e52f8e12d5eb1c47a0707bab6b0a340823e8384611dc6f731698261ce548'})
assert not (MARKERS/('kernel-boot-'+BOOT+'.consumed')).exists()
subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=4)
print(json.dumps({'archive':str(destination),'archived_sha256':SHA,'start_requested':True,'start_count':1,'business_source_changed':False,'checkpoint_changed':False,'markers_removed':False,'journal':str(ROOT)}))
