"""Read actual /proc entry and next-start unit separately. No device mutations."""
import datetime,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

SCRIPT=r'''
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
def unit(name):
 return dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ExecStart','-p','NRestarts','-p','ActiveState','-p','DropInPaths'],text=True).splitlines() if '=' in line)
ui=unit('aura-avatar-ui.service');camera=unit('aura-camera-ui.service')
argv=Path('/proc/'+ui['MainPID']+'/cmdline').read_bytes().decode().split('\0')
path=Path(argv[argv.index('--config')+1]);cfg=json.loads(path.read_text());root=Path(cfg['runtime']);pins=cfg['component_sha256']
pending_args=re.search(r'argv\[\]=(.*?);',ui['ExecStart']).group(1).split()
pending=Path(pending_args[pending_args.index('--config')+1]);nextcfg=json.loads(pending.read_text())
actual_launcher=next(item for item in argv[:argv.index('--config')] if item.endswith('.py'))
pending_launcher=next(item for item in pending_args[:pending_args.index('--config')] if item.endswith('.py'))
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:s=json.load(response)
pan=s.get('manual_pan',{});hands=s.get('handsfree_dialogue',{})
safe=(s.get('phase')=='IDLE' and not s.get('playing',True) and s.get('audio_output_state')=='IDLE_READY'
 and hands.get('enabled') is False and hands.get('microphone_open') is False and not s.get('error')
 and pan.get('automatic_following') is False and pan.get('state') in ('READY','FAULT','HOLD','IDLE','DISABLED')
 and not any(pan.get(k) for k in ('busy','moving','active_motion','motion_active')) and not s.get('ui_settings',{}).get('pending',True))
ui_state={key:s.get(key) for key in ('phase','playing','audio_output_state','generation','portrait_offload','avatar_display','ui_tick_ms','audio_output')}
ui_state['ui_link']=s.get('ui_runtime',{}).get('link')
ui_state['camera_epoch']=s.get('ui_runtime',{}).get('snapshot',{}).get('preview',{}).get('camera_epoch')
print(json.dumps(dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),ui=ui,camera=camera,
 actual_config=str(path),actual_launcher=actual_launcher,actual_runtime=str(root),config=cfg,pins=pins,
 config_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
 pending_config=str(pending),pending_launcher=pending_launcher,pending=nextcfg,
 pending_config_sha256=hashlib.sha256(pending.read_bytes()).hexdigest(),
 pending_launcher_sha256=hashlib.sha256(Path(pending_launcher).read_bytes()).hexdigest(),
 mismatches=[name for name,sha in pins.items() if hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()!=sha],
 state=ui_state,
 listening=hands.get('enabled'),microphone_open=hands.get('microphone_open'),
 pan={k:pan.get(k) for k in ('state','pulse_us','target_us','automatic_following','busy','moving','active_motion','motion_active','backend_pid','error')},safe=safe,
 mechanical_sha256=hashlib.sha256((root/'aura/config/pan_manual.local.json').read_bytes()).hexdigest(),
 settings={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*_settings.json')},
 firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 fdt_sha256=hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest(),vart=Path('/etc/vart.conf').read_text().strip(),
 readonly=True),ensure_ascii=True))
'''

def capture():
    v=json.loads(ssh('python3 -B -',SCRIPT,timeout=25))
    v['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    return v

def same(before,after):
    assert after['safe'] and not after['mismatches'],'Idle/mic/motion/pins gate failed'
    for key in ('boot','actual_config','actual_launcher','actual_runtime','config_sha256','pins',
                'pending_config','pending_launcher','pending_config_sha256','pending_launcher_sha256',
                'settings','mechanical_sha256','firmware','fdt_sha256','vart'):
        assert after[key]==before[key],'Concurrent update: '+key
    for name in ('ui','camera'):
        for key in ('MainPID','ExecStart','DropInPaths','NRestarts','ActiveState'):
            assert after[name][key]==before[name][key],name+key

if __name__=='__main__':
    v=capture();name=sys.argv[1] if len(sys.argv)>1 else 'preflight.json'
    assert '/' not in name and '\\' not in name
    (H/name).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:v[key] for key in ('boot','actual_runtime','actual_config','pending_config','safe','listening','microphone_open','mismatches')},ensure_ascii=True))
    print(json.dumps({'pan_keys':list(v['pan']),'state':v['state']},ensure_ascii=True))
