"""Make isolated source-only test copies, verifying every copied installed source pin."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]
AURA = OUT.parents[1]/'aura'
receipt = json.loads((HERE/'CURRENT_SOURCE_AND_HEALTH.json').read_text(encoding='utf-8'))
baseline = OUT/'identity_dialogue_collaboration/baseline'
pins = receipt['component_sha256']
sources = {}
for relative, expected in pins.items():
    if not relative.endswith('.py'):
        continue
    for root in (HERE/'current_source', baseline, AURA):
        candidate = root/relative
        if candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest() == expected:
            sources[relative] = candidate.read_bytes()
            break
assert 'board/runtime/board_dialogue.py' in sources and 'board/runtime/audio/board_dialogue_jobs.py' in sources
assert 'common/model_inference_wire.py' in sources and 'common/inference_output_contract.py' in sources
manifest = {'installed_public_python_sources_copied': len(sources), 'all_copied_source_pins_verified': True,
            'actual_startup_sha256': receipt['startup_sha256'], 'runtimes': {}}
for mode in ('baseline_runtime_v2', 'candidate_runtime_v2'):
    target_root = HERE/mode
    assert not target_root.exists()
    for relative, raw in sources.items():
        if mode.startswith('candidate_') and (HERE/'candidate'/relative).is_file():
            raw = (HERE/'candidate'/relative).read_bytes()
        target = target_root/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    test_root = target_root/'tests/framework'
    test_root.mkdir(parents=True, exist_ok=True)
    for name in ('test_board_dialogue.py', 'test_board_dialogue_jobs.py'):
        raw = sources.get('tests/framework/'+name, (AURA/'tests/framework'/name).read_bytes())
        (test_root/name).write_bytes(raw)
    (test_root/'test_numeric_llm_metrics.py').write_bytes((HERE/'test_numeric_llm_metrics.py').read_bytes())
    manifest['runtimes'][mode] = str(target_root)
with (HERE/'SYNTHETIC_TEST_INPUTS.json').open('x', encoding='utf-8') as handle:
    json.dump(manifest, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps(manifest, ensure_ascii=True))
