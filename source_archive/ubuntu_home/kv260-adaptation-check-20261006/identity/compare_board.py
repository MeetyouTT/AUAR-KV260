#!/usr/bin/env python3
"""Compare captured board output with the already verified host reference."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
pointer = json.loads((ROOT / 'CURRENT_IDENTITY_TEST.json').read_text())
assert pointer['rc'] == 0
evidence = Path(pointer['evidence'])
raw = (evidence / 'result.txt').read_bytes()
assert hashlib.sha256(raw).hexdigest() == pointer['output_sha256']
board = json.loads(raw)
host = np.load(ROOT / 'identity/reference/host_reference.npz')
faces = np.asarray(board['faces'], dtype=np.float32)
assert faces.shape == host['faces'].shape
error = float(np.max(np.abs(faces - host['faces'])))
feature = np.asarray(board['embedding'], dtype=np.float64)
reference = host['feature'].astype(np.float64)
cosine = float(np.dot(feature, reference) / (np.linalg.norm(feature) * np.linalg.norm(reference)))
assert error < .001, error
assert cosine > .99999, cosine
result = {
    'passed': True, 'role': 'CPU_REFERENCE', 'board_opencv': board['opencv'],
    'board_boot_id': board['boot_id'], 'board_evidence': str(evidence),
    'max_detection_abs_error': error, 'embedding_cosine': cosine,
    'warm_samples': len(board['benchmark']),
    'warm_median_ms': {key: float(np.median([r[key] for r in board['benchmark']]))
                       for key in ('detection_ms', 'recognition_ms', 'total_ms')},
    'camera_opened': False, 'fpga_modified': False,
}
(ROOT / 'identity/reference/cross_board_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
