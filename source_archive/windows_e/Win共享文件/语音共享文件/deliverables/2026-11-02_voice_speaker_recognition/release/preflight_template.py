"""Fresh public source/owner/idle reconciliation; metadata only, no control write."""
import ast
import base64
import copy
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time
import traceback

E=None  # FRESH_R4_EXPECTED

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def owner(pid):
    p=Path('/proc')/str(pid)
    return {'pid':int(pid),'birth_ticks':p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],'command_sha256':sha(p/'cmdline')}
def unit(name):
    r=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],capture_output=True,text=True,timeout=4);assert r.returncode==0
    return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
def get(host,port,path):
    c=http.client.HTTPConnection(host,port,timeout=3)
    try:
        t=time.monotonic();c.request('GET',path);r=c.getresponse();data=r.read(2097153);assert r.status==200 and len(data)<=2097152
        return json.loads(data),r.getheader('Date'),time.monotonic()-t
    finally:c.close()

out={'schema':'aura-per-utterance-voice-fresh-preflight-1','control_writes':0,'errors':[]};stage='source_and_owner'
try:
    assert type(E)is dict
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
    p=Path(E['startup_path']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==E['startup_sha256'];cfg=json.loads(raw);aura=Path(cfg['runtime'])/'aura'
    assert cfg['component_sha256']==E['component_sha256'] and len(cfg['component_sha256'])==380
    assert all(sha(aura/k)==v for k,v in cfg['component_sha256'].items())
    for role in ('gui_owner','gtk_owner','camera_owner'):assert owner(E[role]['pid'])==E[role]
    gu=unit('aura-avatar-ui.service');cu=unit('aura-camera-ui.service')
    assert gu['MainPID']==str(E['gui_owner']['pid']) and gu['ActiveState']=='active' and gu['SubState']=='running' and not gu['Job']
    assert cu['MainPID']==str(E['camera_owner']['pid']) and cu['ActiveState']=='active' and cu['SubState']=='running' and not cu['Job']
    props={k:gu[k] for k in ('Restart','KillMode','SendSIGKILL','TimeoutStopUSec')};assert props==E['original_GUI_properties']
    stage='selected_binding';gui_config=aura/'config/board_avatar_gtk.json';spec=json.loads(gui_config.read_bytes())['board_business']['face_readback'];assert sha(spec['path'])==spec['sha256'];binding=json.loads(Path(spec['path']).read_bytes())
    cam_config=binding['camera_config'];cam_sha=sha(cam_config);assert binding['source_sha256'][cam_config]==cam_sha
    verifier=aura/'board/runtime/audio/face_gallery_readback.py';assert sha(verifier)=='b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
    tree=ast.parse(verifier.read_bytes());klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FaceGalleryReadback');method=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_verify'));method.decorator_list=[];space={'Path':Path,'hashlib':hashlib,'json':json};exec(compile(ast.Module(body=[method],type_ignores=[]),str(verifier)+'::pure-verify','exec'),space);space['_verify'](binding)
    stage='UI_idle_state';v,_,_=get('127.0.0.1',8783,'/api/state');h=v['handsfree_dialogue'];business=v.get('board_business') or {};speaker=business.get('speaker') or {};pan=v.get('manual_pan') or {};rb=pan.get('readback') or {}
    assert v.get('ui_page')=='main' and not v.get('playing') and not v.get('pending_job') and not pan.get('automatic_following')
    assert h['enabled'] is False and h['microphone_open'] is False and not speaker.get('active') and not speaker.get('queued_or_active')
    assert (v.get('runtime_faults') or {}).get('count')==0 and (v.get('character_pair') or {}).get('state')=='READY'
    assert speaker['identity_match_threshold']==.35 and speaker['identity_ambiguity_margin']==.1 and speaker['speaker_calibrated'] is False
    saved=json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes());assert saved=={'version':1,'enabled':False}
    stage='original_model_health';health,date,latency=get('192.168.50.1',8797,'/health');backend=health['backend'];assert date and latency<=1 and health['ok'] is True and health['role']=='model_inference_only'
    assert backend['model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and backend['tts']=='omnivoice' and backend['num_step']==16 and backend['tts_ready'] is True and backend['voice']['alive'] is True
    out.update(boot_id=E['boot_id'],startup_path=str(p),startup_sha256=sha(p),startup_content_base64=base64.b64encode(raw).decode('ascii'),component_sha256=cfg['component_sha256'],all380_actual_bytes_match=True,gui_owner=E['gui_owner'],gtk_owner=E['gtk_owner'],camera_owner=E['camera_owner'],camera_config={'path':cam_config,'sha256':cam_sha},GUI_config_sha256=sha(gui_config),selected_face_binding={'path':spec['path'],'sha256':spec['sha256'],'source_pin_count':len(binding['source_sha256'])},original_GUI_properties=props,saved_listening_enabled=False,current_state={'main':True,'pair_ready':True,'listening_enabled':h['enabled'],'microphone_open':h['microphone_open'],'playing':False,'pending_job':False,'follow':False,'axis_readback':{k:rb.get(k) for k in ('flags','lease_left_ms','width_us','active','armed')},'runtime_fault_count':0},model_health_ready=True,model_health_RTT_ms=round(latency*1000,3),pure_selected_binding_verified=True,board_mono_ms=int(time.monotonic()*1000))
except Exception as exc:out['errors'].append({'stage':stage,'class':type(exc).__name__,'frames':[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(exc.__traceback__)]})
print(json.dumps(out))
