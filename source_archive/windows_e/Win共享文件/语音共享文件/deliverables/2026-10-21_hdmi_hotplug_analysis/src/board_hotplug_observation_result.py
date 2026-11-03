"""Read passive HDMI observation artifacts; no display control or finish signal."""
import json,subprocess
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
root=Path('/run/aura-hdmi-physical-hotplug-v2-20261021')/boot
v={'boot_id':boot,'display_control_writes':0,'movement_commands_sent':0}
for name in ['state.json','result.json','changes.json']:
 p=root/name
 if p.exists():v[name]=json.loads(p.read_text())
v['observer_unit']=subprocess.run(['systemctl','show','aura-hdmi-hotplug-v2-'+boot[:8]+'.service','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5).stdout
old=Path('/run/aura-hdmi-physical-hotplug-20261021')/boot
if (old/'result.json').exists():
 d=json.loads((old/'result.json').read_text())
 v['invalid_off_baseline_observation']={k:d.get(k) for k in ['boot_id','samples','cached_changes','finish_requested','events','display_control_writes']}
print(json.dumps(v),flush=True)
