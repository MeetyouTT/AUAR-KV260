"""Preserve the deployed query source before a bounded speech routing repair."""
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=HERE.parent/'2026-10-19_spoken_identity_query'
files=('aura/common/voice_enrollment.py','aura/common/spoken_input.py',
       'aura/board/runtime/audio/channel_jobs.py','aura/tools/board_model_host.py',
       'aura/tests/framework/test_spoken_identity_query.py',
       'aura/tests/framework/test_channel_jobs.py')
for name in files:
    target=HERE/'before'/name
    if target.exists():raise RuntimeError('Existing repair backup must not be overwritten')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/name,target)
for name in ('prepare.py','preflight.py','activate.py','verify_and_archive.py',
             'reload_voice_host.ps1','rollback.py','probe_voice_host.py','status.py'):
    raw=(OLD/name).read_text(encoding='utf-8')
    raw=raw.replace('/home/root/aura-spoken-identity-query-20261019',
                    '/home/root/aura-spoken-identity-routing-20261019')
    raw=raw.replace("pc['identity_voice_enrollment']['identity_query_version']==1",
        "pc['identity_voice_enrollment']['identity_query_version']==1 and pc['identity_voice_enrollment'].get('identity_query_intent_revision')==2")
    raw=raw.replace("$taskReady.identity_voice_enrollment.identity_query_version -eq 1 -and",
        "$taskReady.identity_voice_enrollment.identity_query_version -eq 1 -and $taskReady.identity_voice_enrollment.identity_query_intent_revision -eq 2 -and")
    (HERE/name).write_text(raw,encoding='utf-8')
print('Backed up six source files and prepared guarded UI-only release helpers.')
