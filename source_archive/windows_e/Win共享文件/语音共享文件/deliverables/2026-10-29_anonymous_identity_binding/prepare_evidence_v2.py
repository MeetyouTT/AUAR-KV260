"""Produce an incremental overlay, preserving the frozen v1 source verbatim."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent/'2026-10-29_speaker_visual_cooperation'
source=B/'candidate/common/speaker_turns.py';raw=source.read_bytes()
expected=json.loads((B/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))['files']['common/speaker_turns.py']['sha256']
assert hashlib.sha256(raw).hexdigest()==expected
extra='''

# v2 is an additive descriptor for explicitly enabled temporary voice clustering.
# v1 callers and their strict fields are preserved; no biometric vector crosses IPC.
_v1_record=record
_v1_validate_record=validate_record

def validate_record(value,meta,cid):
    if isinstance(value,dict) and value.get('version')==2:
        from common.anonymous_voice import validate_alias
        if set(value)!=FIELDS|{'anonymous'}:raise ValueError('Unexpected v2 speaker fields')
        if value.get('status')!='COMPLETE':raise ValueError('Only completed analysis may carry an alias')
        base=dict(value);alias=base.pop('anonymous');base['version']=1
        result=_v1_validate_record(base,meta,cid)
        result.update(version=2,anonymous=validate_alias(alias,meta))
        return result
    return _v1_validate_record(value,meta,cid)

def record(meta,cid,*,status='PENDING',reason='ANALYSIS_PENDING',voice=None,visual=None,anonymous=None):
    value=_v1_record(meta,cid,status=status,reason=reason,voice=voice,visual=visual)
    if anonymous is not None:
        value.update(version=2,anonymous=anonymous)
        return validate_record(value,meta,cid)
    return value
'''
target=H/'candidate/common/speaker_turns.py';target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes(raw+extra.encode())
(H/'v1_evidence_baseline.json').write_text(json.dumps({'source':str(source),'sha256':expected,'v1_bytes_preserved':True},indent=2),encoding='utf-8')
print(json.dumps({'status':'STAGED','v1_bytes_preserved':True,'production_changed':False}))
