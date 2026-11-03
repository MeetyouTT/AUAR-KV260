"""Compile a host fixture and run actual CDLL/Candidate v2 binding tests."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parent
native=root.parent/'schedule-integration'
candidate=root.parent/'business-integration/candidate/aura'
names=['native_bridge.cpp','native_bridge.h','native_lease_v2.hpp','native_recovery.hpp','tensor_layout.hpp']
pins={str(native/n):hashlib.sha256((native/n).read_bytes()).hexdigest() for n in names}
pins.update({str(candidate/'board/vision'/n):hashlib.sha256((candidate/'board/vision'/n).read_bytes()).hexdigest()
             for n in ['native_binding.py','native_protection.py']})
pins.update({str(root/n):hashlib.sha256((root/n).read_bytes()).hexdigest()
             for n in ['fake_v2_dso.cpp','test_roundtrip.py','run_roundtrip.py']})
pins.update({str(p):hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted((native/'fake-include').rglob('*')) if p.is_file()})
report={'scope':'HOST_ACTUAL_CDLL_C_ABI_V2_FAKE_OWNER_FACTORY_VART_XIR_YOLO',
        'started_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':pins,
        'board_contact':False,'real_dpu_jobs':0,'passed':False}
with tempfile.TemporaryDirectory(prefix='aura-v2-abi-') as temporary:
    folder=Path(temporary)
    snapshot=folder/'source';snapshot.mkdir()
    for name in names:shutil.copy2(native/name,snapshot/name)
    shutil.copy2(root/'fake_v2_dso.cpp',snapshot/'fake_v2_dso.cpp')
    fake_include=native/'fake-include'
    command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-pthread','-shared','-fPIC',
             '-I'+str(fake_include),str(snapshot/'fake_v2_dso.cpp'),'-o',str(folder/'fake-only.so'),'-ldl']
    build=subprocess.run(command,capture_output=True,text=True,timeout=60)
    report.update(compile_argv=command,compile_exit=build.returncode,compile_stderr=build.stderr)
    if build.returncode==0:
        environment=dict(os.environ,AURA_ROUNDTRIP_DSO=str(folder/'fake-only.so'),
                         AURA_ROUNDTRIP_CANDIDATE=str(candidate),PYTHONDONTWRITEBYTECODE='1')
        test=subprocess.run([sys.executable,'-m','unittest','-v','test_roundtrip'],cwd=root,
                            env=environment,capture_output=True,text=True,timeout=30)
        report.update(test_exit=test.returncode,test_stdout=test.stdout,test_stderr=test.stderr,
                      tests=12)
        report['passed']=test.returncode==0
report['sources_unchanged']=all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in pins.items())
report['passed']=report['passed'] and report['sources_unchanged']
report['finished_utc']=datetime.now(timezone.utc).isoformat()
if (root/'result.json').exists():
    previous=json.loads((root/'result.json').read_text())
    token=hashlib.sha256(json.dumps(previous,sort_keys=True).encode()).hexdigest()[:12]
    archived=root/('result-prior-'+token+'.json')
    if not archived.exists():archived.write_text(json.dumps(previous,indent=2)+'\n')
(root/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
