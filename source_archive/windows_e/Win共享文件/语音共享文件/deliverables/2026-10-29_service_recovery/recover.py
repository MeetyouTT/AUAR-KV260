"""Recover existing Windows services through their original hidden launchers."""
import datetime,hashlib,json,subprocess
from recovery_common import H,P,A,read,save,board,same_board,windows
baseline=read('baseline.json');assert baseline['status']=='READY_TO_RECOVER'
assert not (H/'recovery.json').exists(),'Inspect existing recovery receipt before repeating'
same_board(board(),baseline['board']);same_board(board(),baseline['board'])
for name,digest in baseline['source_sha256'].items():assert hashlib.sha256((A/name).read_bytes()).hexdigest()==digest,name
assert hashlib.sha256((A/'config/model_storage.local.json').read_bytes()).hexdigest()==baseline['model_storage_sha256']
current=windows();assert not any(r['LocalPort'] in (8791,8792,8795,8796,8810,8812) for r in current['listeners'])
receipt={'status':'STARTING_EXISTING_SERVICES','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'revision':baseline['revision'],'fingerprint':baseline['fingerprint'],'source_changed':False,
 'board_restarted':False,'bindings_changed':False,'microphone_enabled':False,'physical_playback':False,
 'motion_enabled':False,'existing_models_stopped':False,'launcher':str(P/'start_voice.ps1')}
save('recovery.json',receipt)
try:
 with (H/'start_voice_console.log').open('wb') as output:
  completed=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(P/'start_voice.ps1')],
   stdout=output,stderr=subprocess.STDOUT,timeout=540,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 assert completed.returncode==0,'Original launcher failed; inspect start_voice_console.log and owned service logs'
 same_board(board(),baseline['board'])
 receipt.update(status='RESTORED_PENDING_VALIDATION',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as exc:
 receipt.update(status='RECOVERY_NEEDS_INSPECTION',error=type(exc).__name__+': '+str(exc),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 save('recovery.json',receipt);raise
save('recovery.json',receipt)
print(json.dumps({'status':receipt['status'],'revision':receipt['revision'],'source_changed':False,'board_restarted':False}))
