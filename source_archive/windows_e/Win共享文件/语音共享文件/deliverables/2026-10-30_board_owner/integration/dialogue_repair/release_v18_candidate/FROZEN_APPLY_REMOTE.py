V17_STARTUP='0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a'
V17_MANIFEST='38a267a4f8d504803587c8be353452b146f1e232e926ac4e061a5e2832b33620'
CONFIG_SHA='d2511ee2b95f0ae9b2cbb18f16cde90719420d887e858926e8fd07a5c5b60013'
NATIVE_SHA='b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2'
PAIR_SHA='998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'
V18_STAGE='response-latency-v18-memory-recall'
EXPECTED_PAYLOAD={'board/runtime/board_memory_policy.py': ['410e5b3eaf7986be6baa68d148469eb33443654ed0db597004518877732533c5', '6050ed5e4dcfeb456c5d0969e257f624552f80ff722b3c3999a573f86cd933c2'], 'common/board_memory.py': ['c27d4d3c39e5de293cbc7fed8899de8b0d39ea6ccc99c0e7f64f22c8a90a2c0b', 'fe50db190aaafcb8841eaa132ed9ea218a80bc582efacb3c3c83e952bf985e9f'], 'board/runtime/board_dialogue.py': ['c877cdee602ff0bda669cc2b2fefa77e9328ce205a744e317df82ffb17146de6', 'bce1f21962d083275d9e8a966f244d8c227d0d62e9a30314767453d04c05b475'], 'board/runtime/board_speaker_business.py': ['56a01bee6cb93d808506564e71e56b35f3a51fa6d3432e82762e7b853e63870b', 'f299273d903d3bed4f24576f12dd41e327f5a0f0b490f8f122904291a769b067'], 'tools/board_avatar_gtk.py': ['c62dc730404e0de549eca2aaa886997824d4e4b381cd6b31ffb21bae509dc011', '7d95b5f682f7abf4a69509d5843c3345dcc31f8dbefeb0e9f3af27b19aa3542d']}

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
 assert SPEC['startup_sha256']==V17_STARTUP and SPEC['configuration_sha256']==CONFIG_SHA and SPEC['component_pins']==379
 assert SPEC['source_manifest_sha256']==V17_MANIFEST
 assert REVISION['stage']==V18_STAGE and REVISION['before_startup_sha256']==V17_STARTUP
 assert REVISION['before_manifest_sha256']==V17_MANIFEST and REVISION['business_options']=={} and not gui_options
 assert 'wake_word_required' not in REVISION and 'conversation_mode' not in REVISION
 assert REVISION['character_pair_selection_sha256']==PAIR_SHA and REVISION['native_library_sha256']==NATIVE_SHA
 assert sha(old_cfg)==CONFIG_SHA
 assert cfg['board_business']['asr_variant']=='paraformer_small' and cfg['board_business']['asr_threads']==3
 assert cfg['board_business']['asr_directory']=='/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6'
 assert cfg['board_business']['frontend_optimization']=='combined' and cfg['board_business']['frontend_threads']==1
 assert cfg['board_business']['capture_priority_nice']==-10
 assert cfg['character_pair']['selection_sha256']==PAIR_SHA
 assert startup['component_sha256']['tools/libaura_yuki.so']==NATIVE_SHA
 assert startup['component_sha256']['config/yuki_pair.formal.json']==PAIR_SHA
 pair=json.loads(read(root/'runtime/aura/config/yuki_pair.formal.json',PAIR_SHA));assert pair['native_config']['fps']==16
 assert set(PAYLOAD)==set(EXPECTED_PAYLOAD) and len(PAYLOAD)==5
 for rel,item in PAYLOAD.items():
  assert rel.endswith('.py') and (item['sha256'],item['before_sha256'])==tuple(EXPECTED_PAYLOAD[rel])
  assert startup['component_sha256'][rel]==item['before_sha256']
  raw=base64.b64decode(item['base64'],validate=True);assert sha(raw)==item['sha256'] and 0<len(raw)<2*1024*1024
  ast.parse(raw,feature_version=(3,9))
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
   assert not Path(rel).is_absolute() and '..' not in Path(rel).parts and rel.endswith('.py')
   raw=base64.b64decode(item['base64']);assert sha(raw)==item['sha256'];ast.parse(raw,feature_version=(3,9))
   before=item['before_sha256'];path=root/'runtime/aura'/rel
   if before is None:assert rel not in startup['component_sha256'] and not path.exists()
   else:
    assert startup['component_sha256'][rel]==before
    original=read(path,before);dest=backup/rel;dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True);create(dest,original)
   assert path.parent.resolve()==path.parent and path.parent.is_dir()
   new_files[rel]=raw;startup['component_sha256'][rel]=item['sha256'];manifest['component_pins'][rel]=item['sha256']
   manifest['files']['runtime/aura/'+rel]=dict(sha256=item['sha256'],bytes=len(raw))
  assert REVISION['business_options']=={} and not gui_options
  cfgraw=old_cfg;cfgpin=sha(cfgraw);assert cfgpin==CONFIG_SHA
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
  result.update(native_library_sha256=NATIVE_SHA,character_pair_selection_sha256=PAIR_SHA)
  assert len(startup['component_sha256'])==379 and cfgpin==CONFIG_SHA
  for rel,pin in startup['component_sha256'].items():read(root/'runtime/aura'/rel,pin)
  create(stage/'completed.json',encoded(result));print(json.dumps(result))
