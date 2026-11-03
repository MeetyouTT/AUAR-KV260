"""Recompute existing face PNGs on pinned CPU SFace; persist numeric evidence only."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.face_feature_host import FaceFeatureHost
from common.face_features import MODEL_ID,PROTOCOL

folder=ROOT/'身份登记照片/c6c3fa6ebd4449ae93bd9ec316344d51'
m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
host=FaceFeatureHost(ROOT/'aura/models/vision/sface_2021dec.onnx')
rows=[];vectors=[]
for index,row in enumerate(m['images']):
 raw=(folder/row['filename']).read_bytes();sha=hashlib.sha256(raw).hexdigest();assert sha==row['sha256']
 meta={'protocol':PROTOCOL,'model_id':MODEL_ID,'request_id':format(index+1,'032x'),
 'target':{'camera_epoch':'offline-archive-review','track_id':1,'track_generation':1},
 'frame_id':row['frame_id'],'captured_mono_ms':row['captured_mono_ms'],'sha256':sha}
 vector=np.asarray(host.feature(meta,raw)['embedding'],dtype=np.float64);vector/=np.linalg.norm(vector);vectors.append(vector)
 with Image.open(folder/row['filename']) as image:pixels=np.asarray(image.convert('RGB'),dtype=np.float64)
 gray=pixels@[.299,.587,.114]
 rows.append({'frame_id':row['frame_id'],'decision':row['decision'],'pose':row['pose'],
   'is_final_validation':row['frame_id'] in m['validation_frame_ids'],
   'brightness_mean':round(float(gray.mean()),3),'brightness_std':round(float(gray.std()),3),
   'bright_pixel_fraction':round(float((gray>245).mean()),5),
   'near_black_pixel_fraction':round(float((gray<10).mean()),5)})
vectors=np.asarray(vectors);matrix=vectors@vectors.T
selected=next(index for index,row in enumerate(rows) if row['frame_id']==m['selected']['frame_id'])
training=[i for i,row in enumerate(rows) if row['decision']=='collect']
front=[i for i in training if abs(rows[i]['pose']['yaw'])<=.22 and abs(rows[i]['pose']['roll'])<=15]
top5=sorted(front,key=lambda i:(abs(rows[i]['pose']['yaw']),abs(rows[i]['pose']['roll']),
    -(min(rows[i]['pose']['blur'],400)+min(rows[i]['pose']['pixels'],240))))[:5]
chosen=max(top5,key=lambda i:(sum(matrix[i,j] for j in top5),min(rows[i]['pose']['blur'],400)+min(rows[i]['pose']['pixels'],240)))
validation=[i for i,row in enumerate(rows) if row['is_final_validation']]
def distribution(values):
 values=np.asarray(values,dtype=float)
 return {'min':round(float(values.min()),6),'median':round(float(np.median(values)),6),'max':round(float(values.max()),6)}
for i,row in enumerate(rows):row['cosine_vs_selected']=round(float(matrix[i,selected]),6)
template_comparison=[]
for i in training:
 scores=matrix[i,validation]
 template_comparison.append({'template_frame_id':rows[i]['frame_id'],'yaw_ratio':round(rows[i]['pose']['yaw'],4),
  'scores_to_five_final_validation':distribution(scores),'count_pass_080':int((scores>=.8).sum()),
  'is_current_template':i==selected})
replay=json.loads((HERE.parent/'2026-10-19_identity_capture_snapshot/after_enrollment_scores.json').read_text(encoding='utf-8'))
prior_scores={row['frame_id']:row['score'] for row in replay['archive_replay']}
delta=max(abs(row['cosine_vs_selected']-prior_scores[row['frame_id']]) for row in rows)
assert delta<2e-6
controls=json.loads((HERE.parent/'2026-10-19_identity_capture_snapshot/controlled_front_check.json').read_text(encoding='utf-8'))
control_scores=np.asarray([row['score'] for row in controls['samples']])
threshold_rows=[]
for threshold in (.85,.8,.75,.7,.65,.6,.55,.5,.45,.363):
 threshold_rows.append({'threshold':threshold,'saved_25_pass':int((matrix[:,selected]>=threshold).sum()),
   'saved_collection_13_pass':int((matrix[training,selected]>=threshold).sum()),
   'final_validation_5_pass':int((matrix[validation,selected]>=threshold).sum()),
   'controlled_new_frontal_6_pass':int((control_scores>=threshold).sum()),
   'confirmed_different_person_count':0,'false_accept_rate':None,
   'not_a_deployable_threshold_calibration':True})
training_ms=[m['images'][i]['captured_mono_ms'] for i in training]
validation_ms=[m['images'][i]['captured_mono_ms'] for i in validation]
result={'status':'OFFLINE_REAL_PHOTO_DATASET_AUDIT','model_sha256':hashlib.sha256((ROOT/'aura/models/vision/sface_2021dec.onnx').read_bytes()).hexdigest(),
 'model_backend':'PINNED_EXISTING_CPU_SFACE_ORT_IN_ISOLATED_PROCESS','image_count':len(rows),
 'selected_frame_id':rows[selected]['frame_id'],'selection_recomputed_frame_id':rows[chosen]['frame_id'],
 'selection_matches_production':chosen==selected,'front_training_count':len(front),
 'top_five_frontal_selection_frame_ids':[rows[i]['frame_id'] for i in top5],
 'training_duration_ms':max(training_ms)-min(training_ms),
 'heldout_validation_duration_ms':max(validation_ms)-min(validation_ms),
 'gap_training_to_validation_ms':min(validation_ms)-max(training_ms),
 'archive_vs_previous_board_replay_max_cosine_delta':round(delta,9),
 'all_pairwise_scores':np.round(matrix,6).tolist(),'pairwise_frame_ids':[row['frame_id'] for row in rows],
 'samples':rows,'candidate_diagnostics_using_same_session_only':template_comparison,
 'threshold_counterfactual_numeric_replay':threshold_rows,
 'production_database_templates_threshold_or_configs_modified':False,
 'new_photos_or_embeddings_saved':False,'negative_person_samples_available':False,
 'same_session_validation_is_not_cross_session_or_false_accept_evaluation':True}
(HERE/'offline_dataset_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('status','image_count','selection_matches_production','front_training_count',
 'top_five_frontal_selection_frame_ids','training_duration_ms','heldout_validation_duration_ms',
 'gap_training_to_validation_ms','archive_vs_previous_board_replay_max_cosine_delta','threshold_counterfactual_numeric_replay')},ensure_ascii=False))
