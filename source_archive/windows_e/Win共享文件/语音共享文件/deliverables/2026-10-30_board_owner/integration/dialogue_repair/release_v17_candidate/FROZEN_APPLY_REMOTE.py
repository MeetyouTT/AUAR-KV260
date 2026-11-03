V16_STARTUP='bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
V16_CONFIG='8c35161e766c53728c75c592a074845e35e01502e8438aaf649b4a8e078a6101'
V16_MANIFEST='e488f45660e78904d04ba57fe4210e2bcf9eeffa6282219096e9d7b6115df718'
V17_STAGE='response-latency-v17-thinking-and-feature-queries'
OLD_PAIR='87ad6a1cc520538c7c47b6b52aa5e99c24446efdeb49b69cfe65f8872398f2b0'
NEW_PAIR='998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'
NEW_NATIVE='b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2'
NON_PY={'tools/libaura_yuki.so': 'b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2', 'config/yuki_pair.formal.json': '998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'}
EXPECTED_PAYLOAD={'board/runtime/audio/board_dialogue_jobs.py': ['687b80cde20d70e4de56dd71956683b9cec59f55bd25965491dc08d00c8cb248', '71fd1ac8e2ddb2e20eeb572063cc69e370e18f40af4a97fb65e2d8258bae45a0'], 'board/runtime/board_business.py': ['bb82c154ad1d0120b9b188f07a7aa69ec3b3ba6ca15894b1cb0d5ef4a1a1d025', 'b0d19864ac305e52d5d9f4f86823ae97b4d8d134c56c0ec78c0ae316bd8efc18'], 'board/runtime/board_speaker_business.py': ['f299273d903d3bed4f24576f12dd41e327f5a0f0b490f8f122904291a769b067', '43227afc6d86dbf3ae4eed5cf3efcb996ed0267551958773901f49309122a8c7'], 'board/runtime/visual_policy.py': ['e8e80e0d92c889e5533aa84c4abf7782d7424d8658783d64acac2d17ea2a147e', 'efb730d82b812f4323e92c8d6fdf1e69ae9f8dbffab1a5c5db346a18d12b4dc9'], 'common/feature_intents.py': ['1bb807ed88a84515942cca7e0dadab92dac99e2fd39b163b2e5d20a0194d8945', None], 'common/voice_enrollment.py': ['238939dbc4afa0559caa8687ff01a67854b606a33df4bdeaf2b0103fb8c994a8', '9a40e16875afb5c7c031a2994a205bd4e29f7cb78115a624586164f1a08c4f67'], 'tools/speaker_device.py': ['da9c199527abdf9e247661d8798f4345cf0b79524f5c2a06394b5dc9c44107de', '73648e960ab28e16cce1e0676bd7981b5fc35c70bce9868b864e5c8881af4e00'], 'tools/yuki_jobs_candidate.py': ['18d4bcbc6d3a32b3a2edd64103d634493e2fbd00f88ab0809fa600144d26508d', '6dd98c8a1be49f1c4a468ba10a585cbe3fbf36258d9e90d28c7423bac1f8093c'], 'config/yuki_pair.formal.json': ['998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099', '87ad6a1cc520538c7c47b6b52aa5e99c24446efdeb49b69cfe65f8872398f2b0'], 'tools/formal_native_yuki.py': ['3e300d9de790637adc7ef18bd804bdc1a00cbbed3759a2ba85954060e5867e29', '25e648a9630c78843ea188269e2655eac2a412e19c0ed854042d3bcbe87e0453'], 'tools/formal_yuki.py': ['c74b5f00d52208d992e8ee82c998250001c781c900d31b1f72a18bdda6f492e9', '610696bfb89c77a295962e9186f6f5c069ed317234e6ad766d082203e523285d'], 'tools/libaura_yuki.so': ['b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2', '887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2'], 'tools/native_yuki.py': ['306dd3efe445111a57930217709c4a70bf3caf885a7d745fd28c4a6a97442c8e', 'b5193b8766bb3bfe58f748affefbb0cebda9da6e33703dbef41833dfd789e8a4']}
EXPECTED_ARTIFACTS={'feature': '395eda57127551cd788c112ef1a8001f8d75c40d46b400d4a9a2af417702bb7e', 'animation': 'ac34e8c51b988d69110e1c82d9fc1c11ec8c6ab39cd08a5deae95a2260b52dea', 'pair': '04ea05e54da8a83837ea6072ae540c5078373fa2901570e246f475507d2cc838', 'build': '85579d297cc61b1f52a241267c415500bd4fb4493689ca1dd6dd5f4f22d7cd79'}

