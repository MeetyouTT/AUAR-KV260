import hashlib,json,subprocess
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='25b3d8ed-84e5-4a81-a2d6-6c8de1733a5f'
first=Path('/home/root/aura-post-power-20261022/helpers/15d8d8f6a596610a/source.py')
assert hashlib.sha256(first.read_bytes()).hexdigest()=='15d8d8f6a596610a77f26c555f92877f3dad11a4535881cf63b914b7c99c618d'
p=subprocess.run(['/usr/bin/python3','-B',str(first),'--arm'],capture_output=True,text=True,timeout=15)
assert p.returncode==0,p.stderr
armed=json.loads(p.stdout)
cold=Path('/home/root/aura-post-power-20261022/helpers/376e4921416108f4/source.py')
assert hashlib.sha256(cold.read_bytes()).hexdigest()=='376e4921416108f4b7be038c42b05a516ae76851ea03cce90f49736d0ab88566'
p=subprocess.run(['systemd-run','--no-block','--quiet','--unit=aura-deferred-cold-shutdown-376e4921416108f4',
 '--property=Type=oneshot','--property=RuntimeMaxSec=infinity','--property=TimeoutStopSec=infinity',
 '--property=SendSIGKILL=no','--property=KillMode=process','/usr/bin/python3','-B',str(cold),'--shutdown'],
 capture_output=True,text=True,timeout=8);assert p.returncode==0,p.stderr
print(json.dumps({'first_output_trial_armed':armed,'normal_shutdown_controller_started':True,
 'keep_hdmi_connected':True,'first60seconds_no_output_expected':True}))
