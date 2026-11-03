"""Prepare, never apply, the normal-entry single-writer gate for root."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
path=PROJECT/'deliverables/2026-10-18_board_dialogue/start_background_models.ps1'
raw=path.read_bytes();source=raw.decode('utf-8-sig')
anchor='$modelProject=Split-Path -Parent (Split-Path -Parent $modelTaskRoot)'
assert source.count(anchor)==1
gate=r'''
$businessOwnerPath=Join-Path $modelProject 'aura/config/business_owner.local.json'
if(Test-Path -LiteralPath $businessOwnerPath){
    $businessOwnerFile=Get-Item -LiteralPath $businessOwnerPath -ErrorAction Stop
    if($businessOwnerFile.PSIsContainer -or $businessOwnerFile.Length -gt 16384){throw 'Business owner marker is invalid; legacy services remain stopped'}
    $businessOwner=Get-Content -Raw -Encoding UTF8 -LiteralPath $businessOwnerPath | ConvertFrom-Json
    if($businessOwner.schema_version -ne 1 -or $businessOwner.owner -notin @('board','windows')){throw 'Unknown business owner; legacy services remain stopped'}
    if($businessOwner.owner -eq 'board'){
        throw 'Board owns ASR, identity, memory and dialogue business. Do not start old Windows 8791/8792/8795 or device business; use project start_inference.ps1 for model execution only.'
    }
}
'''
pending=source.replace(anchor,anchor+gate,1).encode('utf8')
(HERE/'start_background_models.before.ps1').write_bytes(raw)
(HERE/'start_background_models.pending.ps1').write_bytes(pending)
owner=dict(schema_version=1,owner='board',handover_manifest=dict(path=None,sha256=None))
(HERE/'business_owner.pending.json').write_text(json.dumps(owner,indent=2)+'\n',encoding='utf8')
receipt=dict(status='PREPARED_NOT_APPLIED_WAITING_FOR_ROOT_SINGLE_WRITER_HANDOVER',
    target='deliverables/2026-10-18_board_dialogue/start_background_models.ps1',
    before_sha256=hashlib.sha256(raw).hexdigest(),pending_sha256=hashlib.sha256(pending).hexdigest(),
    owner_marker_target='aura/config/business_owner.local.json',owner_marker_root_must_fill_handover_manifest=True,
    default_start_voice_applied=False,legacy_direct_python_fixtures_changed=False,
    gate_precedes_any_configuration_or_process_start=True)
(HERE/'business_gate_prepared.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
print(json.dumps(receipt))
