"""Parent-authorized compile only. Receives pinned constants in stdin prefix.

Writes exclusively DEST, never modifies the old build/production. No renderer,
EGL, model, device, GUI, service or benchmark is invoked. One low-priority TU.
"""
from pathlib import Path
import base64
import hashlib
import json
import os
import re
import shlex
import subprocess
import time


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(value,code):
    if not value:raise ValueError(code)
def symbols(path):
    raw=subprocess.check_output(['/usr/bin/nm','-D','--defined-only',str(path)],text=True,timeout=8)
    return sorted(line.split()[-1] for line in raw.splitlines() if line.split() and line.split()[-1].startswith('yuki_'))
def needed(path):
    raw=subprocess.check_output(['/usr/bin/readelf','-d',str(path)],text=True,timeout=8)
    return sorted(re.findall(r'\(NEEDED\).*?\[([^\]]+)\]',raw))


root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
destination=Path(DEST)
require(os.geteuid()==0,'root_build_only')
require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'boot_changed')
require(str(destination.parent)=='/home/root/aura-character-xuefei-20261030'
        and destination.name=='framing-'+PATCH_SHA[:16] and not destination.exists(), 'exclusive_isolated_destination_required')
require(destination.parent.resolve(strict=True)==destination.parent,'canonical_parent_required')
for relative,expected in BASE_PINS.items():require(digest(root/relative)==expected,'base_pin_changed_'+relative)
for relative,expected in HEADER_PINS.items():require(digest(root/relative)==expected,'header_pin_changed_'+relative)
source=base64.b64decode(SOURCE_B64,validate=True)
require(hashlib.sha256(source).hexdigest()==PATCH_SHA,'patched_source_changed')
base_library=root/'build_host/libaura_yuki.so'
api=symbols(base_library);dependencies=needed(base_library)
require('yuki_render' in api,'original_native_api_not_found')
destination.mkdir(mode=0o700)
cpp=destination/'yuki_host.cpp';cpp.write_bytes(source);cpp.chmod(0o600)
flags=(root/'build_host/CMakeFiles/aura_yuki.dir/flags.make').read_text()
def setting(name):return next(line.split('=',1)[1].strip() for line in flags.splitlines() if line.startswith(name+' ='))
compile_argv=['nice','-n','15','/usr/bin/c++']
for name in ('CXX_DEFINES','CXX_INCLUDES','CXX_FLAGS'):compile_argv+=shlex.split(setting(name))
compile_argv+=['-I'+str(root/'host'),'-c',str(cpp),'-o',str(destination/'yuki_host.cpp.o')]
original_link=shlex.split((root/'build_host/CMakeFiles/aura_yuki.dir/link.txt').read_text())
substitutions={'libaura_yuki.so':str(destination/'libaura_yuki.so'),
    'CMakeFiles/aura_yuki.dir/yuki_host.cpp.o':str(destination/'yuki_host.cpp.o'),
    'CMakeFiles/aura_yuki.dir/gles2_renderer.cpp.o':str(root/'build_host/CMakeFiles/aura_yuki.dir/gles2_renderer.cpp.o'),
    'CMakeFiles/aura_yuki.dir/diagnostic_api.cpp.o':str(root/'build_host/CMakeFiles/aura_yuki.dir/diagnostic_api.cpp.o'),
    'libyuki_core.a':str(root/'build_host/libyuki_core.a')}
link_argv=['nice','-n','15']+[substitutions.get(value,value) for value in original_link]
record=dict(status='BUILDING_ISOLATED_TU',directory=str(destination),base_library_sha256=digest(base_library),
    base_source_sha256=BASE_PINS['host/yuki_host.cpp'],patched_source_sha256=PATCH_SHA,
    compile_argv=compile_argv,link_argv=link_argv,header_pins=HEADER_PINS,base_pins=BASE_PINS,
    native_api_before=api,needed_before=dependencies,benchmark=False,model_or_gui_or_device_calls=0,
    active_library_installed=False,old_build_written=False,steps=[])
def save():
    (destination/'build_receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    (destination/'build_receipt.json').chmod(0o600)
save()
try:
    with (destination/'build.log').open('xb') as log:
        for label,argv,timeout in [('one_translation_unit',compile_argv,140),('link_existing_objects',link_argv,25)]:
            started=time.monotonic()
            result=subprocess.run(argv,cwd=str(destination),stdin=subprocess.DEVNULL,stdout=log,
                                  stderr=subprocess.STDOUT,timeout=timeout,check=False)
            record['steps'].append(dict(label=label,returncode=result.returncode,seconds=round(time.monotonic()-started,3)))
            save();require(result.returncode==0,label+'_failed')
    output=destination/'libaura_yuki.so';output.chmod(0o600)
    record.update(native_api_after=symbols(output),needed_after=needed(output),library_sha256=digest(output),
                  library_bytes=output.stat().st_size)
    require(record['native_api_after']==api and record['needed_after']==dependencies,'native_abi_or_dependency_changed')
    for relative,expected in BASE_PINS.items():require(digest(root/relative)==expected,'old_build_changed_after_compile_'+relative)
    for relative,expected in HEADER_PINS.items():require(digest(root/relative)==expected,'header_changed_after_compile_'+relative)
    require(digest(cpp)==PATCH_SHA,'candidate_source_changed_after_compile')
    record.update(status='COMPILED_ISOLATED_NOT_INSTALLED',base_sources_and_objects_unchanged=True,
                  native_api_identical=True,shared_dependencies_identical=True)
except Exception as exc:
    record.update(status='BUILD_FAILED_NOT_INSTALLED',error_type=type(exc).__name__,error=str(exc))
finally:save()
print(json.dumps(record),flush=True)
