"""Apply the review patch to a NEW public-source copy inside research only."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

from build_review_patch import ROOT, REFERENCE, EXPECTED, patched_source


if __name__ == '__main__':
    # No existing directory is reused or removed. No production paths written.
    stage = ROOT / ('patch_check_' + uuid.uuid4().hex[:8])
    if not stage.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('unsafe_staging_path')
    stage.mkdir(exist_ok=False)
    target = stage / 'board/runtime/board_dialogue.py'
    target.parent.mkdir(parents=True)
    raw = REFERENCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError('reference_source_changed')
    target.write_bytes(raw)
    results = []
    for args in (['--check', '--whitespace=nowarn'], ['--whitespace=nowarn']):
        process = subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', *args, str(ROOT / 'integration_review.patch')],
                                 cwd=stage, capture_output=True, text=True, timeout=20)
        results.append(dict(operation='check' if '--check' in args else 'apply_to_isolated_copy',
                            exit_code=process.returncode))
        if process.returncode:
            raise RuntimeError('isolated_patch_validation_failed')
    _, expected = patched_source()
    if ast.dump(ast.parse(target.read_text(encoding='utf-8'))) != ast.dump(ast.parse(expected)):
        raise ValueError('patched_controller_ast_mismatch')
    added = stage / 'board/runtime/dialogue_chunk_policy.py'
    if added.read_bytes() != (ROOT / 'candidate/dialogue_chunk_policy.py').read_bytes():
        raise ValueError('patched_policy_mismatch')
    files = sorted(path.relative_to(stage).as_posix() for path in stage.rglob('*') if path.is_file())
    if files != ['board/runtime/board_dialogue.py', 'board/runtime/dialogue_chunk_policy.py']:
        raise ValueError('unexpected_patch_files')
    value = dict(status='PASS_PATCH_APPLIES_TO_ISOLATED_COPY_ONLY',
        prior_attempt='Windows Git core.autocrlf converted the new policy to CRLF after successful apply; source normalized to LF and autocrlf=false now pinned per verification command only',
        run_utc=datetime.now(timezone.utc).isoformat(), stage_relative_path=stage.name,
        base_sha256=EXPECTED, operations=results, changed_files=files,
        expected_controller_ast=True, expected_new_module_bytes=True,
        production_files_changed=False, services_or_devices_operated=False)
    (ROOT / 'PATCH_CHECK.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(value))
