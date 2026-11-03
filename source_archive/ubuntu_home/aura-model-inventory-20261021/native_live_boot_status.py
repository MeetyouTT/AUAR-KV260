import json,subprocess,time
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
units={}
for name in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service','aura-native-rescue-be72669aa53de735.timer']:
 text=subprocess.check_output(['systemctl','show',name,'-p','ActiveState','-p','SubState','-p','MainPID','-p','Result'],text=True)
 units[name]=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'uptime':Path('/proc/uptime').read_text().split()[0],'state':json.loads((root/'state.json').read_text()),'units':units}))
