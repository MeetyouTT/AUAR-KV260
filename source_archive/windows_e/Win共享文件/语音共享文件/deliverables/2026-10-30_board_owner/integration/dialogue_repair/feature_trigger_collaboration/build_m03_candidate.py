"""Create isolated M03 adapter against v17; no existing Store/schema is changed."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
DEST=H/'candidate_m03'
BASE=H/'board_integration_v17/local_runtime_v17'


def once(source,old,new):
    if source.count(old)!=1:raise ValueError('Non-unique anchor: '+old[:80])
    return source.replace(old,new)


def main():
    draft=(H/'candidate_v4/after/board/runtime/feature_capabilities.py').read_text(encoding='utf-8')
    begin=draft.index('class LocalReasoningDialogue:');end=draft.index('class LocalHistoryDelete:')
    source=draft[:begin]+draft[end:]
    source=source.replace('from common.thinking_policy import route as thinking_route\n','')
    source=source.replace('import re\n','import re\nimport hashlib\nimport json\n')
    # Existing synthetic Timeline test doubles expose event_time only. The
    # caller still supplies the exact original explicit mono clock; real v17
    # timelines expose monotonic, whose identity must continue to match.
    source=once(source,'timeline.monotonic is not clock',"getattr(timeline, 'monotonic', clock) is not clock")
    methods=(DEST/'store_adapter_methods.txt').read_text(encoding='utf-8')
    source=once(source,'    def __call__(self, text, *, job, controller, is_current, cancel_event):',methods+'\n    def __call__(self, text, *, job, controller, is_current, cancel_event):')
    source=source.replace('self.store.preview_transcript_delete(', 'self._preview(')
    source=source.replace('self.store.confirm_transcript_delete(', 'self._confirm(')
    source=once(source,"                        fingerprint=snapshot['fingerprint'], generation=job.meta['generation'],",
        "                        fingerprint=snapshot['fingerprint'], generation=job.meta['generation'],\n                        preview_turn_id=job.meta['request_id'],")
    source=once(source,"                    operation_turn_id=job.meta['request_id'])\n                current()",
        "                    operation_turn_id=job.meta['request_id'], preview_turn_id=pending['preview_turn_id'])\n                current()")
    source=once(source,"                    snapshot = self._preview(job.scope, start=selected['start'], end=selected['end'],\n                        operation_turn_id=job.meta['request_id'])",
        "                    try:\n                        snapshot = self._preview(job.scope, start=selected['start'], end=selected['end'],\n                            operation_turn_id=job.meta['request_id'])\n                    except DeletePreviewTooLarge:\n                        return SourcedBoardReply('所选范围超出本次预览限量，本轮没有删除。')")
    source=once(source,'class LocalHistoryDelete:', 'class DeletePreviewTooLarge(ValueError):\n    pass\n\n\nclass LocalHistoryDelete:')
    source=once(source,"                if result['status'] != 'deleted':", "                if result['status'] == 'preview_not_played':\n                    return SourcedBoardReply('上一轮预览未完成完整播放确认，没有删除，请重新预览。')\n                if result['status'] != 'deleted':")
    new=DEST/'after/board/runtime/history_delete.py';new.parent.mkdir(parents=True,exist_ok=True)
    ast.parse(source,feature_version=(3,9));new.write_text(source,encoding='utf-8')
    relative='board/runtime/board_business.py';raw=(BASE/relative).read_bytes()
    before=raw.decode().replace('\r\n','\n')
    after=once(before,'        handlers = dict(extra_handlers or {})',
        "        handlers = dict(extra_handlers or {})\n        from board.runtime.history_delete import LocalHistoryDelete\n        handlers.setdefault('history_delete_preview', LocalHistoryDelete(self.store, self.timeline, clock=clock, zone=config.timezone))")
    old=DEST/'before'/relative;old.parent.mkdir(parents=True,exist_ok=True);old.write_bytes(raw)
    path=DEST/'after'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(after,encoding='utf-8')
    (DEST/'board_business.py.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
        fromfile='before/'+relative,tofile='after/'+relative)),encoding='utf-8')
    pins=json.loads((H/'board_integration_v17/source_mapping.json').read_bytes())['component_pins']
    assert hashlib.sha256(raw).hexdigest()==pins[relative]
    files={relative:dict(before_sha256=pins[relative],sha256=hashlib.sha256(after.encode()).hexdigest(),source=str(path)),
        'board/runtime/history_delete.py':dict(before_sha256=None,sha256=hashlib.sha256(new.read_bytes()).hexdigest(),source=str(new))}
    (DEST/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(status='LOCAL_CANDIDATE_NOT_DEPLOYED',
        baseline_startup_sha256='0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a',files=files,
        original_store_schema_unchanged=True,original_profile_access_and_forgetting_used=True,
        preview_requires_full_playback_ack=True,preview_ttl_monotonic_seconds=60,
        supported_dates='explicit single day only',new_private_database_or_auth=False,
        conflicts='board_business.py binding hunk overlaps D01; root merge must retain both setdefault registrations',
        board_memory_policy_modified=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    combined=H/'candidate_h01_d01_m03/after'
    for path in (H/'candidate_h01_d01/after').rglob('*.py'):
        rel=path.relative_to(H/'candidate_h01_d01/after');dest=combined/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        data=path.read_bytes()
        if rel.as_posix()==relative:
            data=once(data.decode(),'        handlers = dict(extra_handlers or {})',
                "        handlers = dict(extra_handlers or {})\n        from board.runtime.history_delete import LocalHistoryDelete\n        handlers.setdefault('history_delete_preview', LocalHistoryDelete(self.store, self.timeline, clock=clock, zone=config.timezone))").encode()
        dest.write_bytes(data)
    dest=combined/'board/runtime/history_delete.py';dest.write_bytes(new.read_bytes())
    print(json.dumps(files,ensure_ascii=False))


if __name__=='__main__':main()
