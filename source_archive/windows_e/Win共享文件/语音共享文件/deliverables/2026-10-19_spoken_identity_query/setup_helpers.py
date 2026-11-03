"""Stage the query UI; preserve the running camera and user's enrolled identity."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'2026-10-19_windows_face_features'
for name in ('prepare.py','preflight.py','reload_voice_host.ps1','observe.py','status.py'):
    raw=(OLD/name).read_text(encoding='utf-8')
    raw=raw.replace('/home/root/aura-windows-face-features-20261019','/home/root/aura-spoken-identity-query-20261019')
    if name=='prepare.py':
        raw=raw.replace('names=[',"names=['aura/board/identity/spoken_query.py','aura/tests/framework/test_spoken_identity_query.py','aura/tools/voice_channel_source.py', ",1)
        raw=raw.replace("identity['threshold']==.85","identity['threshold']==.8")
        raw=raw.replace("'tests.framework.test_face_features.FeatureProtocolTests','-v'",
            "'tests.framework.test_face_features.FeatureProtocolTests','tests.framework.test_spoken_identity_query.SpokenIdentityQueryTests','-v'")
    elif name=='preflight.py':
        raw=raw.replace("  assert state.snapshot()['modules']['identity']['state']=='KNOWN'",
            "  assert state.snapshot()['modules']['identity']['state']=='KNOWN'\n  assert flow.handle('我是谁',state.snapshot())=={'code':'identity_seen','name':'测试访客'}")
        raw=raw.replace("  feed(blank);assert state.snapshot()['modules']['identity']['state']=='UNKNOWN'",
            "  feed(blank);assert state.snapshot()['modules']['identity']['state']=='UNKNOWN'\n  assert flow.handle('我是谁',state.snapshot())=={'code':'identity_unavailable','name':''}")
        raw=raw.replace('PASS_REAL_WINDOWS_CPU_PUBLIC_FACE_UPFRONT_CONSENT_AUTOMATIC_SAVE_AND_LOSS',
            'PASS_REAL_PUBLIC_ENROLL_KNOWN_SPOKEN_QUERY_AND_LOSS_NO_NAME')
    elif name=='reload_voice_host.ps1':
        raw=raw.replace("if ($taskReady.ready -and", "if ($taskReady.identity_voice_enrollment.identity_query_version -eq 1 -and $taskReady.ready -and",1)
    (HERE/name).write_text(raw,encoding='utf-8')
print('Prepared isolated spoken identity query helpers')
