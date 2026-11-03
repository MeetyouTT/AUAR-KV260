"""Local copy-only migration of explicitly classified speech resources and source.

Never imports a model, accesses a device, follows reparse points, copies a venv,
or copies general language-model weights/Ollama data.
"""
from pathlib import Path
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import time

ENV = Path(__file__).resolve().parent
PACKAGE = ENV.parent
EXTERNAL = PACKAGE/'external_dependencies'
PROJECT = Path('E:/Win共享文件/语音共享文件')
OLD_BASE = Path('C:/Users/35870/.codex/visualizations/2026/10/09/01a12110-3ba4-7651-b3d7-2e6560916eb6')
VOICE_ENV = OLD_BASE/'omnivoice-runtime-py310'
VOICE_PYTHON = VOICE_ENV/'Scripts/python.exe'
SKIP_DIRS = {'.git', '.cache', '__pycache__', '.range-parts', 'venv', '.venv',
             'download-parts', 'parts', 'segments', 'hf_cache', 'hf-cache',
             'pip-cache', 'runtime', 'site-packages'}
SKIP_EXT = {'.pyc', '.pyo', '.db', '.sqlite', '.sqlite3', '.key', '.pem',
            '.mp4', '.avi', '.mp3', '.wav', '.flac', '.webm'}
RESOURCE_ROOTS = [
 ('D:/AIModels/ASR-candidates', 'ASR-candidates', 'ASR candidates; board Paraformer Small currently selected'),
 ('D:/AIModels/audio-frontend-eval-20261021', 'audio-frontend', 'GTCRN/Silero resources and aarch64 wheels'),
 ('D:/AIModels/speaker-identity/ecapa', 'speaker/ecapa', 'Speaker embedding resources; calibration not accepted'),
 ('D:/AIModels/speaker-identity/board-onnx-20261030', 'speaker/board-onnx', 'Board speaker ONNX and public fixture'),
 ('D:/AIModels/speaker-identity/board-webrtcvad-20261030', 'speaker/board-webrtcvad', 'Board VAD dependencies'),
 ('D:/AIModels/speaker-identity/wheels', 'speaker/wheels', 'Offline speaker dependency wheels'),
 ('D:/AIModels/talknet-interaction', 'talknet-interaction', 'Active-speaker experimental resources'),
 ('D:/AIModels/wake-keyword', 'wake-keyword', 'Historical wake-word candidate; feature currently disabled'),
 ('D:/AIModels/cosyvoice3-streaming-validation', 'CosyVoice3-TTS-candidate',
  'TTS-only candidate including CosyVoice3 GGUF; explicit ASR/TTS resource exception; not production LLM'),
 (str(VOICE_ENV/'Lib/site-packages/omnivoice'), 'source/omnivoice', 'Installed OmniVoice own Python source, not the virtualenv'),
]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def regular_files(root):
    stack = [root]
    while stack:
        folder = stack.pop()
        for path in folder.iterdir():
            info = path.lstat()
            if getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                continue
            if path.is_dir():
                if path.name not in SKIP_DIRS and not path.name.startswith(('pip-', 'download-part')):
                    stack.append(path)
            elif stat.S_ISREG(info.st_mode):
                if path.suffix.lower() not in SKIP_EXT and path.name.lower() not in ('auth.json', 'token', '.env'):
                    yield path, info


