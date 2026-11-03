"""Idle-only update of two owned host files, with automatic source rollback."""
import hashlib,json,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path[:0]=[str(A),str(H.parent/'2026-10-18_board_dialogue')]
from board_ssh import ssh
c=json.loads((H/'candidate.json').read_text());assert json.loads((H/'deployment.json').read_text())['status']=='COMMITTED'
def health():
 with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4) as f:return json.load(f)
def gate():
 script=r'''
import json,subprocess,time,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert STARTUP in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
for _ in range(2):
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:s=json.load(f)
 assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY'
 assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue']['microphone_open']
 assert not s['manual_pan']['automatic_following'] and s['manual_pan']['pulse_us'] is None and s['manual_pan']['state']=='FAULT'
 time.sleep(.3)
print('IDLE_PAUSED')
'''.replace('BOOT',repr(c['boot'])).replace('STARTUP',repr(c['startup']))
 assert ssh('python3 -B -',script).strip()=='IDLE_PAUSED'
def stop_owned():
 command=r'''
$ErrorActionPreference='Stop'
$processes=Get-CimInstance Win32_Process
$targets=@($processes | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*E:\Win共享文件\语音共享文件\aura\tools\board_model_host.py*'})
$ownedIds=@($targets | ForEach-Object {$_.ProcessId})
if ($ownedIds.Count -gt 2) {throw 'Unexpected duplicate voice owners'}
$listeners=@(Get-NetTCPConnection -State Listen -LocalPort 8792 -ErrorAction SilentlyContinue)
if (@($listeners | Where-Object {$_.OwningProcess -notin $ownedIds}).Count) {throw 'Unknown voice listener; preserve it'}
do {
 $children=@($processes | Where-Object {$_.ParentProcessId -in $ownedIds -and $_.ProcessId -notin $ownedIds})
 $ownedIds+=@($children | ForEach-Object {$_.ProcessId})
} while ($children.Count)
if (@($processes | Where-Object {$_.ProcessId -in $ownedIds -and $_.Name -notin @('python.exe','pythonw.exe','conhost.exe')}).Count) {throw 'Unknown child; preserve it'}
if (@($processes | Where-Object {$_.ProcessId -in $ownedIds -and $_.Name -eq 'conhost.exe' -and $_.ExecutablePath -ne 'C:\Windows\System32\conhost.exe'}).Count) {throw 'Unknown console owner; preserve it'}
$ownedIds=@($processes | Where-Object {$_.ProcessId -in $ownedIds -and $_.Name -in @('python.exe','pythonw.exe')} | ForEach-Object {$_.ProcessId})
[array]::Reverse($ownedIds)
foreach ($voiceId in $ownedIds) {Stop-Process -Id $voiceId -Force -ErrorAction SilentlyContinue}
@{stopped_owned_python_ids=$ownedIds;ollama_stopped=$false} | ConvertTo-Json -Compress
'''
 return json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True,encoding='utf-8',timeout=30))
def launch():
 result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(H.parent/'2026-10-18_board_dialogue/start_background_models.ps1')],capture_output=True,timeout=460)
 (H/'host_restart_launch.log').write_bytes(result.stdout+result.stderr)
 if result.returncode:raise RuntimeError('Voice startup failed; inspect host_restart_launch.log')
 return health()
def save(value):(H/'host_hotfix.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
gate();before=health();assert before['ready'] and not before['busy']
assert before['service_revision']=='voice-device-skills-20261028-r4'
names=['tools/board_model_host.py','common/voice_service_capabilities.py']
receipt={'status':'PREPARED','files':{},'before_revision':before['service_revision'],'before_fingerprint':before['source_fingerprint']}
for name in names:
 source=A/name;backup=H/'before_host_r5'/name;backup.parent.mkdir(parents=True,exist_ok=True)
 if backup.exists():assert backup.read_bytes()==source.read_bytes(),'Do not overwrite an existing rollback source'
 else:shutil.copy2(source,backup)
 receipt['files'][name]={'before':hashlib.sha256(source.read_bytes()).hexdigest(),'after':hashlib.sha256((H/'candidate_source'/name).read_bytes()).hexdigest()}
save(receipt)
try:
 gate();assert not health()['busy']
 receipt['stop']=stop_owned()
 for name in names:shutil.copy2(H/'candidate_source'/name,A/name)
 receipt['status']='STARTING';save(receipt)
 after=launch()
 assert after['ready'] and after['service_revision']=='voice-device-skills-20261028-r5'
 receipt.update(status='READY',after_revision=after['service_revision'],after_fingerprint=after['source_fingerprint'])
except Exception as exc:
 receipt['error']=type(exc).__name__+': '+str(exc)
 if 'stop' not in receipt:
  receipt['status']='ABORTED_WITHOUT_CHANGES';save(receipt);raise
 stop_owned()
 for name in names:shutil.copy2(H/'before_host_r5'/name,A/name)
 restored=launch();receipt.update(status='ROLLED_BACK',restored_revision=restored['service_revision'])
 save(receipt);raise
save(receipt);print(json.dumps(receipt))
