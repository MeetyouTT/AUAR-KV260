"""Record human visual review decisions and verify the review delivery."""
import ast
import hashlib
import json
from pathlib import Path

BATCH=Path(__file__).resolve().parents[1]
OUT=BATCH/'review_20261005'
notes={
'talking_calm_rest_v3_s421001':'Mid-clip hands move upward; forearm angles and hand placement change.',
'talking_calm_rest_v3_s421002':'Mid-clip torso narrows and shoulder/hand placement changes; eyes visibly close at frames 6-8.',
'talking_calm_rest_v3_s421003':'Mid-clip head tilts, torso width and hand placement change.',
'talking_calm_blink_v3_s421001':'Blink is accompanied by head tilt, torso contour and hand placement changes.',
'talking_calm_blink_v3_s421002':'Mid-clip torso and hand placement change; frames 15-17 show closed eyes despite probe NONE.',
'talking_calm_blink_v3_s421003':'Mid-clip head/torso posture and hand placement change.',
'talking_low_rest_v3_s421001':'Mid-clip shoulder and torso contour change; hands move.',
'talking_low_rest_v3_s421002':'Mid-clip torso narrows and arm/hand placement changes.',
'talking_low_rest_v3_s421003':'Mid-clip head tilts; torso and hands change posture.',
'talking_warm_rest_v3_s421001':'Closed-eye smile is accompanied by head, shoulder and hand movement.',
'talking_warm_rest_v3_s421002':'Closed-eye smile, torso narrowing and hand displacement.',
'talking_warm_rest_v3_s421003':'Mid-clip head tilts; torso contour and hand placement change.'}
integrity=json.loads((OUT/'integrity.json').read_text(encoding='utf-8'))
rows=[]
for r in integrity['records']:
    name=r['id']
    for p in r['pngs']:
        assert hashlib.sha256((BATCH/'raw'/name/p['file']).read_bytes()).hexdigest()==p['sha256']
    rows.append({'id':name,'visual_verdict':'FAIL','release_allowed':False,
                 'inspected_source_frames':r['review_frames'],
                 'inspected_regions':['full_frame','face','hands'],
                 'reason':notes[name],'evidence':name+'_review.png',
                 'all_face_frames_inspected':name in ('talking_calm_blink_v3_s421002','talking_calm_rest_v3_s421002')})
result={'date_client':'2026-10-05','reviewer':'Codex visual review',
        'status':'REWORK_REQUIRED','accepted_ids':[],'rejected_ids':[r['id'] for r in rows],
        'criteria_changed':False,'blink_policy':'Original no-blink base criterion retained pending user choice; posture failures independent of blink choice.',
        'raw_frames_unchanged':True,'production_assets_modified':False,'rows':rows}
(OUT/'visual_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
# Probe annotations changed, not its metric or thresholds.
ast.parse((BATCH/'tools/blink_probe_v2_iris.py').read_text(encoding='utf-8-sig'))
old=json.loads((BATCH/'qc/qc_20261006_075517.json').read_text(encoding='utf-8'))
new=json.loads((BATCH/'qc/review_20261005_numeric.json').read_text(encoding='utf-8'))
assert old['candidates']==new['candidates']
assert '509 passed' in (OUT/'pytest_current.log').read_text(encoding='utf-8')
files=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='review_manifest.json']
files += [BATCH/'tools'/n for n in ['review_batch.py','measure_review_motion.py','finalize_review.py','blink_probe_v2_iris.py']]
manifest={'status':'VERIFIED','raw_frames_rechecked':468,'numeric_matches_transferred_report':True,
          'visual_pass':0,'visual_fail':12,
          'files':[{'path':p.relative_to(BATCH).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files]}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in manifest.items() if k!='files'}))

if __name__=='__main__':pass
