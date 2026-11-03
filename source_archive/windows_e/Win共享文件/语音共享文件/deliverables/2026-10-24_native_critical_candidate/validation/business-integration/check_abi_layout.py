"""Check every ctypes field offset against the current C v2 header only.

Compiles/runs a host layout printer. No DSO, model, VART or device is loaded.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'candidate/aura'))
import ctypes as C
from board.vision.native_binding import Report,TensorInfo,Buffer,Recovery,State,Seed,Ack

header=root.parent/'schedule-integration/native_bridge.h'
types={'AuraNativeReport':Report,'AuraTensorInfo':TensorInfo,'AuraBuffer':Buffer,
       'AuraRecoveryState':Recovery,'AuraNativeState':State,'AuraNativeSeed':Seed,'AuraNativeAck':Ack}
lines=['#include "native_bridge.h"','#include <cstddef>','#include <iostream>','int main(){']
for name,structure in types.items():
    lines.append('std::cout << "'+name+' sizeof " << sizeof('+name+') << "\\n";')
    for field,_ in structure._fields_:
        lines.append('std::cout << "'+name+' '+field+' " << offsetof('+name+','+field+') << "\\n";')
lines.append('}')
report={'scope':'host C header sizes and every field offset; no DSO/model/device',
        'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),
        'binding_sha256':hashlib.sha256((root/'candidate/aura/board/vision/native_binding.py').read_bytes()).hexdigest()}
with tempfile.TemporaryDirectory(prefix='aura-business-abi-') as directory:
    source=Path(directory)/'layout.cpp';binary=Path(directory)/'layout'
    source.write_text('\n'.join(lines)+'\n')
    compiled=subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',
        '-I'+str(header.parent),str(source),'-o',str(binary)],capture_output=True,text=True)
    report['compile_exit_code']=compiled.returncode;report['compile_stderr']=compiled.stderr
    if compiled.returncode==0:
        run=subprocess.run([str(binary)],capture_output=True,text=True)
        report['run_exit_code']=run.returncode;report['run_stderr']=run.stderr
        native={}
        for line in run.stdout.splitlines():
            name,field,value=line.split();native.setdefault(name,{})[field]=int(value)
        python={name:{'sizeof':C.sizeof(structure),**{field:getattr(structure,field).offset
                    for field,_ in structure._fields_}} for name,structure in types.items()}
        report['native']=native;report['ctypes']=python
        report['passed']=run.returncode==0 and native==python
    else:report['passed']=False
(root/'abi-layout-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('native','ctypes')},indent=2))
raise SystemExit(0 if report['passed'] else 1)