import ast,base64,fcntl,hashlib,json,os,pathlib,subprocess,sys
Path=pathlib.Path
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encoded=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
root=Path(SPEC['target']);control=root.parent/'control-production-v1'
assert root==Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13') and root.resolve()==root
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
assert REVISION['stage'].startswith(('automatic-listening-v','response-latency-v')) and '/' not in REVISION['stage'] and '..' not in REVISION['stage']
assert set(REVISION['business_options'])<=set(('frontend_process','frontend_capture_process','frontend_optimization','capture_priority_nice','frontend_threads','asr_threads'))
assert 'wake_word_required' not in REVISION or type(REVISION['wake_word_required']) is bool
assert 'conversation_mode' not in REVISION or REVISION['conversation_mode'] in ('half_duplex','interruptible')
gui_options=REVISION.get('gui_options',{})
assert isinstance(gui_options,dict) and set(gui_options)<=set(('voice_barge_in',))
assert all(type(v) is bool for v in gui_options.values())
def read(p,pin=None):
 p=Path(p);assert p.is_file() and not p.is_symlink() and p.resolve()==p
 raw=p.read_bytes();assert pin is None or sha(raw)==pin
 return raw
def create(p,raw):
 fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def replace(p,raw):
 tmp=p.with_name(p.name+'.listening-revision-new');create(tmp,raw);os.replace(str(tmp),str(p))
 fd=os.open(str(p.parent),os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
with open('/run/aura-production-publisher.lock','a') as publication:
 fcntl.flock(publication,fcntl.LOCK_EX|fcntl.LOCK_NB)
 unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SendSIGKILL','-p','TimeoutStopUSec','-p','Job'],text=True).splitlines() if '=' in x)
 assert unit['MainPID']=='0' and unit['ActiveState']=='inactive' and unit['SendSIGKILL']=='no' and unit['TimeoutStopUSec']=='infinity' and not unit['Job']
 journal=json.loads(read(control/'state.json'));assert journal['phase']=='NORMAL_CLOSED' and journal['guard_removed'] is False and journal['active_root']==str(root)
 read(journal['guard'],journal['guard_sha256'])
 startup_path=root/'startup/config.json';old_startup=read(startup_path,SPEC['startup_sha256']);startup=json.loads(old_startup)
 assert len(startup['component_sha256'])==SPEC['component_pins']
 for rel,pin in startup['component_sha256'].items():read(root/'runtime/aura'/rel,pin)
 cfgpath=root/'runtime/aura/config/board_avatar_gtk.json';old_cfg=read(cfgpath,startup['component_sha256']['config/board_avatar_gtk.json']);cfg=json.loads(old_cfg)
 assert cfg['board_business']['data_origin']=='board' and cfg['board_business']['retention_enabled'] is True
 assert SPEC['startup_sha256']==V16_STARTUP and SPEC['configuration_sha256']==V16_CONFIG and SPEC['component_pins']==378
 assert REVISION['stage']==V17_STAGE and REVISION['business_options']=={} and not gui_options
 assert 'wake_word_required' not in REVISION and 'conversation_mode' not in REVISION
 assert REVISION['character_pair_selection_sha256']==NEW_PAIR and REVISION['native_library_sha256']==NEW_NATIVE
 assert cfg['board_business']['asr_variant']=='paraformer_small' and cfg['board_business']['asr_threads']==3
 assert cfg['board_business']['asr_directory']=='/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6'
 assert cfg['character_pair']['selection_sha256']==OLD_PAIR
 assert set(PAYLOAD)==set(EXPECTED_PAYLOAD) and len(PAYLOAD)==13
 decoded={}
 for rel,item in PAYLOAD.items():
  assert (item['sha256'],item['before_sha256'])==tuple(EXPECTED_PAYLOAD[rel])
  raw=base64.b64decode(item['base64'],validate=True);assert sha(raw)==item['sha256'] and 0<len(raw)<2*1024*1024
  if rel.endswith('.py'):ast.parse(raw,feature_version=(3,9))
  else:assert NON_PY.get(rel)==item['sha256']
  if item['before_sha256'] is None:assert rel=='common/feature_intents.py'
  decoded[rel]=raw
 assert set(ARTIFACTS)==set(EXPECTED_ARTIFACTS)
 evidence={}
 for key,pin in EXPECTED_ARTIFACTS.items():
  raw=base64.b64decode(ARTIFACTS[key]['base64'],validate=True)
  assert sha(raw)==pin==ARTIFACTS[key]['sha256'];evidence[key]=json.loads(raw)
 feature,animation,pair,build=[evidence[k] for k in ('feature','animation','pair','build')]
 assert feature['source_baseline_startup_sha256']==V16_STARTUP and feature['source_baseline_manifest_sha256']==V16_MANIFEST
 assert animation['base_startup_sha256']==V16_STARTUP and animation['base_source_manifest_sha256']==V16_MANIFEST
 assert set(feature['files'])|set(pair['files'])==set(PAYLOAD) and not set(feature['files'])&set(pair['files'])
 for rel,row in feature['files'].items():assert (row['sha256'],row['before_sha256'])==tuple(EXPECTED_PAYLOAD[rel])
 for rel,pin in pair['files'].items():assert pin==EXPECTED_PAYLOAD[rel][0]
 assert pair['selection_sha256']==NEW_PAIR and pair['base_selection_sha256']==OLD_PAIR
 assert pair['native_build_receipt_sha256']==EXPECTED_ARTIFACTS['build']
 assert build['status']=='ISOLATED_COMPILED_CPU_POLICY_PASSED_NOT_INSTALLED'
 assert build['source_sha256']==animation['files']['native/yuki_host.cpp']['after_sha256']
 assert build['header_sha256']==animation['files']['native/yuki_host.h']['after_sha256']
 assert build['shared_dependencies_identical'] is True and build['native_policy_test']['status']=='PASS'
 assert build['production_installed'] is False and build['library_sha256']==NEW_NATIVE
 old_pair=json.loads(read(root/'runtime/aura/config/yuki_pair.formal.json',OLD_PAIR))
 new_pair=json.loads(decoded['config/yuki_pair.formal.json'])
 expected_pair=json.loads(json.dumps(old_pair))
 expected_pair['runtime_pins']['tools/native_yuki.py']=EXPECTED_PAYLOAD['tools/native_yuki.py'][0]
 expected_pair['runtime_pins']['tools/libaura_yuki.so']=NEW_NATIVE
 assert new_pair==expected_pair and new_pair['native_config']['fps']==16
 assert new_pair['identity']==old_pair['identity'] and new_pair['presentation']==old_pair['presentation']
 native=decoded['tools/libaura_yuki.so'];assert native[:6]==b'\x7fELF\x02\x01' and int.from_bytes(native[18:20],'little')==183
 formal=ast.parse(decoded['tools/formal_yuki.py'])
 formal_pair_pins=[ast.literal_eval(n.value) for n in formal.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PAIR_CONFIG_SHA256' for t in n.targets)]
 assert formal_pair_pins==[NEW_PAIR]
 private=Path(cfg['board_business']['private_root']);assert private==Path('/home/root/.local/share/aura-board-business')
 sys.path.insert(0,str(root/'runtime/aura'))
 from common.board_production_bootstrap import verify_production_bootstrap
 proof=verify_production_bootstrap(private,cfg['board_business']['bootstrap_receipt'],cfg['board_business']['bootstrap_receipt_sha256']);assert proof['profiles_migration_verified'] is True
 with open(private/'writer.lock','a') as writer:
  fcntl.flock(writer,fcntl.LOCK_EX|fcntl.LOCK_NB)
  manifest_path=root/'production_source_manifest.json';old_manifest=read(manifest_path,REVISION['before_manifest_sha256']);manifest=json.loads(old_manifest)
  stage=control/REVISION['stage'];stage.mkdir(mode=0o700);backup=stage/'before';backup.mkdir(mode=0o700)
  for name,raw in [('startup-config.json',old_startup),('gui-config.json',old_cfg),('production-source-manifest.json',old_manifest)]:create(backup/name,raw)
  new_files={}
  for rel,item in PAYLOAD.items():
   assert not Path(rel).is_absolute() and '..' not in Path(rel).parts and (rel.endswith('.py') or NON_PY.get(rel)==item['sha256'])
   raw=decoded[rel];assert sha(raw)==item['sha256']
   if rel.endswith('.py'):ast.parse(raw,feature_version=(3,9))
   else:assert NON_PY.get(rel)==item['sha256']
   before=item['before_sha256'];path=root/'runtime/aura'/rel
   if before is None:assert rel not in startup['component_sha256'] and not path.exists()
   else:
    assert startup['component_sha256'][rel]==before
    original=read(path,before);dest=backup/rel;dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True);create(dest,original)
   assert path.parent.resolve()==path.parent and path.parent.is_dir()
   new_files[rel]=raw;startup['component_sha256'][rel]=item['sha256'];manifest['component_pins'][rel]=item['sha256']
   manifest['files']['runtime/aura/'+rel]=dict(sha256=item['sha256'],bytes=len(raw))
  expected_cfg=json.loads(old_cfg);expected_cfg['character_pair']['selection_sha256']=NEW_PAIR
  cfg['character_pair']['selection_sha256']=NEW_PAIR
  assert cfg==expected_cfg
  cfgraw=encoded(cfg);cfgpin=sha(cfgraw)
  create(stage/'effective-gui-config.json',cfgraw);startup['component_sha256']['config/board_avatar_gtk.json']=cfgpin
  manifest['component_pins']['config/board_avatar_gtk.json']=cfgpin;manifest['files']['runtime/aura/config/board_avatar_gtk.json']=dict(sha256=cfgpin,bytes=len(cfgraw))
  startupraw=encoded(startup);manifest['files']['startup/config.json']=dict(sha256=sha(startupraw),bytes=len(startupraw))
  manifest.update(configuration_path=str(stage/'effective-gui-config.json'),configuration_sha256=cfgpin,
   listening_revision=dict(previous_startup_sha256=SPEC['startup_sha256'],stage=REVISION['stage'],default_automatic_listening=True,
    explicit_pause_persisted=True,business_options=REVISION['business_options'],private_data_replayed=False,original_queue_frames=8))
  if 'wake_word_required' in REVISION:
   manifest['listening_revision']['wake_word_required']=REVISION['wake_word_required']
  if 'conversation_mode' in REVISION:
   manifest['listening_revision']['conversation_mode']=REVISION['conversation_mode']
  if gui_options:manifest['listening_revision']['gui_options']=gui_options
  manifest_raw=encoded(manifest)
  create(stage/'intent.json',encoded(dict(previous_startup_sha256=SPEC['startup_sha256'],new_startup_sha256=sha(startupraw),source_files={r:sha(v) for r,v in new_files.items()},private_data_replayed=False)))
  for rel,raw in new_files.items():
   path=root/'runtime/aura'/rel
   if path.exists():replace(path,raw)
   else:create(path,raw)
  replace(cfgpath,cfgraw);replace(startup_path,startupraw);replace(manifest_path,manifest_raw)
  result=dict(status='LISTENING_REVISION_INSTALLED_UI_STOPPED',target=str(root),stage=REVISION['stage'],startup_sha256=sha(startupraw),component_pins=len(startup['component_sha256']),
   configuration_sha256=cfgpin,source_manifest_sha256=sha(manifest_raw),source_files={r:sha(v) for r,v in new_files.items()},automatic_listening=True,retention_enabled=True,
   private_data_replayed=False,business_options=REVISION['business_options'])
  if 'wake_word_required' in REVISION:result['wake_word_required']=REVISION['wake_word_required']
  if 'conversation_mode' in REVISION:result['conversation_mode']=REVISION['conversation_mode']
  if gui_options:result['gui_options']=gui_options
  result.update(native_library_sha256=NEW_NATIVE,character_pair_selection_sha256=NEW_PAIR)
  assert len(startup['component_sha256'])==379
  for rel,pin in startup['component_sha256'].items():read(root/'runtime/aura'/rel,pin)
  create(stage/'completed.json',encoded(result));print(json.dumps(result))
