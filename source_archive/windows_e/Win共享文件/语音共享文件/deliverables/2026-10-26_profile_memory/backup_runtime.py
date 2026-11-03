"""Consistent private runtime backup; report contains metadata only."""
import datetime,hashlib,json,sqlite3,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
runtime=HERE.parent/'2026-10-18_board_dialogue/model_host'
source=runtime/'conversations.sqlite3'
target=runtime/('conversations.before-profiles-'+uuid.uuid4().hex+'.sqlite3')
assert source.is_file() and not target.exists()
with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as original:
    with sqlite3.connect(target) as backup:
        original.backup(backup)
        assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
value={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'backup_path':str(target),'backup_bytes':target.stat().st_size,
       'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
       'integrity':'ok','private_runtime_only':True,'included_in_source_package':False}
(HERE/'database_backup.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({'backup_created':True,'integrity':'ok','bytes':value['backup_bytes']}))
