"""Retain failed real-user validation separately from software preflight success."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
folder=HERE.parent/'2026-10-19_simple_face_enrollment'
read=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
write=lambda path,data:path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary=read(folder/'verification_summary.json')
summary.update(status='REAL_USER_VALIDATION_FAILED_AFTER_COLLECTION_TIMEOUT',
    actual_user_simple_registration_passed=False,real_user_feedback='验证不通过',
    actual_user_failure_counts={'collect':10,'validate':0},
    actual_user_failure_reason='采样或确认已超时，请重新采样',diagnosis_entry=str(HERE/'README.md'))
write(folder/'verification_summary.json',summary)
listening=read(folder/'listening.json');listening.update(actual_user_simple_registration_passed=False,user_feedback='验证不通过')
write(folder/'listening.json',listening)
scores=read(HERE/'live_exact_crop_scores.json')
feedback={'client_date':'2026-10-19','user_feedback':'验证不通过','active_runtime':summary['active_runtime'],
 'failure_stage':'collected_minimum_but_heldout_validation_not_completed','failure_counts':{'collect':10,'validate':0},
 'failure_reason':'采样或确认已超时，请重新采样','failure_session_frame_scores_retained':False,
 'subsequent_exact_production_crop_sample_count':len(scores['samples']),
 'subsequent_same_track_pair_min':scores['same_track_pair_min'],
 'subsequent_same_track_pair_median':scores['same_track_pair_median'],
 'subsequent_same_track_pairs_at_point85':scores['same_track_pairs_at_point85'],
 'subsequent_same_track_pair_count':scores['same_track_pair_count'],
 'subsequent_samples_are_not_failed_session_candidate':True,
 'database_revision':scores['database_revision'],'registered_count':scores['registered_count'],
 'database_unchanged_during_diagnosis':scores['database_unchanged'],
 'threshold_changed':False,'photos_exported':False,'templates_exported':False,'names_exported':False}
write(HERE/'feedback.json',feedback)
print(json.dumps(feedback,ensure_ascii=True))
