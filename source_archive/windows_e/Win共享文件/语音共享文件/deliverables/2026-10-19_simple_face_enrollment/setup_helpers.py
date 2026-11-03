"""Prepare the existing guarded workflow for upfront-confirmed enrollment."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'2026-10-19_natural_face_enrollment'
for name in ('prepare.py','preflight.py','activate.py','rollback.py','verify_and_archive.py',
             'render_sampling_ui.py','reload_voice_host.ps1','observe.py','status.py'):
    raw=(OLD/name).read_text(encoding='utf-8')
    raw=raw.replace('/home/root/aura-natural-enrollment-20261019','/home/root/aura-simple-enrollment-20261019')
    raw=raw.replace('NATURAL_ENROLLMENT_DEPLOYED_AWAITING_REAL_USER_VALIDATION',
                    'SIMPLE_ENROLLMENT_DEPLOYED_AWAITING_REAL_USER_VALIDATION')
    if name=='prepare.py':
        raw=raw.replace("names=[", "names=['aura/tests/framework/test_simple_enrollment.py', ",1)
        raw=raw.replace("modules=['test_enrollment_sampling'", "modules=['test_simple_enrollment','test_enrollment_sampling'",1)
    elif name=='activate.py':
        raw=raw.replace("['sampling_guidance_version']==2","['sampling_guidance_version']==3")
    elif name=='reload_voice_host.ps1':
        raw=raw.replace('sampling_guidance_version -eq 2','sampling_guidance_version -eq 3')
    elif name=='preflight.py':
        raw=raw.replace("cfg['threshold'],cfg['ambiguity_margin']);os.chmod",
                        "cfg['threshold'],cfg['ambiguity_margin'],allow_cross_thread=True);os.chmod")
        raw=raw.replace('from board.identity.store import IdentityStore',
                        'from board.identity.store import IdentityStore\nfrom board.identity.voice_enrollment import VoiceEnrollment')
        raw=raw.replace("  assert state.command(command('identity_sample_start',{'target':identity['face_target']},'sample'))['accepted']",
            """  flow=VoiceEnrollment(state.boot,state.snapshot,state.command,simple=True,now_ms=lambda:clock[0],clock=lambda:clock[0]/1000)
  assert flow.handle('帮我登记身份我叫测试访客',state.snapshot())['code']=='prepare_name' and store.revision==0
  assert flow.handle('确认登记',state.snapshot())['code']=='sample_auto' and store.revision==0""")
        raw=raw.replace("  assert state.command(command('identity_enroll',{'target':identity['face_target'],'display_name':'public fixture','confirmed':True},'save'))['accepted']",
            """  replies=[];flow.guide(lambda reply,final:replies.append((reply,final)))
  assert replies==[({'code':'registered','name':''},True)] and store.revision==1
  assert flow.public()['stage']=='idle'""")
        raw=raw.replace('PASS_REAL_CPU_PUBLIC_FACE_NATURAL_WINDOW_ENROLL_RECOGNIZE_AND_LOSS',
                        'PASS_REAL_CPU_PUBLIC_FACE_UPFRONT_CONSENT_AUTOMATIC_SAVE_AND_LOSS')
    (HERE/name).write_text(raw,encoding='utf-8')
print('Prepared simple enrollment deployment helpers')
