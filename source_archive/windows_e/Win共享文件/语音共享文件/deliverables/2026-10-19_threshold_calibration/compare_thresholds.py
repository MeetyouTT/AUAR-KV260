"""Counterfactual decision replay on retained anonymous scores, no live writes."""
import json,math,statistics,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'aura'))
from board.identity.sampling import EnrollmentSampling
failure=json.loads((ROOT/'deliverables/2026-10-19_validation_score_failure/actual_failure.json').read_text(encoding='utf-8'))
frames=failure['sampling_diagnostics']['last_failure']['metrics']['recent_validation']
assert len(frames)==24 and all(v['other_identity_gap'] is not None for v in frames)
rows=[]
for threshold in (.363,.5,.6,.7,.75,.8,.81,.82,.83,.84,.85):
    sampling=EnrollmentSampling(threshold,.1,lambda:1000)
    sampling.candidate={'embedding':(1.,0.)}
    passes=run=longest=0;first_five=None
    for index,item in enumerate(frames):
        score=item['score'];vector=(score,math.sqrt(max(0,1-score*score)))
        other=score-item['other_identity_gap']
        accepted=sampling.usable(vector,other)
        assert accepted==(score>=threshold and item['other_identity_gap']>=.1)
        passes+=int(accepted);run=run+1 if accepted else 0;longest=max(longest,run)
        if run>=5 and first_five is None:first_five=index+1
    rows.append({'threshold':threshold,'passed':passes,'total':len(frames),
        'longest_consecutive':longest,'first_five_at_retained_frame':first_five,
        'score_gate_could_complete_five':first_five is not None})
gallery=json.loads((ROOT/'deliverables/2026-10-19_validation_diagnosis/live_exact_crop_scores.json').read_text(encoding='utf-8'))
gallery_rows=[]
for threshold in (.363,.5,.6,.7,.75,.8,.85):
    accepted=ambiguous=unknown=0;winning_hashes=set()
    for sample in gallery['samples']:
        matches=sorted(sample['matches'],key=lambda row:row['cosine'],reverse=True)
        if matches[0]['cosine']<threshold:unknown+=1
        elif len(matches)>1 and matches[0]['cosine']-matches[1]['cosine']<.1:ambiguous+=1
        else:accepted+=1;winning_hashes.add(matches[0]['template_hash'])
    gallery_rows.append({'threshold':threshold,'accepted_against_old_library':accepted,'ambiguous':ambiguous,
        'unknown':unknown,'number_of_distinct_winning_records':len(winning_hashes),
        'ground_truth_person_accuracy':'NOT_MEASURABLE_UNKNOWN_RECORD_OWNERSHIP'})
result={'client_date':'2026-10-19','status':'OFFLINE_SCORE_REPLAY_COMPLETE_NOT_PRODUCTION_VALIDATION',
    'source':'failed_session_36963353_last24_scores_rounded_6_decimals',
    'source_total_validation_attempts':77,'retained_frame_count':len(frames),
    'threshold_rows':rows,'ambiguity_margin_held_fixed':.1,
    'uses_production_EnrollmentSampling_usable_decision':True,
    'score_projection_only_no_model_or_full_enrollment_replay':True,
    'source_scores_min':min(f['score'] for f in frames),'source_scores_median':statistics.median(f['score'] for f in frames),
    'source_scores_max':max(f['score'] for f in frames),
    'historical_different_session_library_comparison':gallery_rows,
    'historical_library_source_frame_count':len(gallery['samples']),
    'old_library_ground_truth':'USER_UNCERTAIN_ALL_RECORDS_SUBSEQUENTLY_DELETED',
    'false_match_rate':None,'false_non_match_rate':None,'calibrated_deployment_threshold':None,
    'official_sface_demo_reference':{'threshold':.363,'metric':'cosine_similarity','benchmark':'LFW',
      'source':'https://docs.opencv.org/4.9.0/d0/dd4/tutorial_dnn_face.html',
      'not_a_calibrated_camera_specific_1_to_N_threshold':True},
    'production_changed_by_analysis':False,'photos_accessed':False,'vectors_exported':False,
    'limits':['Only the final 24 of 77 validation scores are retained.',
      'Quality skips, source timestamps, track transitions and earlier frames cannot be reconstructed.',
      'The selected candidate and frame inputs are not retained; no feature model is re-run.',
      'Recorded gaps compare with other old identity records, whose physical-person ownership is unknown.',
      'The older 12-frame gallery probe uses another session and is not a labelled impostor test.',
      'A lower gate passing this sample does not establish correctness, enrollment commit or stranger rejection.']}
(HERE/'threshold_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'threshold_rows':rows,'historical_library':gallery_rows},ensure_ascii=True))
