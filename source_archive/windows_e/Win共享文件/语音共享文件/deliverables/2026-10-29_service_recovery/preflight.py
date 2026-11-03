"""Capture this boot and source identity; back up current data, never restore old."""
import datetime,hashlib,json,shutil,time
from recovery_common import H,P,A,board,windows,same_board,checkpoint,save
from common.voice_service_capabilities import source_fingerprint,SOURCE_FILES,SERVICE_REVISION
assert not (H/'baseline.json').exists(),'Inspect existing recovery receipt before repeating'
accepted=json.loads((H.parent/'2026-10-29_chat_latency/PROGRESS.json').read_text(encoding='utf-8'))
fingerprint=source_fingerprint(A);assert fingerprint==accepted['fingerprint'] and SERVICE_REVISION==accepted['revision']
for name in ('db_checkpoint.py','start_checkpoint.ps1'):
 source=(H.parent/'2026-10-29_chat_latency'/name).read_text(encoding='utf-8')
 if name=='db_checkpoint.py':source=source.replace('chatlatency-20261029-','service-recovery-20261029-')
 (H/name).write_text(source,encoding='utf-8')
first=board();assert first['preflight_ready']
time.sleep(.25);same_board(board(),first)
win=windows();assert any(row['IPAddress']=='192.168.50.1' for row in win['ipv4'])
assert not any(row['LocalPort'] in (8791,8792,8795,8796,8810,8812) for row in win['listeners']),'Inspect existing service before recovery'
value={'status':'READY_TO_RECOVER','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'revision':SERVICE_REVISION,'fingerprint':fingerprint,'board':first,'windows':win,
 'source_sha256':{name:hashlib.sha256((A/name).read_bytes()).hexdigest() for name in SOURCE_FILES},
 'model_storage_sha256':hashlib.sha256((A/'config/model_storage.local.json').read_bytes()).hexdigest(),
 'database_before':checkpoint('before'),'source_deployment':False,'microphone_enabled':False,
 'physical_playback':False,'motion_enabled':False,'board_restarted':False,'models_stopped':False}
same_board(board(),first);save('baseline.json',value)
print(json.dumps({'status':value['status'],'revision':SERVICE_REVISION,'windows_last_boot':win['last_boot'],
 'board_boot':first['boot'],'runtime':first['actual_runtime'],'pins':len(first['pins']),
 'pan':first['pan'],'original_databases':{k:v.get('counts') for k,v in value['database_before']['databases'].items()}},ensure_ascii=True))
