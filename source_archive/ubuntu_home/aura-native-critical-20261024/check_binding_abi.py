"""Build/run a host fake dependency fixture; never load target VART or models."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
report = {'scope': 'host real ctypes/C++ ABI with fake XIR/VART; actual DPU jobs 0',
          'source_sha256': {n: hashlib.sha256((root/n).read_bytes()).hexdigest() for n in
              ('native_bridge.cpp','native_bridge.h','native_lease.hpp','native_binding.py',
               'fake_dso_fixture.cpp','test_binding_real_abi.py')}}
with tempfile.TemporaryDirectory(prefix='aura-fake-abi-') as temporary:
    folder = Path(temporary)
    # Keep the independently reviewed fake surface separate and unmodified.
    fake = (root/'independent-review/fake-include/fake_runtime.hpp').read_text()
    fake = fake.replace('return T(7);', 'return T(name_ == "sface_output" ? 5 : 7);')
    (folder/'fake_runtime.hpp').write_text(fake)
    include = root/'independent-review/fake-include'
    command = ['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-pthread','-shared','-fPIC',
               '-I'+str(folder),'-I'+str(include),str(root/'fake_dso_fixture.cpp'),
               '-o',str(folder/'fake-only.so'),'-ldl']
    build = subprocess.run(command,capture_output=True,text=True)
    report.update(compile_exit_code=build.returncode,compile_stderr=build.stderr)
    if build.returncode == 0:
        model = folder/'fake-model.tag';model.write_text('fake-only; no model data')
        (folder/'fake-manifest.json').write_text(json.dumps({
            'sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'partitions':[{
                'device':'DPU','fingerprint':'0x101000056010407',
                'inputs':[{'name':'sface_input','dims':[1,112,112,3],'dtype':'xint8','fix_point':7}],
                'outputs':[{'name':'sface_output','dims':[1,128],'dtype':'xint8','fix_point':5}]}]}))
        environment = dict(os.environ,AURA_HOST_FAKE_DSO=str(folder/'fake-only.so'))
        run = subprocess.run(['python3','-m','unittest','-v','test_binding_real_abi'],cwd=root,
            env=environment,capture_output=True,text=True,timeout=30)
        report.update(test_exit_code=run.returncode,test_stderr=run.stderr,test_stdout=run.stdout)
report['passed'] = report.get('compile_exit_code') == report.get('test_exit_code') == 0
(root/'binding-real-abi-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
