"""Local-only frozen-source checks. Never contacts UART, a DPU or a model."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parent
sources=['native_bridge.cpp','native_bridge.h','native_lease_v2.hpp','native_recovery.hpp','tensor_layout.hpp',
         'test_recovery_integration.cpp','test_bridge_v2.cpp','test_legacy_v2.cpp','test_abi_sizes.cpp']
pins={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in sources}
report={'scope':'LOCAL_ONLY_FAKE_CALLBACKS_FAKE_VART_NO_BOARD_OR_MODEL_JOBS',
        'started_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':pins,'checks':{},
        'physical_board_contact':False,'real_dpu_jobs':0}

def command(name,argv,timeout=90,parse=False):
    result=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=timeout)
    item={'argv':argv,'exit_code':result.returncode,'stderr':result.stderr[-12000:]}
    if parse and result.returncode==0:item['result']=json.loads(result.stdout)
    else:item['stdout']=result.stdout[-12000:]
    report['checks'][name]=item
    if result.returncode:raise RuntimeError(name+' failed: '+result.stderr[-1000:])
    return item

try:
    base=['nice','-n','10','g++','-std=c++17','-Wall','-Wextra','-Werror','-pthread']
    for label,source in [('gate','test_recovery_integration.cpp'),('legacy','test_legacy_v2.cpp'),('bridge','test_bridge_v2.cpp')]:
        flags=['-Ifake-include'] if label=='bridge' else []
        libs=['-ldl'] if label=='bridge' else []
        command(label+'_compile',base+['-O2']+flags+[source]+libs+['-o','test_'+label+'_final'])
        command(label+'_run',['./test_'+label+'_final'],parse=True)
    for label,source in [('gate','test_recovery_integration.cpp'),('bridge','test_bridge_v2.cpp')]:
        flags=['-Ifake-include'] if label=='bridge' else []
        libs=['-ldl'] if label=='bridge' else []
        command(label+'_san_compile',base+['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']+
                flags+[source]+libs+['-o','test_'+label+'_san_final'])
        command(label+'_san_run',['./test_'+label+'_san_final'],parse=True)
    command('sizes_compile',base+['test_abi_sizes.cpp','-o','test_abi_sizes_final'])
    command('sizes',['./test_abi_sizes_final'],parse=True)
    command('matched_target_headers_syntax',base+['-fsyntax-only','-isystem','../matched-include','native_bridge.cpp'])
    compiler='/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-g++'
    command('aarch64_compiler_version',[compiler,'--version'])
    command('aarch64_object',['nice','-n','10',compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-pthread','-fPIC','-isystem','../matched-include','-c','native_bridge.cpp','-o','native_bridge.v2.aarch64.o'])
    report['aarch64_object_sha256']=hashlib.sha256((root/'native_bridge.v2.aarch64.o').read_bytes()).hexdigest()
    report['sources_unchanged']=all(hashlib.sha256((root/n).read_bytes()).hexdigest()==pin for n,pin in pins.items())
    assert report['sources_unchanged']
    report['passed']=True
except BaseException as error:
    report['passed']=False;report['failure']=type(error).__name__+': '+str(error)
finally:
    report['finished_utc']=datetime.now(timezone.utc).isoformat()
    (root/'checks-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'checks':list(report['checks']),
                  'failure':report.get('failure'),'real_dpu_jobs':0}))
raise SystemExit(0 if report['passed'] else 1)
