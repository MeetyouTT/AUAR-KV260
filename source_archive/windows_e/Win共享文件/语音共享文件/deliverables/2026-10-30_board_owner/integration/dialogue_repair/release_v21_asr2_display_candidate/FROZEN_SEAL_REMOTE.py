
import hashlib,http.client,json,pathlib,subprocess,time
root=pathlib.Path(SPEC['target']);sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
assert SPEC['startup_sha256']==EXPECTED_STARTUP and SPEC['expected_final_listening_enabled'] is False
startup=(root/'startup/config.json').read_bytes();assert sha(startup)==SPEC['startup_sha256']
pins=json.loads(startup)['component_sha256'];assert pins==SPEC['component_sha256'] and len(pins)==SPEC['component_pins']==380
for rel,pin in pins.items():
 path=root/'runtime/aura'/rel;assert path.resolve()==path and sha(path.read_bytes())==pin
assert set(PRODUCTS)==set(ALLOWED_PRODUCTS)
assert all(pins[rel]==pin for rel,pin in PRODUCTS.items())
manifest_raw=(root/'production_source_manifest.json').read_bytes();assert sha(manifest_raw)==SPEC['source_manifest_sha256']
manifest=json.loads(manifest_raw)
assert manifest['component_pins']==pins and manifest['configuration_sha256']==SPEC['configuration_sha256']
assert manifest['configuration_path']==SPEC['minor_prepared_configuration_path']
assert sha(pathlib.Path(manifest['configuration_path']).read_bytes())==SPEC['configuration_sha256']
assert sha((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())==SPEC['configuration_sha256']
assert json.loads((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())['board_business']['asr_threads']==2
assert sha(pathlib.Path(SPEC['face_readback']['path']).read_bytes())==SPEC['face_readback']['sha256']
unit=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecMainStatus','-p','NRestarts','-p','DropInPaths'],text=True).splitlines())
assert unit['MainPID']==str(READY['main_pid']) and unit['ActiveState']=='active' and unit['SubState']=='running'
control=json.loads((root.parent/'control-production-v1/state.json').read_bytes())
assert control['phase']=='COMMITTED' and control['guard_removed'] and unit['DropInPaths']==control['final_dropins']
assert control['target_startup_sha256']==SPEC['startup_sha256']

def identity(pid):
 path=pathlib.Path('/proc')/str(pid);fields=(path/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':int(pid),'birth_ticks':int(fields[19]),'command_sha256':sha((path/'cmdline').read_bytes())}

def process_args(pid):
 raw=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes();assert len(raw)<=1048576
 return [part.decode() for part in raw.split(b'\0') if part]

assert process_args(READY['main_pid'])==['/usr/bin/python3','-B',str(root/'startup/launcher.py'),'--config',str(root/'startup/config.json')]
assert process_args(READY['gtk_pid'])[:3]==['/usr/bin/python3','-B',str(root/'runtime/aura/tools/board_avatar_pan.py')]
child_fields=(pathlib.Path('/proc')/str(READY['gtk_pid'])/'stat').read_text().rsplit(')',1)[1].split()
assert int(child_fields[1])==READY['main_pid']
camera=identity(SPEC['camera_owner']['camera_pid'])
assert str(camera['birth_ticks'])==SPEC['camera_owner']['camera_start_ticks'] and camera['command_sha256']==SPEC['camera_owner']['camera_cmdline_sha256']
preference_path=pathlib.Path('/home/root/.local/share/aura-board-business/listening_preference.json')
assert preference_path.resolve()==preference_path
preference_raw=preference_path.read_bytes();assert len(preference_raw)<=4096
preference=json.loads(preference_raw)
assert set(preference)=={'version','enabled'} and type(preference['version']) is int and preference['version']==1
assert preference['enabled'] is False
connection=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
try:
 connection.request('GET','/api/state');response=connection.getresponse();assert response.status==200
 raw=response.read(1048577);assert len(raw)<=1048576;ui=json.loads(raw)
finally:connection.close()
listening=ui.get('handsfree_dialogue',{});display=ui.get('avatar_display',{})
assert listening.get('enabled') is False and listening.get('state')=='PAUSED' and listening.get('microphone_open') is False
assert ui.get('phase')=='IDLE' and ui.get('playing') is False
assert display.get('kind')=='native_yuki_egl' and display.get('visible') is True and display.get('frames',0)>0
print(json.dumps({'status':'ASR2_DISPLAY_SOURCE_AND_SERVICE_VERIFIED','observed_mono':time.monotonic(),
 'boot_id':SPEC['boot_id'],'root':str(root),'startup_sha256':SPEC['startup_sha256'],
 'source_manifest_sha256':SPEC['source_manifest_sha256'],'configuration_sha256':SPEC['configuration_sha256'],
 'configuration_path':manifest['configuration_path'],'asr_threads':2,
 'component_pins':pins,'source_files':PRODUCTS,'unit':unit,'supervisor':identity(READY['main_pid']),'gtk':identity(READY['gtk_pid']),
 'camera':camera,'private_data_exported':False,'current_publication_committed':True,
 'saved_listening_preference':preference,'listening':{'enabled':False,'state':'PAUSED','microphone_open':False},
 'phase':'IDLE','playing':False,'native_visible':True,'native_frames':display['frames']}))
