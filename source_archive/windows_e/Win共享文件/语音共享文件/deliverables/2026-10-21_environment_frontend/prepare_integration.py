"""Overlay the remote CPU frontend on the currently effective UI runtime."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
base=json.loads(ssh('python3 -B -',r'''
import base64,json,re,subprocess
from pathlib import Path
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
config=Path(re.findall(r'--config (\S+)',unit)[-1])
assert str(config) in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
cfg=json.loads(config.read_text());root=Path(cfg['runtime'])
names=['aura/tools/board_avatar_gtk.py','aura/config/board_avatar_gtk.json']
print(json.dumps({'ui_unit':unit,'runtime':str(root),'config_path':str(config),'startup_config':cfg,
 'baseline_files':{n:base64.b64encode((root/n).read_bytes()).decode() for n in names}}))
''',timeout=20))
(HERE/'integration_board_baseline.json').write_text(json.dumps(base,indent=2)+'\n',encoding='utf-8')
gtk=base64.b64decode(base['baseline_files']['aura/tools/board_avatar_gtk.py']).decode().replace('\r\n','\n')
old='recording_type=RecordingController;recording_options={}'
assert gtk.count(old)==1
gtk=gtk.replace(old,"recording_type=RecordingController;recording_options={'audio_frontend':config.get('audio_frontend')}")
old="recording_options={'boot_id':self.board_boot_id,"
assert gtk.count(old)==1
gtk=gtk.replace(old,old+"\n                                   'audio_frontend':config.get('audio_frontend'),")
compile(gtk,'board_avatar_gtk.py','exec')
cfg=json.loads(base64.b64decode(base['baseline_files']['aura/config/board_avatar_gtk.json']))
cfg['audio_frontend']={'enabled':True,'host':'192.168.50.1','port':8795,'timeout_ms':180}
merged={'aura/tools/board_avatar_gtk.py':gtk.encode(),
        'aura/config/board_avatar_gtk.json':(json.dumps(cfg,indent=2)+'\n').encode()}
names=['aura/common/frontend_wire.py','aura/board/runtime/audio/remote_frontend.py',
       'aura/board/runtime/audio/automatic_capture.py','aura/board/runtime/audio/vad.py',
       'aura/tools/barge_in_capture.py','aura/tools/barge_in_recording.py','aura/tools/board_recording.py',
       'aura/tools/audio_frontend_host.py','aura/tests/framework/test_remote_frontend.py']
for name in names:merged[name]=(PROJECT/name).read_bytes()
for name,data in merged.items():
    target=HERE/'integration_sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
payload={n:base64.b64encode(raw).decode() for n,raw in merged.items()}
template=(PROJECT/'deliverables/2026-10-20_listening_timing/prepare.py').read_text(encoding='utf-8')
remote=template.split("remote=r'''",1)[1].split("'''.replace('BASE'",1)[0]
remote=remote.replace('aura-listening-timing-20261020','aura-audio-frontend-20261021')
remote=remote.replace("modules=['test_listening_timing'","modules=['test_remote_frontend','test_barge_verification','test_listening_timing'",1)
remote=remote.replace('base=BASE;p=PAYLOAD','base='+repr(base)+';p='+repr(payload),1)
r=json.loads(ssh('python3 -B -',remote,timeout=250))
for key in ('tests_log','preflight_log'):(HERE/('integration_'+key+'.log')).write_text(r.pop(key),encoding='utf-8')
(HERE/'integration_candidate.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:r[k] for k in ('runtime','tests_passed','preflight_passed')}))
assert r['tests_passed'] and r['preflight_passed']
