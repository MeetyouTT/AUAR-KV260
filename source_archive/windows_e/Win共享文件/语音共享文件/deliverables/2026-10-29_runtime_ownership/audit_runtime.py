"""Read-only runtime ownership inventory; no media, DB content or device commands."""
import concurrent.futures,datetime,json,socket,subprocess,sys,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from common import frontend_wire,portrait_wire
from board_ssh import ssh

def get(port,path='/health'):
    with urllib.request.urlopen('http://127.0.0.1:%d%s'%(port,path),timeout=4) as response:return json.load(response)
def health(port):
    try:
        if port in (8795,8796):
            wire=frontend_wire if port==8795 else portrait_wire
            with socket.create_connection(('192.168.50.1',port),timeout=3) as connection:
                wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'});value,payload=wire.receive(connection,0 if port==8796 else 3)
                assert not payload
        elif port==8810:value=get(port)
        else:
            with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=4) as response:value=json.load(response)
        return str(port),value
    except Exception as exc:return str(port),{'error':type(exc).__name__+': '+str(exc)[:180]}

report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'doll runtime and storage ownership','read_only':True}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:report['windows_health']=dict(pool.map(health,(8791,8792,8795,8796,8810,8812)))
ps=r'''
$listeners=@(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in @(8791,8792,8795,8796,8810,8812,11435,11436)} | Select-Object LocalAddress,LocalPort,OwningProcess)
$owners=@($listeners.OwningProcess)
$processes=@(Get-CimInstance Win32_Process | Where-Object {$owners -contains $_.ProcessId} | Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine)
[pscustomobject]@{listeners=$listeners;owners=$processes} | ConvertTo-Json -Depth 4
'''
report['windows_processes']=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',ps],text=True,encoding='utf-8',errors='replace',timeout=15))
report['dialogue_config']=json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
report['timeline_config']=json.loads((A/'config/timeline_memory.json').read_text(encoding='utf-8-sig'))
try:
    configured=report['dialogue_config']['model']
    report['configured_llm_residency']=[{k:r[k] for k in ('name','model','size','size_vram','expires_at') if k in r} for r in get(11435,'/api/ps').get('models',[]) if configured in (r.get('name'),r.get('model'))]
except Exception as exc:report['llm_residency_error']=type(exc).__name__+': '+str(exc)
remote=r'''
import datetime,hashlib,json,re,subprocess,sys,urllib.request
from pathlib import Path
def unit(name):return dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show',name,'-p','ActiveState','-p','MainPID','-p','ExecStart'],text=True).splitlines() if '=' in line)
ui=unit('aura-avatar-ui.service');camera=unit('aura-camera-ui.service')
match=re.search(r'--config\s+([^ ;]+)',ui['ExecStart']);assert match
cfg=json.loads(Path(match[1]).read_text());a=Path(cfg['runtime'])/'aura'
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:state=json.load(response)
value={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runtime':cfg['runtime'],'startup_config':match[1],
       'ui_service':ui,'camera_service':camera,'component_pins':len(cfg['component_sha256']),
       'component_hash_mismatches':[n for n,h in cfg['component_sha256'].items() if hashlib.sha256((a/n).read_bytes()).hexdigest()!=h],
       'state_keys':sorted(state),'phase':state.get('phase'),'audio_output_state':state.get('audio_output_state'),
       'listening':state.get('handsfree_dialogue',{}).get('enabled'),'microphone_open':state.get('handsfree_dialogue',{}).get('microphone_open'),
       'manual_pan':{k:state.get('manual_pan',{}).get(k) for k in ('state','pulse_us','automatic_following')},
       'portrait':state.get('portrait_offload'),'display':state.get('avatar_display'),'source_inspection':{}}
for name in ('config/board_identity.json','config/board_avatar_gtk.json'):
    path=a/name
    if path.exists():
        raw=json.loads(path.read_text());value['source_inspection'][name]={'keys':sorted(raw)}
        for key in ('backend','feature_backend','features','remote_features','audio_frontend','handsfree_dialogue','voice_first','portrait_offload'):
            if key in raw:value['source_inspection'][name][key]=raw[key]
for name in ('tools/voice_first_recording.py','tools/handsfree_recording.py','board/runtime/audio/voice_channel.py',
             'board/runtime/device_observer.py','board/runtime/visual_social.py','board/identity/backends.py',
             'board/identity/camera_faces.py','tools/streaming_controller.py'):
    path=a/name
    if path.exists():
        pattern=r'192\.168\.50|RemoteSpeechGate|VoiceFirst|VisualSocial|DeviceObserver|windows_sface|RemoteFaceFeatures|feature_backend|front_end|audio_frontend|wake_mode|wake_word|self\.observer|self\.social|self\.portrait'
        rows=[{'line':i,'code':line.strip()} for i,line in enumerate(path.read_text().splitlines(),1) if re.search(pattern,line)]
        value['source_inspection'][name]=rows[:24]
pid=camera['MainPID']
if pid!='0':value['camera_cmdline']=Path('/proc/'+pid+'/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
try:
 with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as response:camera_health=json.load(response)
 value['camera_health']={k:camera_health[k] for k in ('role','camera_error','detector_error','native_primary_deferred') if k in camera_health}
 for key in ('identity','detector'):
  data=camera_health.get(key,{})
  if isinstance(data,dict):value['camera_health'][key]={k:data[k] for k in ('ready','backend','model_id','processed','role','detail','kind','engine','name') if k in data}
except Exception as exc:value['camera_health_error']=type(exc).__name__+': '+str(exc)
print(json.dumps(value))
'''
try:report['board']=json.loads(ssh('python3 -B -',remote,timeout=25))
except Exception as exc:report['board']={'error':type(exc).__name__+': '+str(exc)[:350]}
report['device_commands_sent']=False;report['models_loaded_or_unloaded']=False;report['media_or_private_rows_read']=False
(H/'runtime_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checked_utc':report['checked_utc'],'windows_services':{p:{k:v[k] for k in ('ready','status','service_revision','revision','speaker_ready') if k in v} for p,v in report['windows_health'].items()},
 'board':{k:report['board'][k] for k in ('runtime','phase','component_pins','component_hash_mismatches','camera_health') if k in report['board']}},ensure_ascii=True))
