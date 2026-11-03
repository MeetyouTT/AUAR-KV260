import hashlib,json,subprocess
from pathlib import Path
source=Path('/home/root/aura-post-power-20261022/helpers/c6b338dc8423086d/source.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='c6b338dc8423086d6bef3754bbc569fe3f7e04b6b9efdf57f28147c0c3ec3d25'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
assert Path('/home/root/aura-native-coldboot-20261024/c6b338dc8423086d/prepared.json').exists()
p=subprocess.run(['systemd-run','--no-block','--quiet','--unit=aura-native-cold-shutdown-c6b338dc8423086d',
 '--property=Type=oneshot','--property=RuntimeMaxSec=infinity','--property=TimeoutStopSec=infinity',
 '--property=SendSIGKILL=no','--property=KillMode=process','/usr/bin/python3','-B',str(source),'--shutdown'],
 capture_output=True,text=True,timeout=8)
assert p.returncode==0,p.stderr
print(json.dumps({'normal_shutdown_controller_started':True,'human_should_wait_before_unplugging':True,
 'report':'/home/root/aura-native-coldboot-20261024/c6b338dc8423086d/shutdown.json'}))
