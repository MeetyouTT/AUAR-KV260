import base64,hashlib,json,subprocess
from pathlib import Path
def run(args):return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5).stdout.strip()
working=Path(run(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value']))
assert working==Path('/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/runtime/aura')
root=working.parent.parent
config=root/'startup/config.json';launcher=root/'startup/launcher.py'
value=json.loads(config.read_text())
marker=Path(value['display_recovery_marker'])
report={'status':'READ_ONLY_HDMI_BOOT_CONFIG','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'service_enabled':run(['systemctl','is-enabled','aura-avatar-ui.service']),
 'service_state':run(['systemctl','is-active','aura-avatar-ui.service']),
 'exec_start':run(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value']),
 'config_path':str(config),'display_config':{k:value[k] for k in ('startup_display_retrain','display_retrain_off_seconds','edid_grace_seconds','display_stable_seconds','display_recovery_marker','output','mode','rate')},
 'marker':json.loads(marker.read_text()) if marker.exists() else None,
 'artifacts':{}}
for name,p in [('actual-config.json',config),('actual-launcher.py',launcher)]:
 data=p.read_bytes();report['artifacts'][name]={'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
print(json.dumps(report),flush=True)
