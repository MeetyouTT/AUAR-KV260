"""Reuse guarded deployment; only add CPU feature transport and diagnostics."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'2026-10-19_simple_face_enrollment'
for name in ('prepare.py','preflight.py','activate.py','rollback.py','verify_and_archive.py',
             'reload_voice_host.ps1','observe.py','status.py','probe_voice_host.py'):
    raw=(OLD/name).read_text(encoding='utf-8')
    raw=raw.replace('/home/root/aura-simple-enrollment-20261019','/home/root/aura-windows-face-features-20261019')
    raw=raw.replace('SIMPLE_ENROLLMENT_DEPLOYED_AWAITING_REAL_USER_VALIDATION',
                    'WINDOWS_FACE_FEATURES_DEPLOYED_AWAITING_REAL_USER_VALIDATION')
    if name=='prepare.py':
        raw=raw.replace('names=[',"names=['aura/common/face_features.py','aura/tools/face_feature_host.py','aura/board/identity/remote_features.py','aura/tests/framework/test_face_features.py', ",1)
        raw=raw.replace("(configs/'board_identity.json').write_text", "identity['feature_backend']={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}\n(configs/'board_identity.json').write_text",1)
        raw=raw.replace("*['tests.framework.'+n for n in modules],'-v'", "*['tests.framework.'+n for n in modules], 'tests.framework.test_face_features.FeatureProtocolTests','-v'",1)
    elif name=='reload_voice_host.ps1':
        raw=raw.replace('if ($taskReady.ready -and $taskReady.identity_voice_enrollment.sampling_guidance_version -eq 3)',
            "if ($taskReady.ready -and $taskReady.identity_voice_enrollment.sampling_guidance_version -eq 3 -and $taskReady.identity_features.ready -and $taskReady.identity_features.backend -eq 'WINDOWS_CPU_SFACE_ORT' -and $taskReady.identity_features.model_id -eq 'sface-2021dec-0ba9fbfa01b5')")
    elif name=='preflight.py':
        raw=raw.replace("result_ttl_ms=3000,multi_frame=True)","result_ttl_ms=3000,multi_frame=True,backend='WINDOWS_CPU_SFACE_ORT')")
        raw=raw.replace('PASS_REAL_CPU_PUBLIC_FACE_UPFRONT_CONSENT_AUTOMATIC_SAVE_AND_LOSS',
            'PASS_REAL_WINDOWS_CPU_PUBLIC_FACE_UPFRONT_CONSENT_AUTOMATIC_SAVE_AND_LOSS')
    elif name=='activate.py':
        raw=raw.replace("assert pc['identity_voice_enrollment']['sampling_guidance_version']==3",
            "assert pc['identity_voice_enrollment']['sampling_guidance_version']==3\nassert pc['identity_features']['ready'] and pc['identity_features']['backend']=='WINDOWS_CPU_SFACE_ORT'\nassert pc['identity_features']['model_id']=='sface-2021dec-0ba9fbfa01b5'")
        raw=raw.replace("assert identity==old_identity", "assert {k:v for k,v in identity.items() if k!='feature_backend'}=={k:v for k,v in old_identity.items() if k!='feature_backend'}\nassert identity['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}\nassert old_identity.get('feature_backend') in (None,identity['feature_backend'])")
        raw=raw.replace("assert camera['detector']==before['detector']", "assert camera['identity']['backend']=='WINDOWS_CPU_SFACE_ORT'\n assert camera['detector']==before['detector']")
    elif name=='verify_and_archive.py':
        raw=raw.replace("assert item['target_kind']=='face'", "assert item['target_kind']=='face' and item['backend']=='WINDOWS_CPU_SFACE_ORT'\nassert pc['identity_features']['ready'] and not pc['identity_features']['gpu_used']")
    elif name=='probe_voice_host.py':
        raw=raw.replace("('sample_auto','registered')", "('sample_auto','sample_validate','registered')")
    (HERE/name).write_text(raw,encoding='utf-8')
print('Prepared guarded Windows CPU feature deployment helpers')
