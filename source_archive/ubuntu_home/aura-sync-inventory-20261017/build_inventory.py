"""Audit current ASR dependencies and accepted voice assets; package ASR code."""
import hashlib
import json
from pathlib import Path
import shutil
import socket
import zipfile

WORK=Path(__file__).resolve().parent
SHARED=Path('/home/ghmd/Win共享文件/共享文件夹')
AURA=SHARED/'aura'
OUT=SHARED/'deliverables/2026-10-17_board_asr_host_files'
CODE=('scripts/start_board_asr.ps1','tools/asr_server.py','common/asr_wire.py','docs/BOARD_ASR.md',
      'board/runtime/audio/asr.py','board/runtime/audio/__init__.py','board/runtime/__init__.py','common/__init__.py')
MODEL='models/asr/sherpa-onnx-paraformer-zh-2023-09-14/'
MODELS=tuple(MODEL+n for n in ('model.int8.onnx','tokens.txt','test_wavs/0.wav'))

def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()

files={name:{'bytes':(AURA/name).stat().st_size,'sha256':digest(AURA/name),
             'kind':'source' if name in CODE else 'model'} for name in CODE+MODELS}
manifest={'scope':'ASR_ONLY_REQUIRED_FILES','source_host':socket.gethostname(),'source_root':str(AURA),
          'files':files,'dependencies':{'accepted_windows_python':'3.10',
          'sherpa-onnx':'1.13.8','sherpa-onnx-core':'1.13.8','numpy':'required; accepted Windows baseline 2.2.6'},
          'optional_launcher_config':'../deliverables/2026-10-11_omnivoice_dialogue/machine_config.json or stage_config.json; alternatively pass -VoicePython',
          'windows_copy_not_inspected':True}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'ASR_REQUIRED_FILES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
shutil.copyfile(WORK/'check_asr_files.py',OUT/'check_asr_files.py')
release=hashlib.sha256(json.dumps({name:files[name] for name in CODE},sort_keys=True).encode()).hexdigest()[:16]
archive=OUT/('asr-host-complete-code-'+release+'.zip')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
    for name in CODE:z.write(AURA/name,name)
    z.write(OUT/'ASR_REQUIRED_FILES.json','ASR_REQUIRED_FILES.json')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(CODE)|{'ASR_REQUIRED_FILES.json'}
    for name in CODE:assert z.read(name)==(AURA/name).read_bytes()

# Verify the previously accepted, frozen model/reference handover independently.
baseline=SHARED/'deliverables/2026-10-11_voice_accepted'
assets=[]
for source in ('model_files.json','baseline_files.json'):
    for row in json.loads((baseline/source).read_text(encoding='utf-8-sig'))['files']:
        path=SHARED/row['path']
        exists=path.is_file()
        ok=exists and path.stat().st_size==row['bytes'] and digest(path)==row['sha256']
        assets.append({'path':row['path'],'exists':exists,'matches_saved_manifest':ok,'bytes':row['bytes']})
result={'scope':'UBUNTU_ASR_FILES_AND_ACCEPTED_VOICE_ASSETS','host':socket.gethostname(),
        'asr_required_files':len(files),'asr_sources':len(CODE),'asr_model_files':len(MODELS),
        'asr_model_bytes':sum(files[name]['bytes'] for name in MODELS),
        'accepted_assets_checked':len(assets),'accepted_assets_passed':sum(r['matches_saved_manifest'] for r in assets),
        'accepted_assets':assets,'ollama_on_path':shutil.which('ollama'),
        'nvidia_smi_on_path':shutil.which('nvidia-smi'),
        'windows_directory_listing_available':False,'windows_environment_verified':False,
        'complete_code_archive':str(archive),'code_archive_bytes':archive.stat().st_size,
        'code_archive_sha256':digest(archive),'model_weights_in_code_archive':False,
        'other_project_paths_outside_sync_root':['/home/ghmd/AMD_Smart','/home/ghmd/下载/项目.zip',
            '/home/ghmd/aura-asr-integration-20261016']}
(WORK/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(OUT/'ubuntu_inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='accepted_assets'},ensure_ascii=False))
