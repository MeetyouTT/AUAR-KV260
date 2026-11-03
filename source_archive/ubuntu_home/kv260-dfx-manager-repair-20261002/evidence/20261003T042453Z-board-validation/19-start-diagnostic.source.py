import os,json,subprocess
from pathlib import Path
assert os.geteuid()==0
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
print('UPTIME '+Path('/proc/uptime').read_text(),flush=True)
for a in [['systemctl','status','dfx-mgr.service','--no-pager','-l'],['systemctl','show','dfx-mgr.service','--property=MainPID,ActiveState,SubState,Result,ExecMainStatus,ExecStart,DropInPaths'],['journalctl','-u','dfx-mgr.service','--no-pager','-n','120','-o','short-monotonic']]:
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 print('DIAGNOSTIC '+json.dumps({'argv':a,'rc':p.returncode,'output':p.stdout}),flush=True)
m=Path('/sys/module/zocl')
s={'srcversion':(m/'srcversion').read_text().strip() if m.exists() else None,'refcnt':(m/'refcnt').read_text().strip() if m.exists() else None,'fpga_state':Path('/sys/class/fpga_manager/fpga0/state').read_text(),'fpga_firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode() if Path('/proc/device-tree/fpga-full/firmware-name').exists() else None,'device_exists':Path('/sys/bus/platform/devices/axi:zyxclmm_drm').exists(),'socket_exists':Path('/tmp/dfx-mgrd.socket').exists()}
print('CURRENT '+json.dumps(s),flush=True)
log=Path('/home/root/kv260-dfx-manager-repair-20261003T042453Z/candidate-manager.log')
print('CANDIDATE_LOG_BEGIN',flush=True)
print(log.read_text(errors='replace') if log.exists() else 'NO LOG',flush=True)
print('CANDIDATE_LOG_END',flush=True)
print('KERNEL_BEGIN',flush=True)
subprocess.run(['dmesg'],check=True)
print('KERNEL_END',flush=True)
