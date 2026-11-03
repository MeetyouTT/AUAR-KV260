"""Finish the previously successful network probe after metadata-only cleanup repair."""
import datetime,json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent
path=H/'board_probe.json'
report=json.loads(path.read_text(encoding='utf-8'))
assert report['status']=='FAIL' and 'started_unix' in report['cleanup_error']
assert 'error' not in report and len(report['turns'])==2
assert all(row['status']=='PASS' and row['sample_count']>0 and row['playback_ack_sent'] is False for row in report['turns'])
assert report['turns'][1]['backend']=='conversation_memory_command' and '绿色' in report['turns'][1]['reply']
cleanup=json.loads((H/'board_probe_cleanup.json').read_text(encoding='utf-8'))
assert cleanup['status']=='PASS' and cleanup['only_public_test_conversation_removed'] and cleanup['remaining_test_rows']==0
original=H/'board_probe_before_cleanup_fix.json'
assert not original.exists()
shutil.copy2(path,original)
report['cleanup_recovery']={'initial_status':'FAIL','initial_cleanup_error':report.pop('cleanup_error'),
 'reason':'Missing started_unix only affected empty digest build timestamp; ownership guards unchanged.',
 'rechecked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'network_probe_repeated':False}
report.update(status='PASS',cleanup=cleanup)
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'cleanup':cleanup['status'],'network_probe_repeated':False}))
