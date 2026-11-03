from pathlib import Path
import json,hashlib,subprocess,time,http.client
HERE=Path(__file__).resolve().parent;E=json.loads((HERE/'expected.json').read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def owner(pid):
    p=Path('/proc')/str(pid);return dict(pid=int(pid),birth_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(p/'cmdline'))
def guard():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
    assert sha(Path(E['startup_path']))==E['startup_sha256']
    for key in ('gui_owner','camera_owner'):assert owner(E[key]['pid'])==E[key]
    assert owner(E['gui_children'][0]['pid'])==E['gui_children'][0]
    conn=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
    try:conn.request('GET','/api/state');r=conn.getresponse();v=json.loads(r.read(1048576));assert r.status==200
    finally:conn.close()
    assert not v['playing'] and not v['pending_job'] and v['phase']=='IDLE' and v['manual_pan']['automatic_following'] is False
    return dict(gui_owner=E['gui_owner'],camera_owner=E['camera_owner'],monotonic=time.monotonic())
before=guard();R=Path(E['runtime']);cfg=json.loads(Path(E['startup_path']).read_bytes())
assert all(sha(R/k)==h for k,h in cfg['component_sha256'].items())
out=HERE/'build';out.mkdir(exist_ok=False);root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
original=json.loads((HERE/'original_native_pins.json').read_bytes())
for group in ('base_pins','header_pins'):
    for rel,h in original[group].items():assert sha(root/rel)==h,rel
steps=[]
def run(label,argv,timeout=240):
    start=time.monotonic();r=subprocess.run(argv,capture_output=True,timeout=timeout)
    steps.append(dict(label=label,args=argv,seconds=time.monotonic()-start,exit_code=r.returncode,stderr=r.stderr.decode(errors='replace')[-6000:]))
    (out/'steps.json').write_text(json.dumps(steps,indent=2))
    assert r.returncode==0,label+' '+r.stderr.decode(errors='replace')[-5000:]
    return r.stdout
flags=['nice','-n','15','/usr/bin/c++','-std=gnu++20','-O1','-DNDEBUG','-I'+str(HERE/'candidate/native'),'-I'+str(root/'host'),'-I'+str(root/'candidate_core/include'),'-isystem',str(root.parent/'deps/json'),'-isystem','/usr/include/libpng16']
assets=R/'assets/yuki'
for label,source in [('legacy_policy_physics','native_physics_audit.cpp'),('dialogue_state_actions','native_dialogue_audit.cpp')]:
    run('compile_'+label,flags+['-DOPTIMIZED',str(HERE/'tests'/source),str(root/'build_host/libyuki_core.a'),'-o',str(out/label)])
    raw=run('run_'+label,[str(out/label),str(assets/'model.runtime.json'),str(assets/'yuk_0.ems.resx.json'),str(assets)])
    (out/(label+'.log')).write_bytes(raw);result=json.loads(raw.decode().strip().splitlines()[-1]);assert result['status']=='PASS'
    (out/(label+'.json')).write_text(json.dumps(result,indent=2))
flags=[('-O2' if v=='-O1' else v) for v in flags]
run('compile_release',flags+['-fPIC','-Wall','-Wextra','-c',str(HERE/'candidate/native/yuki_host.cpp'),'-o',str(out/'yuki_host.cpp.o')])
objs=root/'build_host/CMakeFiles/aura_yuki.dir'
run('link_release',['nice','-n','15','/usr/bin/c++','-shared','-Wl,-soname,libaura_yuki.so','-o',str(out/'libaura_yuki.so'),str(out/'yuki_host.cpp.o'),str(objs/'gles2_renderer.cpp.o'),str(objs/'diagnostic_api.cpp.o'),str(root/'build_host/libyuki_core.a'),'/usr/lib/libGLESv2.so','/usr/lib/libpng16.so','/usr/lib/libz.so'])
result=dict(status='R4_ARM_BUILD_AND_STATE_ACTION_POLICIES_PASS',library_sha256=sha(out/'libaura_yuki.so'),source_files={p.name:sha(p) for p in (HERE/'candidate/native').iterdir() if p.is_file()},before=before,after=guard(),production_changed=False,GPU_or_audio_opened=False,execution_host='KV260 ARM CPU',steps=steps,stage=str(HERE))
(out/'BUILD_RECEIPT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
