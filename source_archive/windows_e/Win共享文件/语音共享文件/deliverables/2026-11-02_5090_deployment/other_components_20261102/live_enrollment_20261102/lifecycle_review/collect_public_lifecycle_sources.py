"""Read only public pinned source. No API, store, microphone or hardware calls."""
import hashlib, importlib.util, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
LOCAL=HERE.parent/'start_sync_fix/candidate_runtime'
NAMES=(
 'tools/board_recording.py','tools/handsfree_recording.py','tools/voice_first_recording.py',
 'tools/production_listening.py','board/runtime/audio/automatic_capture.py',
 'board/runtime/audio/board_capture.py','board/runtime/audio/capture.py',
 'board/runtime/audio/board_dialogue_jobs.py','board/runtime/board_business.py',
 'board/runtime/board_speaker_business.py','board/runtime/audio/face_binding_bridge.py',
 'board/identity/voice_enrollment.py','board/interaction/ui_services.py',
 'board/runtime/board_dialogue.py','tools/streaming_controller.py',
 'tools/binding_hub_runtime.py','board/runtime/audio/board_asr.py',
 'board/runtime/audio/board_asr_frontend.py',
)
known={n:hashlib.sha256((LOCAL/n).read_bytes()).hexdigest() for n in NAMES if (LOCAL/n).is_file()}
source='''import hashlib,json\nfrom pathlib import Path\nNAMES=__NAMES__\nKNOWN=__KNOWN__\nroot=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')\nraw=(root/'startup/config.json').read_bytes(); startup=json.loads(raw); aura=Path(startup['runtime'])/'aura'\nrows={}\nfor name in NAMES:\n p=aura/name\n assert p.is_file() and not p.is_symlink() and p.resolve()==p and p.stat().st_size<180000\n data=p.read_bytes();sha=hashlib.sha256(data).hexdigest();pin=startup['component_sha256'].get(name)\n assert pin==sha,(name,'pin mismatch')\n row={'sha256':sha,'pin':pin,'bytes':len(data),'matches_local':KNOWN.get(name)==sha}\n if KNOWN.get(name)!=sha:row['public_source']=data.decode('utf-8')\n rows[name]=row\nassert (root/'startup/config.json').read_bytes()==raw\nprint(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'startup_sha256':hashlib.sha256(raw).hexdigest(),'stable_startup':True,'sources':rows,'public_source_only':True,'board_mutations':False,'health_or_private_api_or_store_reads':False}))\n'''.replace('__NAMES__',repr(NAMES)).replace('__KNOWN__',repr(known))
spec=importlib.util.spec_from_file_location('strict_board_ssh',r'E:\Win共享文件\语音共享文件\deliverables\2026-10-18_board_dialogue\board_ssh.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
value=json.loads(helper.ssh('python3 -B -',source,timeout=25))
HERE.mkdir(exist_ok=True)
(HERE/'PUBLIC_SOURCE_READBACK.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name,row in value['sources'].items():
 if 'public_source' in row:
  target=HERE/'current_public'/name;target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(row['public_source'].encode('utf-8'))
print(json.dumps({'boot':value['boot_id'],'startup_sha256':value['startup_sha256'],'count':len(value['sources']),'mismatches':{n:r['sha256'] for n,r in value['sources'].items() if not r['matches_local']},'all_pins_match':True,'private_data_read':False},ensure_ascii=True))