def main():
    ENV.mkdir(parents=True, exist_ok=True)
    EXTERNAL.mkdir(parents=True, exist_ok=True)
    plan = []
    for source, relative, purpose in RESOURCE_ROOTS:
        root = Path(source)
        if not root.is_dir():
            plan.append(dict(source=source, target=relative, purpose=purpose, exists=False, files=[]))
            continue
        assert not any(part.lower() in ('ollama-aura', 'qwen3.8-27b-abliterated', 'dflash2-qwen3.8-27b') for part in root.parts)
        rows = [dict(source=str(path), relative=path.relative_to(root).as_posix(),
                     bytes=info.st_size, mtime_ns=info.st_mtime_ns) for path, info in regular_files(root)]
        plan.append(dict(source=str(root), target=relative, purpose=purpose, exists=True,
                         file_count=len(rows), bytes=sum(row['bytes'] for row in rows), files=rows))
    (ENV/'DEPENDENCY_COPY_PLAN.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    tasks = []
    for entry in plan:
        for row in entry['files']:
            target = EXTERNAL/entry['target']/row['relative']
            tasks.append((row, target))
    def copy_one(task):
        row, target = task
        source = Path(row['source'])
        target.parent.mkdir(parents=True, exist_ok=True)
        assert target.is_relative_to(EXTERNAL)
        shutil.copy2(source, target, follow_symlinks=False)
        assert target.stat().st_size == row['bytes']
        digest = sha(target)
        assert sha(source) == digest
        return dict(source=str(source), target=str(target), bytes=row['bytes'], sha256=digest,
                    source_stat_unchanged=source.stat().st_size == row['bytes'] and source.stat().st_mtime_ns == row['mtime_ns'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        manifest = list(pool.map(copy_one, tasks))
    assert all(row['source_stat_unchanged'] for row in manifest)
    (ENV/'EXTERNAL_COPY_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    # Distribution metadata is read by the original interpreter; no torch/model import.
    metadata_code = "import importlib.metadata as m,json,sys,platform;print(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'packages':sorted([{'name':d.metadata['Name'],'version':d.version} for d in m.distributions()],key=lambda x:x['name'].lower())}))"
    environments = [('voice_py310', VOICE_PYTHON), ('analysis_py312', Path('D:/py312/python.exe')),
                    ('dashboard_codex_python', Path('C:/Users/35870/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'))]
    env_records = []
    for label, python in environments:
        if not python.is_file():
            env_records.append(dict(label=label, executable=str(python), exists=False))
            continue
        result = subprocess.run([str(python), '-I', '-B', '-c', metadata_code], capture_output=True,
                                text=True, encoding='utf-8', timeout=35, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert result.returncode == 0, label
        data = json.loads(result.stdout)
        (ENV/(label+'_packages.json')).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        frozen = '\n'.join(row['name']+'=='+row['version'] for row in data['packages'])+'\n'
        (ENV/(label+'_requirements_observed.txt')).write_text(frozen, encoding='utf-8')
        env_records.append(dict(label=label, executable=str(python), python=data['python'], packages=len(data['packages']),
                                exported_distribution_versions_only=True, virtualenv_copied=False))
    (ENV/'PYTHON_ENVIRONMENTS.json').write_text(json.dumps(env_records, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    # Save language-model identity/configuration references, never model payloads.
    llm_root = Path('D:/AIModels/qwen3.8-27b-abliterated')
    verified = json.loads((llm_root/'download_verified.json').read_text(encoding='utf-8-sig'))
    download = json.loads((llm_root/'download_manifest.json').read_text(encoding='utf-8-sig'))
    llm_info = dict(policy='NO_GENERAL_LLM_WEIGHTS_OR_OLLAMA_DATA_IN_E', weights_copied=False,
        active_model='aura-qwen3.8-27b-abliterated:iq4_xs', weights_directory=str(llm_root),
        ollama_directory='D:/AIModels/Ollama-AURA', draft_directory='D:/AIModels/dflash2-qwen3.8-27b',
        existing_verified_record=verified, existing_download_manifest=download,
        existing_checksum_recomputed=False,
        modelfile=(llm_root/'Modelfile').read_text(encoding='utf-8-sig'),
        recovery='Copy actual GGUF/Ollama files by a separate external medium into a model directory outside the E shared root, or re-download exact repository/revision then verify known SHA; never create E junctions.',
        model_file_is_link=(llm_root/verified['file']).is_symlink(),
        resolved_source=str((llm_root/verified['file']).resolve()))
    download_script = (llm_root/'download_model.py').read_text(encoding='utf-8')
    import re
    llm_info['download_url_references'] = sorted(set(re.findall(r'https://[^\s\"\'<>]+', download_script)))
    (ENV/'LLM_EXTERNAL_STORAGE_REFERENCE.json').write_text(json.dumps(llm_info, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    report = dict(schema='aura-migration-external-dependencies-1', status='COPIED_AND_HASH_VERIFIED',
        files=len(manifest), bytes=sum(row['bytes'] for row in manifest), roots=len(plan),
        verification='Every copied source and destination SHA256 recomputed and equal; source size/mtime unchanged',
        source_deleted_or_moved=False, model_or_device_services_called=False,
        llm_weights_or_ollama_data_copied=False, private_database_keys_or_media_copied=False,
        venv_copied=False, production_OmniVoice_already_under_E=True,
        manifest=str(ENV/'EXTERNAL_COPY_MANIFEST.json'), plan=str(ENV/'DEPENDENCY_COPY_PLAN.json'),
        python_environments=env_records)
    (ENV/'DEPENDENCY_MIGRATION_RESULT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
