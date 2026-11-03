"""Current revision receipts; human listening remains separate from ACK."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
INTEGRATION=REPAIR.parent

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

if __name__=='__main__':
    origins={
        'installed':INTEGRATION/'listening_entry_fix/actual_automatic-listening-v6-prepared-guard.json',
        'ready':INTEGRATION/'production_business_acceptance/actual_ready.json',
        'control':INTEGRATION/'listening_entry_fix/actual_control_semantics.json',
        'live':INTEGRATION/'listening_entry_fix/actual_live_listening.json'}
    values={name:read(path) for name,path in origins.items()}
    installed,live,control=(values[name] for name in ('installed','live','control'))
    pin=installed['startup_sha256']
    assert pin==live['startup_sha256']==control['startup_sha256']
    assert live['continuous_capture_passed'] and live['priority_scope_passed'] and control['cancel_rearm_passed']
    evidence={}
    for name,path in origins.items():
        raw=path.read_bytes();(HERE/('actual_'+name+'.json')).write_bytes(raw)
        evidence[name]=dict(path='actual_'+name+'.json',sha256=hashlib.sha256(raw).hexdigest())
    status=dict(status='PREPARED_GUARD_OPTIMIZATION_DEPLOYED_AWAITING_SPEECH_RESULT',
        startup_sha256=pin,source_manifest_sha256=installed['source_manifest_sha256'],component_pins=375,
        board_boot_id=live['board_boot_id'],main_pid=control['main_pid'],gtk_pid=control['gtk_pid'],camera_pid=live['camera_pid'],
        automatic_listening=True,wake_word_required=False,conversation_mode='half_duplex',
        change='One fresh read connection/transaction and batched SELECT per prepared-audio guard',
        per_packet_authority_checks=True,cached_validity=False,full_playback_ACK_preserved=True,
        pause_resume_cancel_verified=True,short_capture_check_passed=True,
        source_tests=dict(guard_contracts=56,dialogue_controls_and_instrumentation=22,subtests=3),
        synthetic_ARM_ABBA='actual_arm_comparison_33cb8cedd1913829.json',
        physical_dialogue_acceptance=False,smooth_playback_after_optimization=None,
        prior_half_duplex_only_operator_result='still_stuttering',
        independent_open_issue='One capture queue overflow after approximately 237s; automatic recovery after approximately 5s',
        private_data_replayed=False,transcript_or_pcm_archived=False,model_or_voice_changed=False,evidence=evidence)
    (HERE/'STATUS.json').write_bytes(encoded(status))
    old=REPAIR/'STATUS.json'
    if old.exists() and read(old).get('startup_sha256')!=pin:
        archive=REPAIR/'half_duplex_v5_STATUS.json'
        if archive.exists():assert archive.read_bytes()==old.read_bytes()
        else:archive.write_bytes(old.read_bytes())
    (REPAIR/'STATUS.json').write_bytes(encoded(dict(status,detail='guard_candidate/STATUS.json')))
    print(json.dumps(dict(status=status['status'],startup_sha256=pin)))
