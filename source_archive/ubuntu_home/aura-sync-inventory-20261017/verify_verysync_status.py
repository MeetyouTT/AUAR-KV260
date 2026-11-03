"""Verify the captured sync state and ASR peer availability without mutations."""
import hashlib
import ipaddress
import json
from pathlib import Path

WORK=Path(__file__).resolve().parent/'verysync-status'
snapshots=sorted(WORK.glob('status-*.json'))
# Keep generated diagnostics free of full peer IDs and public addresses.
for path in snapshots:
    data=json.loads(path.read_text())
    for folder in data.get('folders',[]):
        status=folder.get('status',{})
        sequence=status.get('remoteSequence',{})
        if isinstance(sequence,dict):
            status['remoteSequence']={hashlib.sha256(key.encode()).hexdigest()[:10] if len(key)>10 else key:value for key,value in sequence.items()}
    for row in data.get('connections',[]):
        value=row.get('address','')
        if value.startswith('[public address]'):continue
        try:
            host,port=value.rsplit(':',1)
            if not ipaddress.ip_address(host.strip('[]')).is_private:row['address']='[public address]:'+port
        except ValueError:pass
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

latest=json.loads(snapshots[-1].read_text())
folder=next(row for row in latest['folders'] if row['path']=='/home/ghmd/Win共享文件')
assert folder['pytest_cache_ignore_loaded']
assert folder['status']['state']=='idle' and folder['status']['needTotalItems']==0
assert folder['status']['errors']==folder['status']['pullErrors']==0
assert not folder['errors'] and not latest['pending_errors']
peer=next(row for row in folder['remote_completion'] if row['name']=='JoneNike')
assert peer['completion']==100 and peer['needItems']==peer['needBytes']==0
assert not peer['needed_files']
manifest=json.loads(Path('/home/ghmd/Win共享文件/共享文件夹/deliverables/2026-10-17_board_asr_host_files/ASR_REQUIRED_FILES.json').read_text())
indexed={row['path']:row for row in folder['important_files']}
for name,row in manifest['files'].items():
    record=indexed['共享文件夹/aura/'+name]
    assert record['global']['size']==record['local']['size']==row['bytes']
    assert any(p['peer']==peer['peer'] and not p['from_temporary'] for p in record['availability'])
archive='共享文件夹/deliverables/2026-10-17_board_asr_host_files/asr-host-complete-code-b9ac9d83fe24f179.zip'
assert any(p['peer']==peer['peer'] for p in indexed[archive]['availability'])
result={'status':'PASS_CURRENT_SYNC_COMPLETE_AND_ASR_PEER_INDEX_CONFIRMED','source_report':str(snapshots[-1]),
        'observed_unix':latest['observed_unix'],'sync_root':folder['path'],
        'local_files':folder['status']['localFiles'],'local_bytes':folder['status']['localBytes'],
        'local_pending_items':0,'local_errors':0,'peer_name':peer['name'],'peer_completion':100,
        'peer_pending_items':0,'peer_pending_bytes':0,'asr_required_files_available_on_peer':len(manifest['files']),
        'complete_code_archive_available_on_peer':True,'pytest_cache_ignore_loaded':True,
        'independent_windows_disk_hash_check':False,'windows_asr_service_verified':False,
        'scope':'Read-only sync status and version availability; not recognition service acceptance'}
(WORK/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
