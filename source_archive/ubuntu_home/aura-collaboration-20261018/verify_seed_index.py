"""Verify all locally seeded files are accepted by the active sync index."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
from sync_api import API, alias, utc

WORK = Path(__file__).resolve().parent
api = API()
folder = next(row for row in api.folders() if alias(api.identity(row)) == '04087ac86d')
identity = api.identity(folder)
plan = json.loads((WORK/'local-seed-plan.json').read_text())
expected = {row['target']: row for row in plan['files'] if row['action'] == 'LOCAL_CONTENT_REUSE'}
created = [entry for path in WORK.glob('local-seed-attempt-*.json')
           for entry in json.loads(path.read_text())['created']]


def verify(row):
    info = api.call('/rest/db/file', {'folder': identity, 'file': row['path']})
    target = expected[row['path']]
    global_info, local = info.get('global') or {}, info.get('local') or {}
    flags = ('deleted', 'invalid', 'ignored', 'mustRescan')
    valid = (global_info.get('blocksHash') == local.get('blocksHash') == target['blocks_hash']
             and global_info.get('size') == local.get('size') == row['bytes']
             and not any(value.get(flag) for value in (global_info, local) for flag in flags))
    return {'path': row['path'], 'verified': valid, 'bytes': row['bytes'],
             'sha256_after_copy': row['sha256'], 'expected_blocks_hash': target['blocks_hash']}


with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(verify, created))
report = {'observed_utc': utc(), 'files': results,
          'created_files': len(results), 'index_accepted_count': sum(row['verified'] for row in results),
          'total_bytes': sum(row['bytes'] for row in results),
          'all_created_files_index_accepted': all(row['verified'] for row in results)}
path = WORK/('seed-index-validation-'+str(time.time_ns())+'.json')
path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({key: value for key, value in report.items() if key != 'files'}, ensure_ascii=False))
print(json.dumps({'saved': str(path)}))
