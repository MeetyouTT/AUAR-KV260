# IMPORT_DEVICE_READ_HEADER
import os
HERE=Path(__file__).resolve().parent;e=json.loads((HERE/'expected.json').read_bytes());m=json.loads((HERE/'PUBLICATION.json').read_bytes())
assert sha(P)==m['startup_after'] and owner(e['camera_owner']['pid'])==e['camera_owner']
cfg=json.loads(P.read_bytes());rt=Path(cfg['runtime'])/'aura';assert len(cfg['component_sha256'])==380 and all(sha(rt/k)==h for k,h in cfg['component_sha256'].items())
g=unit('aura-avatar-ui.service');c=unit('aura-camera-ui.service');assert g['ActiveState']=='active' and g['SubState']=='running' and not g['Job']
launch=json.loads((Path(cfg['runtime'])/'launch.json').read_bytes());gtk=owner(launch['pid']);go=owner(g['MainPID'])
assert launch['supervisor_pid']==go['pid']
s=state();h=s['handsfree_dialogue'];a=s['avatar_display'];pan=s['manual_pan']
assert s['ui_page']=='main' and s['phase']=='IDLE' and not s['playing'] and not s['pending_job']
assert h['enabled'] is False and h['microphone_open'] is False and pan['automatic_following'] is False
assert s['character_pair']['state']=='READY' and a['visible'] is True and s['runtime_faults']['count']==0
stop=json.loads((HERE/'STOP_RESULT_original.json').read_bytes());assert all(g[k]==v for k,v in stop['original_GUI_properties'].items())
pref=json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes());assert pref==stop['saved_listening']
own=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:
  if str(HERE).encode() in (p/'cmdline').read_bytes():own.append(owner(p.name))
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
assert not own
guards=list(Path('/run/systemd/system/aura-avatar-ui.service.d').glob('*animation*'));assert not guards
print(json.dumps(dict(status='FRESH_READY_NO_ANIMATION_HELPERS_OR_PENDING_COMMANDS',boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),startup_sha256=sha(P),native_library_sha256=sha(rt/'tools/libaura_yuki.so'),all_380_pins_match=True,gui_owner=go,gtk_owner=gtk,camera_owner=owner(c['MainPID']),GUI_properties={k:g[k] for k in stop['original_GUI_properties']},main_page=True,avatar_visible=True,phase=s['phase'],pair_ready=True,runtime_fault_count=s['runtime_faults']['count'],native_frames=a['frames'],listening_preference=pref,microphone_open=False,playing=False,automatic_following=False,animation_helpers_remaining=own,temporary_animation_guards=guards,probe_read_only=True)))
