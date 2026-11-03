"""Build a content-index-checked local reuse plan for the pending voice mirror."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
from pathlib import Path
from sync_api import API, alias, utc

ROOT = Path('/home/ghmd/Win共享文件')
WORK = Path(__file__).resolve().parent
api = API()
folder = next(row for row in api.folders() if alias(api.identity(row)) == '04087ac86d')
identity = api.identity(folder)
need = api.call('/rest/db/need', {'folder': identity, 'page': 1, 'perpage': 10000})
entries = {row['name']: row for group in ('progress', 'queued', 'rest') for row in need.get(group) or []}


def usable(value):
    return bool(value.get('blocksHash')) and not any(value.get(key) for key in ('deleted', 'invalid', 'ignored'))


def inspect(relative):
    if not relative.startswith('语音共享文件/') or Path(relative).is_absolute() or '..' in Path(relative).parts:
        return {'target': relative, 'action': 'SKIP_SCOPE'}
    target = ROOT / relative
    if target.exists() or target.is_symlink():
        return {'target': relative, 'action': 'SKIP_ALREADY_EXISTS'}
    target_info = api.call('/rest/db/file', {'folder': identity, 'file': relative}).get('global') or {}
    if not usable(target_info):
        return {'target': relative, 'action': 'SKIP_NO_VALID_CONTENT_HASH'}
    suffix = relative.split('/', 1)[1]
    for prefix in ('共享文件夹/', ''):
        candidate = prefix + suffix
        path = ROOT / candidate
        if not path.is_file() or path.is_symlink() or path.stat().st_size != target_info.get('size'):
            continue
        value = api.call('/rest/db/file', {'folder': identity, 'file': candidate})
        source_info = value.get('local') or {}
        if (usable(source_info) and source_info['blocksHash'] == target_info['blocksHash']
                and source_info.get('numBlocks') == target_info.get('numBlocks')
                and source_info.get('size') == target_info.get('size')):
            return {'target': relative, 'source': candidate, 'action': 'LOCAL_CONTENT_REUSE',
                    'bytes': target_info['size'], 'blocks_hash': target_info['blocksHash'],
                    'num_blocks': target_info['numBlocks'], 'modified': target_info['modified'],
                    'permissions': target_info.get('permissions'), 'target_version': target_info.get('version')}
    return {'target': relative, 'action': 'WAIT_REMOTE_VERSION', 'bytes': target_info.get('size')}


plan = {'observed_utc': utc(), 'folder_alias': alias(identity), 'pending_count': len(entries), 'files': []}
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(inspect, relative): relative for relative in entries}
    for future in as_completed(futures):
        try:
            plan['files'].append(future.result())
        except Exception as error:
            plan['files'].append({'target': futures[future], 'action': 'INSPECTION_ERROR', 'error': type(error).__name__})
        if len(plan['files']) % 250 == 0:
            print(json.dumps({'inspected': len(plan['files']), 'total': len(entries)}), flush=True)
plan['files'].sort(key=lambda row: row['target'])
plan['reusable_count'] = sum(row['action'] == 'LOCAL_CONTENT_REUSE' for row in plan['files'])
plan['reusable_bytes'] = sum(row.get('bytes', 0) for row in plan['files'] if row['action'] == 'LOCAL_CONTENT_REUSE')
plan['remaining_remote_count'] = sum(row['action'] == 'WAIT_REMOTE_VERSION' for row in plan['files'])
target = WORK / 'local-seed-plan.json'
target.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({key: value for key, value in plan.items() if key != 'files'}, ensure_ascii=False), flush=True)
