"""Reuse closed, retained download bytes after validating overlap with official ranges."""
import hashlib
import json
from pathlib import Path

CHUNK = 32 * 1024 * 1024
base = Path('E:/项目/tmp')
folder = base / 'qwen-young-voice-weight-parts'
report_folder = Path('E:/项目/共享文件夹/deliverables/2026-10-06_voice_design_young')
metadata = json.loads((report_folder / 'official_model_metadata.json').read_text(encoding='utf-8'))
entry = next(row for row in metadata['siblings'] if row['rfilename'] == 'model.safetensors')
partial = next((base / 'Qwen3-TTS-12Hz-1.7B-VoiceDesign/.cache/huggingface/download').glob('*.' + entry['lfs']['sha256'] + '.incomplete'))
source_size = partial.stat().st_size
reused = []
with partial.open('rb') as source:
    first = source.read(CHUNK)
    if hashlib.sha256(first).digest() != hashlib.sha256((folder / '0000.part').read_bytes()).digest():
        raise ValueError('Retained prefix did not match verified official range overlap')
    source.seek(0)
    for index in range(source_size // CHUNK):
        chunk = source.read(CHUNK)
        if len(chunk) != CHUNK:
            raise ValueError('Unexpected retained prefix size')
        destination = folder / f'{index:04d}.part'
        if destination.exists():
            if hashlib.sha256(chunk).digest() != hashlib.sha256(destination.read_bytes()).digest():
                raise ValueError('Retained prefix and official range differ')
            continue
        temporary = folder / f'{index:04d}.reusedworking'
        temporary.write_bytes(chunk)
        temporary.replace(destination)
        reused.append(index)
result = {'retained_prefix_bytes': source_size, 'reused_part_indices': reused,
          'overlapping_ranges_sha256_match': True,
          'note': 'Directory-entry length while a file is open was stale. The original transfer had received data; retained bytes were reused. Final whole weight hash remains required.'}
(report_folder / 'retained_download_reuse.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print('REUSED ' + str(len(reused)) + ' retained ranges; final whole SHA256 still required', flush=True)
