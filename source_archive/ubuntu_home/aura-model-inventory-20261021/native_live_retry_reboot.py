import fcntl,json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89760db2-7019-49c6-a379-b92fb98b8a5b'
s=json.loads((root/'state.json').read_text());assert s['phase']=='ARMED' and s['dependency_fix']['same_boot_retry_correctly_refused']
for unit in ['aura-camera-ui.service','aura-avatar-ui.service']:
 assert subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()=='0'
with open('/run/aura-person-dpu.lock','a+') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
subprocess.check_call(['systemd-run','--quiet','--unit=aura-native-retry-reboot-be72669aa53de735',
 '--on-active=2s','/bin/systemctl','reboot','--no-block'])
print(json.dumps({'second_controlled_reboot_scheduled':True,'failed_boot_evidence_retained':True,'no_same_boot_unlock':True}))
