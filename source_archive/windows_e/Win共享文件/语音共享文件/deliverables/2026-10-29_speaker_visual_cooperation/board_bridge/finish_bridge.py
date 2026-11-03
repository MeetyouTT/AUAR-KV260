import datetime,difflib,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;C=H/'candidate';BASE=H.parent
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((BASE/'SOURCE_MANIFEST.json').read_text())
for name,v in frozen['files'].items():assert digest(BASE/'candidate'/name)==v['sha256'],'Original 55 candidate changed: '+name
pre=json.loads((H/'board_preflight.json').read_text());files={}
for p in sorted(C.rglob('*')):
 if p.is_file() and p.suffix in ('.py','.json'):
  name=p.relative_to(C).as_posix();v=dict(sha256=digest(p),bytes=p.stat().st_size)
  if name in frozen['files']:v['frozen_55_sha256']=frozen['files'][name]['sha256']
  if name in pre['pins']:v['actual_base_sha256']=pre['pins'][name]
  files[name]=v
diffs=H/'diffs';diffs.mkdir(exist_ok=True)
for name in ('board/runtime/audio/channel_jobs.py','board/runtime/audio/voice_channel.py'):
 for label,source in (('frozen55',BASE/'candidate'/name),('actual279',BASE/'board_source'/name)):
  output=''.join(difflib.unified_diff(source.read_text(encoding='utf-8').splitlines(True),(C/name).read_text(encoding='utf-8').splitlines(True),fromfile=label+'/'+name,tofile='board_bridge/'+name))
  (diffs/(label+'_'+Path(name).name+'.diff')).write_text(output,encoding='utf-8')
def tests(path):
 root=ET.parse(path).getroot();s=root.find('testsuite') if root.tag=='testsuites' else root
 return {k:int(s.get(k,0)) for k in ('tests','failures','errors','skipped')}
config=json.loads((C/'config/face_gallery_readback.local.json').read_text())
manifest=dict(version=1,status='FROZEN_CANDIDATE_VERIFIED_NOT_DEPLOYED',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 files=files,components=list(files),existing_components_updated=[name for name in files if name in pre['pins']],
 new_components=[name for name in files if name not in pre['pins']],expected_board_pins=279+sum(name not in pre['pins'] for name in files),
 base_runtime=pre['actual_runtime'],base_boot=pre['boot'],base_pins=279,base_source_byte_checked=True,
 original_55_manifest_sha256=digest(BASE/'SOURCE_MANIFEST.json'),original_55_files_unchanged=True,
 readback_config_sha256=digest(C/'config/face_gallery_readback.local.json'),camera_source_pins=config['source_sha256'],
 tests=tests(H/'tests.xml'),compatibility=tests(H/'compat.xml'),arm=json.loads((H/'arm_readonly.json').read_text()),
 wire=dict(gallery_post='/v1/voice/identity/gallery',gallery_body_max=24576,packet_schema_max=32768,
   gallery_header='X-Aura-Face-Gallery',gallery_header_max=4096,identity_result_body_max=4096,
   oversize_receipt='omit_entire_receipt_keep_binding_incomplete',signing='trusted_windows_original_token_adapter_only'),
 not_validated=['live_face_enrollment','live_linked_voice_enrollment','biometric_field_accuracy','cross_boot_readback_refresh'],
 effects=dict(deployed=False,services_restarted=False,camera_restarted=False,private_gallery_written=False,
   identity_templates_exported=False,microphone_opened=False,playback=False,motion=False,new_models=False))
(H/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(dict(status=manifest['status'],files=len(files),expected_board_pins=manifest['expected_board_pins'],
 tests=manifest['tests'],compatibility=manifest['compatibility'],manifest_sha256=digest(H/'SOURCE_MANIFEST.json'))))
