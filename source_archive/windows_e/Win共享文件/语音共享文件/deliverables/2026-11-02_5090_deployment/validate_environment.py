"""Validate the isolated host directly, without changing PowerShell policy."""
import hashlib
import importlib.metadata as metadata
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXPECTED_REVISION = 'c5fdb5ccb189668d56333f77ba2629f4cd7535f4'


def main():
    import torch

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('Exactly one available CUDA GPU is required')
    capability = list(torch.cuda.get_device_capability(0))
    architectures = torch.cuda.get_arch_list()
    if capability != [12, 0] or 'sm_120' not in architectures:
        raise RuntimeError('The target GPU architecture is not supported by this runtime')
    specs = [line.strip().split('==') for line in
             (HERE / 'voice_py310_requirements_5090.txt').read_text(encoding='utf-8-sig').splitlines()
             if line.strip() and not line.startswith('#')]
    for name, expected in specs:
        if metadata.version(name) != expected:
            raise RuntimeError('Installed package differs from the migration lock: ' + name)
    tiny = float(torch.ones(1, device='cuda').sum().item())
    torch.cuda.synchronize()
    if tiny != 1.0:
        raise RuntimeError('The CUDA kernel validation did not produce the expected result')
    model_root = ROOT / 'aura/models/tts/OmniVoice'
    identity = json.loads((model_root / 'download_identity.json').read_bytes())
    if identity.get('repository') != 'k2-fsa/OmniVoice' or identity.get('revision') != EXPECTED_REVISION:
        raise RuntimeError('The formal OmniVoice identity changed')
    checked = []
    for item in identity['files']:
        path = (model_root / item['path']).resolve()
        if not path.is_relative_to(model_root.resolve()) or path.stat().st_size != item['bytes']:
            raise RuntimeError('Missing or incomplete formal TTS file')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != item['sha256']:
            raise RuntimeError('Formal TTS file SHA256 differs: ' + item['path'])
        checked.append(dict(path=item['path'], bytes=item['bytes'], sha256=digest.hexdigest()))
    print(json.dumps(dict(passed=True, python=sys.version, executable=sys.executable,
        torch=torch.__version__, cuda_build=torch.version.cuda,
        gpu=torch.cuda.get_device_name(0), compute_capability=capability,
        compiled_arch_list=architectures, tiny_cuda_result=tiny,
        exact_packages_checked=len(specs), tts_revision=EXPECTED_REVISION,
        tts_files_verified=checked, models_started=False, board_accessed=False), ensure_ascii=False))


if __name__ == '__main__':
    main()
