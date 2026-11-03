import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/home/root/aura-sface-recovery-20261023/promotion/4bcbe0999c62a348')
report=json.loads((root/'report.json').read_text());assert report['complete'] and report['accepted']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
folder=Path(report['gui_context']);sys.path.insert(0,str(folder));import gui_trial as g
meta=json.loads((folder/'session.json').read_text());g.verify(folder,meta)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==report['boot']
override=Path(report['runtime_camera_override']);assert sha(override)==report['candidate_unit_sha256']
release=Path(report['release']);sources={name:sha(release/'aura'/name) for name in report['candidate_pins']}
assert sources==report['candidate_pins']
parent=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136')
before={str(p.relative_to(parent/'aura')):sha(p) for p in (parent/'aura').rglob('*.py') if '__pycache__' not in p.parts}
after={str(p.relative_to(release/'aura')):sha(p) for p in (release/'aura').rglob('*.py') if '__pycache__' not in p.parts}
changed=sorted(name for name in after if after[name]!=before.get(name))
assert changed==sorted(report['candidate_pins'])
cam=g.camera();g.retained().single_owner(cam['pid']);assert cam['pid']==report['candidate_camera_pid']
full=g.get(8790,'/health');state=g.ui();g.idle()
config=json.loads((release/'board_camera_ui.json').read_text());original=json.loads((parent/'board_camera_ui.json').read_text())
assert {k:v for k,v in config.items() if k not in ('sface_dpu_recovery','dpu_protection_seed')}==original
idconfig=Path(original['identity']['config']);idsha=sha(idconfig)
assert idsha=='398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3'
db=Path('/home/root/.local/share/aura/sface-int8-12b2ff5c7de15713-333217.sqlite3')
assert sha(db)=='ee22b97dbaa6f29f5b76c18565acc4f597cd61c6090f1946b993d2a29ab8101a'
gui_runtime=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/runtime')
gui_report=json.loads(Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/report.json').read_text())
gui_sources={str(p.relative_to(gui_runtime/'aura')):sha(p) for p in (gui_runtime/'aura').rglob('*.py') if '__pycache__' not in p.parts}
assert gui_sources==gui_report['gui_sources_after']
units=(report['guard']+'.timer','aura-sface-recovery-promotion-4bcbe0999c62a348.service')
states={unit:g.prop(unit,'ActiveState') for unit in units}
tr=Path('/sys/kernel/tracing')
probes=[line for line in (tr/'uprobe_events').read_text().splitlines() if 'aura_optional_' in line or 'aura_vart_' in line or 'aura_iso_' in line]
result={'read_only':True,'boot':report['boot'],'snapshot_mono_ns':time.monotonic_ns(),
 'unit_sha256':sha(g.UNIT),'runtime_override':str(override),'runtime_override_sha256':sha(override),
 'camera':cam,'sface_recovery':full['dpu_schedule']['sface_recovery'],
 'sources':sources,'changed_camera_python':changed,'camera_python_count':len(after),'gui_python_count':len(gui_sources),
 'gui_sources_unchanged':True,'identity_config_sha256':idsha,'database_sha256':sha(db),
 'ui':{k:state.get(k) for k in ('phase','audio_output_state','playing','paused','ui_page')},
 'microphone_open':state.get('handsfree_dialogue',{}).get('microphone_open'),
 'rollback_check':g.restore(folder,'check'),'unit_states':states,'own_probe_definitions':probes,
 'usb_audio_warning_delta_since_promotion':g.retained().audio_warnings(report['kernel_cursor']),
 'nrestarts':{unit:g.prop(unit,'NRestarts') for unit in (g.CAMERA,g.GUI,'xserver-nodm.service')},
 'services':{unit:{k:g.prop(unit,k) for k in ('ActiveState','MainPID')} for unit in (g.CAMERA,g.GUI,'xserver-nodm.service')}}
result['source_and_configuration_verified']=True
print(json.dumps(result))
