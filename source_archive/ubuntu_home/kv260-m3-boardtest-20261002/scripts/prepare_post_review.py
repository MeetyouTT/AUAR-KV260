#!/usr/bin/env python3
"""Prepare a post-recovery read-only firmware and manager-log review."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import sys


def main():
    run=Path(sys.argv[1]).resolve()
    text=(run/'action_sources/25-final-state.final_kernel.py').read_text()
    boundary="gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')\ncapture('AFTER')"
    assert text.endswith(boundary+'\n')
    prefix=text[:-len(boundary+'\n')]
    gate="gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')\n"
    entries=[('installed_hashes',prefix+gate+'''p=WORK/'m3-stage/provenance/runtime_manifest.json'
for item in json.loads(p.read_text())['runtime_files']:
 path='/'+item['path'];actual=digest(path);assert actual==item['sha256']
 print(json.dumps({'path':path,'sha256':actual}),flush=True)
'''),('manager_logs',prefix+gate+'''units_text=subprocess.check_output(['systemctl','list-units','--all','--plain','--no-pager'],text=True)
units=[line.split()[0] for line in units_text.splitlines() if 'dfx' in line.lower() and '.service' in line]
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  comm=(p/'comm').read_text().strip()
  if comm.startswith('dfx-mgr'):processes.append({'pid':int(p.name),'comm':comm,'cgroup':(p/'cgroup').read_text()})
 except OSError:continue
print('MANAGER_DISCOVERY '+json.dumps({'units':units,'processes':processes}),flush=True)
for unit in units:
 print('UNIT_JOURNAL_BEGIN '+unit,flush=True)
 subprocess.run(['journalctl','-u',unit,'--no-pager','-o','short-monotonic'],check=True)
 print('UNIT_JOURNAL_END '+unit,flush=True)
for process in processes:
 print('PID_JOURNAL_BEGIN '+str(process['pid']),flush=True)
 subprocess.run(['journalctl','--no-pager','-o','short-monotonic','_PID='+str(process['pid'])],check=True)
 print('PID_JOURNAL_END '+str(process['pid']),flush=True)
''')]
    manifest=[]
    for ident,code in entries:
        compile(code,'post_recovery_readonly','exec')
        path=run/'action_sources'/('26-post-review.'+ident+'.py')
        assert not path.exists();path.write_text(code)
        blob=base64.b64encode(gzip.compress(code.encode(),mtime=0)).decode()
        command='python3 -B -c '+shlex.quote('import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(blob)+')))')
        assert len(command)*4/3+850<3900
        manifest.append({'id':ident,'command':command,'timeout':240})
    path=run/'26-post-review.commands.json';assert not path.exists()
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    (run/'post_review_preparation.json').write_text(json.dumps({
        'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_hashes':{ident:hashlib.sha256(code.encode()).hexdigest() for ident,code in entries},
        'scope':'Only after original baseline recovery; no MMIO, firmware changes or app switching'},indent=2)+'\n')
    print(json.dumps({'prepared_readonly_commands':len(entries),'execute_only_after_recovery':True}))


if __name__=='__main__':
    main()
