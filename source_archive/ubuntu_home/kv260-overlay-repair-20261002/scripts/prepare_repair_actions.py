#!/usr/bin/env python3
"""Prepare one-action UART manifests with board, driver and client guards."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    run = Path(sys.argv[1]).resolve()
    meta = json.loads((run / "run.json").read_text())
    state = json.loads((run / "02-state.drivers_and_parameters.output").read_text())
    work = meta["board_work_directory"]
    original = "0991D1B457855C8987936E6"
    patched = "9BDC942A6014BCCBD1DCB78"
    archive_info = json.loads((ROOT / "bundle/archive_manifest.json").read_text())
    assert state["root_device"] == "mmcblk1p2" and state["loaded_srcversion"] == original
    params = state["zocl_parameters"]
    module_args = [k + "=" + value for k, value in sorted(params.items())]
    # The live IKCONFIG already matched byte for byte; saved boot_id guards
    # subsequent actions against a different kernel boot without long UART lines.
    guard = '''import os,json,hashlib,subprocess,re
from pathlib import Path
WORK=Path(%r)
ORIGINAL_SHA='215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d'
PARAMS=%r
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def active_packages():
 text=subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True)
 result=[]
 for line in text.splitlines():
  fields=line.split()
  if fields and re.fullmatch(r'-?\\d+,?',fields[-1]):
   slot=int(fields[-1].rstrip(','))
   if slot!=-1: result.append((fields[0],slot))
 return result
def guard(expected,app):
 assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2','Unexpected root/kernel'
 assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100','Wrong test card'
 dev=os.stat('/').st_dev
 assert Path('/sys/dev/block/%%d:%%d'%%(os.major(dev),os.minor(dev))).resolve().name=='mmcblk1p2','Wrong root partition'
 assert digest('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko')==ORIGINAL_SHA,'Original module changed'
 if (WORK/'baseline/state.json').exists():
  saved=json.loads((WORK/'baseline/state.json').read_text())
  assert saved['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'Boot changed'
 m=Path('/sys/module/zocl')
 if expected is None: assert not m.exists(),'ZOCL unexpectedly loaded'
 else:
  assert (m/'srcversion').read_text().strip()==expected,'Wrong loaded module'
  assert int((m/'refcnt').read_text())==0 and not list((m/'holders').iterdir()),'ZOCL busy'
  assert {p.name:p.read_text().strip() for p in (m/'parameters').iterdir()}==PARAMS,'Module parameters changed'
 nodes={'/dev/dri/card1','/dev/dri/renderD128'}
 for p in Path('/sys/class/drm').iterdir():
  module=p/'device/driver/module'
  if module.exists() and str(module.resolve())=='/sys/module/zocl': nodes.add('/dev/dri/'+p.name)
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit(): continue
  try:
   for fd in (proc/'fd').iterdir():
    try: target=os.readlink(fd).split(' (deleted)')[0]
    except OSError: continue
    assert target not in nodes,'DRM client still open: PID '+proc.name
  except (FileNotFoundError,PermissionError): continue
 wanted=[] if app is None else [(app,0)]
 assert active_packages()==wanted,'Unexpected active packages'
def snapshot(label):
 print(label+'_UPTIME '+Path('/proc/uptime').read_text().strip(),flush=True)
 print(label+'_ACTIVE '+json.dumps(active_packages()),flush=True)
 print(label+'_DMESG_BEGIN',flush=True)
 subprocess.run(['dmesg'],check=True)
 print(label+'_DMESG_END',flush=True)
''' % (work, params)

    def command(code):
        compile(code, "prepared_board_action", "exec")
        encoded = base64.b64encode(gzip.compress(code.encode(), mtime=0)).decode()
        decoder = "import base64,gzip;exec(gzip.decompress(base64.b64decode(" + repr(encoded) + ")))"
        result = "python3 -B -c " + shlex.quote(decoder)
        assert len(result) * 4 / 3 + 850 < 3900, "UART shell line would exceed safe length: %d command bytes" % len(result)
        return result

    guard_sha = hashlib.sha256(guard.encode()).hexdigest()
    (run / "board_guard.py").write_text(guard)
    guard_loader = "import hashlib\nfrom pathlib import Path\np=Path(%r)\ns=p.read_bytes()\nassert hashlib.sha256(s).hexdigest()==%r,'Guard file changed'\nexec(compile(s,str(p),'exec'))\n" % (work + "/baseline/board_guard.py", guard_sha)

    def save(phase, action, timeout=180, prefix=None):
        path = run / (phase + ".commands.json")
        content = json.dumps([{"id": phase.split('-', 1)[1], "command": command((guard_loader if prefix is None else prefix) + action), "timeout": timeout}], indent=2) + "\n"
        if path.exists():
            if path.read_text() != content:
                raise RuntimeError("Refusing to overwrite differing phase: " + phase)
            return
        path.write_text(content)

    backup = '''guard(%r,'kv260-benchmark-b4096')
import shutil,tarfile
WORK.mkdir(exist_ok=False)
b=WORK/'baseline';b.mkdir()
for src,name in [('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko','original-zocl.ko'),('/proc/config.gz','config.gz'),('/etc/vart.conf','vart.conf'),('/sys/firmware/fdt','boot-fdt.dtb')]:
 p=Path(src)
 if p.exists(): (b/name).write_bytes(p.read_bytes())
(b/'dmesg-before.output').write_bytes(subprocess.check_output(['dmesg']))
(b/'state.json').write_text(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'parameters':PARAMS,'original_sha256':digest(b/'original-zocl.ko'),'active':active_packages(),'uptime':Path('/proc/uptime').read_text()},indent=2))
print(json.dumps({'backup':str(b),'original_module_sha256':digest(b/'original-zocl.ko')},indent=2),flush=True)
''' % original
    save("05-save-original", backup, prefix=guard)
    snapshots = '''guard(%r,'kv260-benchmark-b4096')
import tarfile
b=WORK/'baseline'
assert not (b/'official-firmware.tar.gz').exists() and not (b/'live-device-tree.tar.gz').exists()
with tarfile.open(str(b/'official-firmware.tar.gz'),'w:gz') as tar:
 for p in sorted(Path('/lib/firmware/xilinx/kv260-benchmark-b4096').iterdir()):
  assert p.is_file() and not p.is_symlink(),'Unexpected firmware member'
  tar.add(str(p),arcname=p.name,recursive=False)
with tarfile.open(str(b/'live-device-tree.tar.gz'),'w:gz') as tar:
 base=Path('/proc/device-tree').resolve()
 for p in sorted(base.rglob('*')):
  if p.is_file() and not p.is_symlink(): tar.add(str(p),arcname=str(p.relative_to(base)),recursive=False)
records={p.name:digest(p) for p in sorted(b.iterdir()) if p.is_file()}
(b/'manifest.json').write_text(json.dumps(records))
print(json.dumps(records),flush=True)
''' % original
    save("05b-save-live-snapshots", snapshots, prefix=guard)
    install_guard = "G=%r\nexec(compile(G,'reviewed_guard','exec'))\nguard(%r,'kv260-benchmark-b4096')\nassert digest(WORK/'baseline/original-zocl.ko')==ORIGINAL_SHA\np=WORK/'baseline/board_guard.py'\nwith p.open('xb') as f:f.write(G.encode())\nassert digest(p)==%r\nprint('SAVED_GUARD '+digest(p),flush=True)\n" % (guard,original,guard_sha)
    save("05c-save-action-guard", install_guard, prefix="")
    unpack = '''guard(%r,'kv260-benchmark-b4096')
import tarfile
assert digest(WORK/'baseline/original-zocl.ko')==ORIGINAL_SHA
archive=WORK/'candidate.tar.gz'
assert digest(archive)==%r,'Transferred archive SHA mismatch'
stage=WORK/'candidate-stage';stage.mkdir(exist_ok=False)
with tarfile.open(str(archive),'r:gz') as tar:
 members=tar.getmembers()
 assert len(members)==6,'Wrong archive member count'
 for m in members:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts,'Unsafe member'
  parts=Path(m.name).parts
  assert len(parts)==2 and parts[0]=='kv260-zocl-reference-repair-20261002','Unexpected archive path'
  with (stage/parts[1]).open('xb') as f: f.write(tar.extractfile(m).read())
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=str(stage),check=True)
assert digest(stage/'zocl.ko')=='5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412','Candidate module hash differs'
subprocess.run(['modinfo',str(stage/'zocl.ko')],check=True)
print('CANDIDATE_STAGE '+str(stage),flush=True)
''' % (original, archive_info["sha256"])
    save("07-unpack-candidate", unpack)

    def remove(phase, expected):
        save(phase, "guard(%r,'kv260-benchmark-b4096')\nsnapshot('BEFORE')\nsubprocess.run(['dfx-mgr-client','-remove'],check=True)\nguard(%r,None)\nassert not Path('/sys/bus/platform/devices/axi:zyxclmm_drm').exists(),'ZOCL device remains registered'\nsnapshot('AFTER')\n" % (expected, expected))

    remove("08-remove-old-app", original)
    save("09-unload-original-module", "guard(%r,None)\nsnapshot('BEFORE')\nsubprocess.run(['rmmod','zocl'],check=True)\nguard(None,None)\nsnapshot('AFTER')\n" % original)
    save("10-load-repaired-module", "guard(None,None)\np=WORK/'candidate-stage/zocl.ko'\nassert digest(p)=='5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412'\nsubprocess.run(['insmod',str(p)]+%r,check=True)\nguard(%r,None)\nsnapshot('AFTER')\n" % (module_args, patched))
    for cycle in range(1,4):
        save("c%d-load-official" % cycle, "guard(%r,None)\nsnapshot('BEFORE')\nsubprocess.run(['dfx-mgr-client','-load','kv260-benchmark-b4096'],check=True)\nguard(%r,'kv260-benchmark-b4096')\nassert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'\nassert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\\0')==b'kv260-benchmark-b4096.bit.bin'\nsnapshot('AFTER')\n" % (patched,patched))
        functional = json.loads((run / "03-baseline-functional.commands.json").read_text())
        (run / ("c%d-functional.commands.json" % cycle)).write_text(json.dumps(functional,indent=2)+"\n")
        remove("c%d-remove-official" % cycle,patched)
    perf = json.loads((run / "04-baseline-performance.commands.json").read_text())
    (run / "11-repaired-performance.commands.json").write_text(json.dumps(perf,indent=2)+"\n")
    save("r1-unload-repaired-module", "guard(%r,None)\nsnapshot('BEFORE')\nsubprocess.run(['rmmod','zocl'],check=True)\nguard(None,None)\nsnapshot('AFTER')\n" % patched)
    save("r2-restore-original-module", "guard(None,None)\nassert digest(WORK/'baseline/original-zocl.ko')==ORIGINAL_SHA\nsubprocess.run(['modprobe','zocl']+%r,check=True)\nguard(%r,None)\nsnapshot('AFTER')\n" % (module_args,original))
    save("r3-restore-official-app", "guard(%r,None)\nsnapshot('BEFORE')\nsubprocess.run(['dfx-mgr-client','-load','kv260-benchmark-b4096'],check=True)\nguard(%r,'kv260-benchmark-b4096')\nsnapshot('AFTER')\n" % (original,original))
    (run / "r4-restored-functional.commands.json").write_text((run / "03-baseline-functional.commands.json").read_text())
    (run / "r5-final-state.commands.json").write_text((run / "02-state.commands.json").read_text())
    print(json.dumps({"prepared_run":str(run),"board_work_directory":work,"module_parameters":params,"executed_on_board":False}))


if __name__ == "__main__":
    main()
