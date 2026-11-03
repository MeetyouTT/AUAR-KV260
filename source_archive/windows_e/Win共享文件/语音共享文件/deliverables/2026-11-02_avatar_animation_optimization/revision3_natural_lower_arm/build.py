from pathlib import Path
import json,hashlib,subprocess,time,http.client,os
HERE=Path(__file__).resolve().parent;E=json.loads((HERE/'expected.json').read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def owner(pid):
 p=Path('/proc')/str(pid);return dict(pid=int(pid),birth_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(p/'cmdline'))
def guard():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
 assert sha(Path(E['startup_path']))==E['startup_sha256']
 for k in ('gui_owner','camera_owner'):assert owner(E[k]['pid'])==E[k]
 assert owner(E['gui_children'][0]['pid'])==E['gui_children'][0]
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:c.request('GET','/api/state');r=c.getresponse();v=json.loads(r.read(1048576));assert r.status==200
 finally:c.close()
 assert not v['playing'] and not v['pending_job'] and v['phase']=='IDLE' and v['manual_pan']['automatic_following'] is False
 return dict(gui_owner=E['gui_owner'],camera_owner=E['camera_owner'],monotonic=time.monotonic())
before=guard();R=Path(E['runtime']);cfg=json.loads(Path(E['startup_path']).read_bytes());assert all(sha(R/k)==h for k,h in cfg['component_sha256'].items())
out=HERE/'build';out.mkdir(exist_ok=False);root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
original=json.loads((HERE/'original_native_pins.json').read_bytes())
for g in ('base_pins','header_pins'):
 for rel,h in original[g].items():assert sha(root/rel)==h,rel
steps=[]
def run(label,argv,timeout=180):
 t=time.monotonic();r=subprocess.run(argv,capture_output=True,timeout=timeout)
 steps.append(dict(label=label,args=argv,seconds=time.monotonic()-t,exit_code=r.returncode,stderr=r.stderr.decode(errors='replace')[-5000:]));(out/'steps.json').write_text(json.dumps(steps,indent=2))
 assert r.returncode==0,label+' '+r.stderr.decode(errors='replace')[-3000:]
 return r.stdout
flags=['nice','-n','15','/usr/bin/c++','-std=gnu++20','-O2','-DNDEBUG','-ffp-contract=off','-I'+str(HERE/'candidate/native'),'-I'+str(root/'host'),'-I'+str(root/'candidate_core/include'),'-isystem',str(root.parent/'deps/json'),'-isystem','/usr/include/libpng16']
run('compile_direct_old_new_motion_compare',flags+[str(HERE/'tests/motion_compare.cpp'),'-o',str(out/'motion_compare')])
numeric=json.loads(run('60000_tick_old_new_channel_comparison',[str(out/'motion_compare')]).decode());assert numeric['status']=='PASS';(out/'MOTION_COMPARE.json').write_text(json.dumps(numeric,indent=2))
# Tests use the original fixed core. The generated host is additionally tested
# with the real renderer below; this CPU probe opens no display/audio device.
testflags=[('-O1' if x=='-O2' else x) for x in flags]
run('compile_original_policy_and_natural_arm_probe',testflags+['-DOPTIMIZED',str(HERE/'tests/native_physics_audit.cpp'),str(root/'build_host/libyuki_core.a'),'-o',str(out/'native_policy')])
a=R/'assets/yuki';raw=run('run_original_policy_and_six_scene_probe',[str(out/'native_policy'),str(a/'model.runtime.json'),str(a/'yuk_0.ems.resx.json'),str(a)])
(out/'native_policy.log').write_bytes(raw);policy=json.loads(raw.decode().strip().splitlines()[-1]);assert policy['status']=='PASS';(out/'PHYSICAL_PARAMETERS.json').write_text(json.dumps(policy,indent=2))
run('compile_release_host',flags+['-fPIC','-Wall','-Wextra','-c',str(HERE/'candidate/native/yuki_host.cpp'),'-o',str(out/'yuki_host.cpp.o')])
objs=root/'build_host/CMakeFiles/aura_yuki.dir'
run('link_release',['nice','-n','15','/usr/bin/c++','-shared','-Wl,-soname,libaura_yuki.so','-o',str(out/'libaura_yuki.so'),str(out/'yuki_host.cpp.o'),str(objs/'gles2_renderer.cpp.o'),str(objs/'diagnostic_api.cpp.o'),str(root/'build_host/libyuki_core.a'),'/usr/lib/libGLESv2.so','/usr/lib/libpng16.so','/usr/lib/libz.so'])
after=guard();result=dict(status='R3_ARM_BUILD_ORIGINAL_POLICIES_AND_CHANNEL_COMPARE_PASS',library_sha256=sha(out/'libaura_yuki.so'),source_files={p.name:sha(p) for p in (HERE/'candidate/native').iterdir() if p.is_file()},numeric_comparison=numeric,before=before,after=after,production_changed=False,GPU_or_audio_opened=False,steps=steps,stage=str(HERE))
(out/'BUILD_RECEIPT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
