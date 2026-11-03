"""Reuse the guarded deployment workflow, scoped to the natural enrollment candidate."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'2026-10-19_multiframe_enrollment'
for name in ('prepare.py','preflight.py','activate.py','rollback.py','verify_and_archive.py',
             'render_sampling_ui.py','reload_voice_host.ps1','probe_voice_host.py','observe.py'):
    source=(OLD/name).read_text(encoding='utf-8')
    source=source.replace('/home/root/aura-multiframe-enrollment-20261019','/home/root/aura-natural-enrollment-20261019')
    source=source.replace('MULTIFRAME_ENROLLMENT_DEPLOYED_AWAITING_REAL_USER_VALIDATION',
                          'NATURAL_ENROLLMENT_DEPLOYED_AWAITING_REAL_USER_VALIDATION')
    if name=='prepare.py':
        source=source.replace("names=['aura/board/identity/sampling.py',", "names=['aura/board/identity/face_targets.py', 'aura/tests/framework/test_identity_face_targets.py', 'aura/board/identity/sampling.py',")
    elif name=='preflight.py':
        begin=source.index(' original_extract=extractor.extract')
        end=source.index(' def feed(source):',begin)
        source=source[:begin]+source[end:]
        source=source.replace('for _ in range(15):feed(image)','for _ in range(27):feed(image)')
        source=source.replace("{'front':4,'left':3,'right':3,'validate':5}","{'collect':10,'validate':5}")
        source=source.replace("'pose_labels_injected_for_public_fixture':True","'pose_labels_injected_for_public_fixture':False")
        source=source.replace('PASS_REAL_CPU_PUBLIC_FACE_MULTIFRAME_ENROLL_RECOGNIZE_AND_LOSS',
                              'PASS_REAL_CPU_PUBLIC_FACE_NATURAL_WINDOW_ENROLL_RECOGNIZE_AND_LOSS')
    elif name=='activate.py':
        source=source.replace("['sampling_guidance_version']==1","['sampling_guidance_version']==2")
    elif name=='verify_and_archive.py':
        source=source.replace(",'aura/board/identity/face_targets.py'",'')
    elif name=='render_sampling_ui.py':
        source=source.replace("'stage':'left','counts':{'front':4,'left':1,'right':0,'validate':0}",
                              "'stage':'collect','counts':{'collect':7,'validate':0}")
        source=source.replace("'total':5,","'total':7,")
        source=source.replace('请轻微向左转头，双眼保持可见','请看着镜头慢慢自然转头，正在自动挑选清晰人脸')
    elif name=='reload_voice_host.ps1':
        source=source.replace('sampling_guidance_version -eq 1','sampling_guidance_version -eq 2')
    elif name=='probe_voice_host.py':
        source=source.replace("('sample_front','sample_left','sample_right','sample_validate','confirm_update_name')",
                              "('sample_front','sample_validate','confirm_update_name')")
        source=source.replace('final=seq==4','final=seq==2').replace('if seq<4:','if seq<2:')
        source=source.replace("end['clauses']==5","end['clauses']==3")
        source=source.replace('controlled_five_phase_identity_relay','controlled_natural_enrollment_identity_relay')
        source=source.replace('PASS_REAL_FIVE_PHASE_ASR_TTS_RELAY_AND_ORIGINAL_27B_CHAT',
                              'PASS_REAL_NATURAL_ENROLLMENT_ASR_TTS_RELAY_AND_ORIGINAL_27B_CHAT')
    (HERE/name).write_text(source,encoding='utf-8')
print('Prepared scoped deployment helpers')
