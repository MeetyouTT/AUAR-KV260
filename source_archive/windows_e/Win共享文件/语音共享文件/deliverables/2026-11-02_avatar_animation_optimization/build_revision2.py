from pathlib import Path
import hashlib,json,subprocess,time
HERE=Path(__file__).resolve().parent;E=json.loads((HERE/'expected.json').read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def guard():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
 assert sha(Path(E['startup_path']))==E['startup_sha256']
 assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).strip()==b'0'
 p=Path('/proc')/str(E['camera_owner']['pid']);assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==E['camera_owner']['birth_ticks'];assert sha(p/'cmdline')==E['camera_owner']['command_sha256']
guard();root=Path('/home/root/aura-yuki-validation-20261030/native_integration');dest=HERE/'revision2';dest.mkdir(exist_ok=True)
original=json.loads((HERE/'original_native_pins.json').read_bytes())
for group in ('base_pins','header_pins'):
 for rel,h in original[group].items():assert sha(root/rel)==h
source=dest/'native';core=root/'build_host/libyuki_core.a';obj=root/'build_host/CMakeFiles/aura_yuki.dir';steps=[]
common=['nice','-n','15','/usr/bin/c++','-std=gnu++20','-O2','-DNDEBUG','-I'+str(source),'-I'+str(root/'host'),'-I'+str(root/'candidate_core/include'),'-isystem',str(root.parent/'deps/json'),'-isystem','/usr/include/libpng16']
def run(label,argv):
 t=time.monotonic();r=subprocess.run(argv,capture_output=True,timeout=180)
 steps.append(dict(label=label,args=argv,seconds=time.monotonic()-t,exit_code=r.returncode,stderr=r.stderr.decode(errors='replace')[-5000:]));(dest/'steps.json').write_text(json.dumps(steps,indent=2))
 assert r.returncode==0,label+' '+r.stderr.decode(errors='replace')[-2000:]
 return r.stdout
run('candidate_geometry_pivot_policy_test_compile',common+['-DOPTIMIZED',str(HERE/'tests/native_physics_audit.cpp'),str(core),'-o',str(dest/'policy_test')])
a=Path(E['runtime'])/'assets/yuki'
raw=run('candidate_original_policy_and_six_scenes',[str(dest/'policy_test'),str(a/'model.runtime.json'),str(a/'yuk_0.ems.resx.json'),str(a)])
(dest/'policy_test.log').write_bytes(raw);report=json.loads(raw.decode().strip().splitlines()[-1]);assert report['status']=='PASS';(dest/'physical_parameters.json').write_text(json.dumps(report,indent=2))
run('host_compile',common+['-fPIC','-Wall','-Wextra','-c',str(source/'yuki_host.cpp'),'-o',str(dest/'yuki_host.cpp.o')])
run('link',['nice','-n','15','/usr/bin/c++','-shared','-Wl,-soname,libaura_yuki.so','-o',str(dest/'libaura_yuki.so'),str(dest/'yuki_host.cpp.o'),str(obj/'gles2_renderer.cpp.o'),str(obj/'diagnostic_api.cpp.o'),str(core),'/usr/lib/libGLESv2.so','/usr/lib/libpng16.so','/usr/lib/libz.so'])
guard();result=dict(status='REVISION2_ARM_BUILD_AND_POLICIES_PASS_NOT_INSTALLED',library_sha256=sha(dest/'libaura_yuki.so'),steps=steps,source_files={p.name:sha(p) for p in source.iterdir() if p.is_file()},production_changed=False)
(dest/'BUILD_RECEIPT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
