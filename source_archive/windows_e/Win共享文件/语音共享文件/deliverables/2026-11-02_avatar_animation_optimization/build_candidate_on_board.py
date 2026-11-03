"""Stage-local build; no production file, audio, camera or display changes."""
from pathlib import Path
import json,hashlib,subprocess,os,time,http.client
HERE=Path(__file__).resolve().parent
E=json.loads((HERE/'expected.json').read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def owner(pid):
 p=Path('/proc')/str(pid)
 return dict(pid=int(pid),birth_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(p/'cmdline'))
def guard():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
 assert sha(Path(E['startup_path']))==E['startup_sha256']
 for k in ('gui_owner','camera_owner'):assert owner(E[k]['pid'])==E[k]
 assert owner(E['gui_children'][0]['pid'])==E['gui_children'][0]
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4);c.request('GET','/api/state');r=c.getresponse();v=json.loads(r.read(1048576));c.close();assert r.status==200
 assert not v['playing'] and not v['pending_job'] and v['phase']=='IDLE'
 assert v['handsfree_dialogue']['enabled'] is False and v['handsfree_dialogue']['microphone_open'] is False
 assert v['manual_pan']['automatic_following'] is False
 assert v['character_pair']['state']=='READY'
 return {'monotonic':time.monotonic(),'gui_owner':E['gui_owner'],'camera_owner':E['camera_owner']}
before=guard();root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
pins=json.loads((HERE/'original_native_pins.json').read_bytes())
verified={}
for group in ('base_pins','header_pins'):
 for rel,h in pins[group].items():
  assert sha(root/rel)==h,rel
  verified[rel]=h
out=HERE/'build';out.mkdir(exist_ok=False)
core=root/'build_host/libyuki_core.a';objects=root/'build_host/CMakeFiles/aura_yuki.dir'
steps=[]
def run(label,argv):
 start=time.monotonic();r=subprocess.run(argv,capture_output=True,timeout=190)
 steps.append(dict(label=label,argv=argv,exit_code=r.returncode,seconds=time.monotonic()-start,stderr=r.stderr.decode(errors='replace')[-6000:]))
 (out/'steps.json').write_text(json.dumps(steps,indent=2))
 assert r.returncode==0,label+' '+r.stderr.decode(errors='replace')[-3000:]
 return r.stdout
common=['nice','-n','15','/usr/bin/c++','-std=gnu++20','-O2','-DNDEBUG','-I'+str(root/'host'),'-I'+str(root/'candidate_core/include'),'-isystem',str(root.parent/'deps/json'),'-isystem','/usr/include/libpng16']
assets=Path(E['runtime'])/'assets/yuki';args=[str(assets/'model.runtime.json'),str(assets/'yuk_0.ems.resx.json'),str(assets)]
for variant in ('baseline','candidate_physics'):
 source=HERE/variant/'native';flags=common+['-I'+str(source)]
 # Variant include must precede original host include.
 flags=common[:7]+['-I'+str(source)]+common[7:]
 testflags=flags+(['-DOPTIMIZED'] if variant=='candidate_physics' else [])
 run(variant+'_test_compile',testflags+[str(HERE/'tests/native_physics_audit.cpp'),str(core),'-o',str(out/(variant+'_test'))])
 data=run(variant+'_policy_and_physics',[str(out/(variant+'_test'))]+args)
 (out/(variant+'_test.log')).write_bytes(data)
 result=json.loads(data.decode().strip().splitlines()[-1]);assert result['status']=='PASS'
 (out/(variant+'_physical_parameters.json')).write_text(json.dumps(result,indent=2))
 if variant=='candidate_physics':
  run('candidate_host_compile',flags+['-fPIC','-Wall','-Wextra','-c',str(source/'yuki_host.cpp'),'-o',str(out/'yuki_host.cpp.o')])
  run('candidate_link',['nice','-n','15','/usr/bin/c++','-shared','-Wl,-soname,libaura_yuki.so','-o',str(out/'libaura_yuki.so'),str(out/'yuki_host.cpp.o'),str(objects/'gles2_renderer.cpp.o'),str(objects/'diagnostic_api.cpp.o'),str(core),'/usr/lib/libGLESv2.so','/usr/lib/libpng16.so','/usr/lib/libz.so'])
after=guard()
result=dict(status='ARM_BUILD_AND_ORIGINAL_POLICIES_AND_PHYSICAL_PARAMETERS_PASSED',library_sha256=sha(out/'libaura_yuki.so'),library_bytes=(out/'libaura_yuki.so').stat().st_size,verified_original_native_inputs=verified,steps=steps,before=before,after=after,production_modified=False,display_opened=False,stage=str(HERE))
(out/'BUILD_RECEIPT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
