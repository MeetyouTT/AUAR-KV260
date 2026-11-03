"""Create only two isolated H01 source candidates from exact public v17 bytes."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

H = Path(__file__).resolve().parent
DEST = H/'candidate_h01'
BASE = H/'board_integration_v17/local_runtime_v17'


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Non-unique edit anchor: '+old[:120])
    return source.replace(old, new)


def memory(source):
    for name in ('history', 'history_with_status', '_history_query'):
        source = once(source,
            'def '+name+'(self, scope, *, start=None, end=None, topic=None, search=None, limit=20):',
            'def '+name+'(self, scope, *, start=None, end=None, topic=None, search=None, limit=20, exclude_event_ids=()):')
    source = source.replace('self._history_query(scope, start=start, end=end, topic=topic, search=search, limit=limit)',
        'self._history_query(scope, start=start, end=end, topic=topic, search=search, limit=limit, exclude_event_ids=exclude_event_ids)')
    source = once(source, '        start = 0 if start is None else _time(start)',
        '''        if not isinstance(exclude_event_ids, (tuple, list)) or len(exclude_event_ids) > 16:
            raise ValueError("Invalid internal history exclusions")
        excluded = tuple(sorted({_identifier(value, "excluded event id") for value in exclude_event_ids}))
        # Current query sources are filtered before SQL LIMIT and match counts.
        # A summary referring to an excluded source is excluded as one unit.
        marks = ",".join("?" for _ in excluded)
        detail_exclusion = " AND e.event_id NOT IN (" + marks + ")" if excluded else ""
        summary_exclusion = (" AND NOT EXISTS (SELECT 1 FROM bm_summary_sources excluded WHERE "
            "excluded.summary_id=s.summary_id AND excluded.event_id IN ("+marks+"))") if excluded else ""
        start = 0 if start is None else _time(start)''')
    source = once(source, 'tuple(summary_values) + (limit,)', 'tuple(summary_values) + excluded + (limit,)')
    source = once(source, 'tuple(detail_values) + (limit,)', 'tuple(detail_values) + excluded + (limit,)')
    source = once(source, 'summary_search + " ORDER BY s.end_utc DESC LIMIT ?"',
                  'summary_search + summary_exclusion + " ORDER BY s.end_utc DESC LIMIT ?"')
    source = once(source, 'detail_search +\n                                " ORDER BY e.recorded_utc DESC LIMIT ?"',
                  'detail_search + detail_exclusion +\n                                " ORDER BY e.recorded_utc DESC LIMIT ?"')
    source = once(source, 'summary_search, args[:-1]', 'summary_search + summary_exclusion, args[:-1]')
    source = once(source, 'detail_search, detail_args[:-1]', 'detail_search + detail_exclusion, detail_args[:-1]')
    source = once(source, 'tuple(summary_values)\n            overlaps', 'tuple(summary_values) + excluded\n            overlaps')
    source = once(source, 'summary_search, overlap_args)', 'summary_search + summary_exclusion, overlap_args)')
    return source


def dialogue(source):
    return once(source, 'self.store.history_with_status(turn.scope, **history_query)',
        'self.store.history_with_status(turn.scope, exclude_event_ids=(turn.user_event_id,), **history_query)')


def main():
    pins = json.loads((H/'board_integration_v17/source_mapping.json').read_bytes())['component_pins']
    files = {}
    for relative, edit in [('common/board_memory.py', memory), ('board/runtime/board_dialogue.py', dialogue)]:
        raw = (BASE/relative).read_bytes()
        before_sha = hashlib.sha256(raw).hexdigest()
        if before_sha != pins[relative]:
            raise ValueError('v17 baseline changed')
        before = raw.decode('utf-8').replace('\r\n', '\n')
        after = edit(before)
        ast.parse(after, feature_version=(3,9))
        for kind,data in [('before',raw),('after',after.encode('utf-8'))]:
            path = DEST/kind/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (DEST/(Path(relative).name+'.patch')).write_text(''.join(difflib.unified_diff(
            before.splitlines(True),after.splitlines(True),fromfile='before/'+relative,tofile='after/'+relative)),encoding='utf-8')
        files[relative] = dict(before_sha256=before_sha,sha256=hashlib.sha256(after.encode()).hexdigest(),
                               source=str(DEST/'after'/relative))
    (DEST/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(status='LOCAL_CANDIDATE_NOT_DEPLOYED',
        purpose='H01 exclude current query at authorized SQL source selection before LIMIT/counts',
        baseline_startup_sha256='0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a',
        files=files,original_budget_2048_unchanged=True,board_memory_policy_modified=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(files,ensure_ascii=False))


if __name__ == '__main__':
    main()
