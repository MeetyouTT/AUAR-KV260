"""Verify and record actual saved face photos and the formal update outcome."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
prior=HERE.parent/'2026-10-19_enrollment_photo_archive'
export=json.loads((prior/'latest_photo_export.json').read_text(encoding='utf-8'))
assert export['status']=='SAVED_ENROLLMENT_PHOTOS_EXPORTED' and export['outcome']=='committed'
folder=Path(export['folder']);manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
assert manifest['session_id']==export['session_id'] and len(manifest['validation_frame_ids'])==5
for path in folder.glob('*.png'):
 with Image.open(path) as source:
  assert source.size==(112,112) and source.format=='PNG';source.verify()
for row in manifest['images']+[manifest['selected']]:
 assert hashlib.sha256((folder/row['filename']).read_bytes()).hexdigest()==row['sha256']
assert manifest['selected']['frame_id'] not in manifest['validation_frame_ids']
assert all(score>=.8 for score in manifest['validation_scores'])
assert not manifest['contains_full_camera_frames'] and not manifest['contains_embeddings_or_names']
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,re,sqlite3,urllib.request
from pathlib import Path
sid=SID;assert re.fullmatch('[0-9a-f]{32}',sid)
root=Path('/home/root/.local/share/aura/enrollment_photos');folder=root/sid
m=json.loads((folder/'manifest.json').read_text());assert m['outcome']=='committed'
assert root.stat().st_mode&0o777==0o700 and folder.stat().st_mode&0o777==0o700
assert all(path.stat().st_mode&0o777==0o600 for path in folder.iterdir() if path.is_file())
ui=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
snapshot=json.load(urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/status',timeout=4))
i=snapshot['modules']['identity'];service=ui['local_transcription']['service']
codes=[]
for turn in ui.get('turns',[]):
 llm=turn.get('server_metrics',{}).get('timing',{}).get('llm',{})
 codes.append({'generation':turn['generation'],'code':llm.get('identity_reply_code'),'audio_complete':turn.get('audio_complete')})
with sqlite3.connect('file:/home/root/.local/share/aura/identities.sqlite3?mode=ro',uri=True) as con:
 counts={'identities':con.execute('SELECT count(*) FROM identities').fetchone()[0],
 'templates':con.execute('SELECT count(*) FROM templates').fetchone()[0],
 'revision':con.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
assert counts=={'identities':1,'templates':1,'revision':m['database_revision_after']}
print(json.dumps({'board_directory_mode':'0700','board_file_modes':'0600','manifest_outcome':m['outcome'],
 'board_photo_count':len(m['images']),'database':counts,'current_identity_state':i['state'],
 'turn_codes':codes,'last_voice_route':service.get('last_voice_route'),
 'registered_audio_complete':any(row['code']=='registered' and row['audio_complete'] for row in codes)}))
'''.replace('SID',repr(export['session_id']),1)
board=json.loads(ssh('python3 -B -',remote,timeout=25))
review={'status':'PASS_REAL_ENROLLMENT_FACE_PHOTOS_SAVED_AND_EXPORTED',
 'session_id':export['session_id'],'outcome':'committed','user_confirmed_enrollment_completed':True,
 'image_count':len(manifest['images']),'selected_frame':manifest['selected']['frame_id'],
 'validation_frame_ids':manifest['validation_frame_ids'],'validation_scores':manifest['validation_scores'],
 'selected_and_validation_frames_disjoint':True,'all_saved_pngs_decoded_exact_112x112':True,
 'all_png_hashes_verified':True,'source_pngs_modified':False,'full_camera_frames_saved':False,
 'selected_and_side_rejection_and_two_validation_photos_visually_inspected':True,
 'visual_observation':'Model crops center the face; glasses show screen reflections; the side-view example is marked quality_rejected.',
 'names_or_embeddings_exported':False,'selected':export['selected'],'gallery':export['gallery'],
 'folder':str(folder),'board':board,'human_reentry_recognition_tested':False}
(HERE/'photo_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
(folder/'查看记录.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(review,ensure_ascii=False))
