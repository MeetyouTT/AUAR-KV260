"""Preserve the single expressly requested public ACK metadata read."""
from pathlib import Path
import hashlib
import json
import sys
import time

HERE = Path(__file__).resolve().parents[1]
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

source = (HERE / 'remote/read_route_after_manual_r1.py').read_bytes()
result = json.loads(ssh('python3 -B -', source.decode('utf-8'), timeout=12))
report = dict(schema='aura-manual-r1-route-metadata-envelope-1',
              source_sha256=hashlib.sha256(source).hexdigest(),
              prior_manual_first_sample_mono=55442.752763967,
              prior_manual_ack_request_token='8db2358adf1cd749e621baaee14ec65a8b87ba50a042b8419a8dfa32c1e86f34',
              result=result)
path = HERE / 'evidence' / ('manual_r1_route_metadata_' + str(time.time_ns()) + '.json')
raw = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
with path.open('xb') as stream:
    stream.write(raw)
print(json.dumps(dict(evidence=str(path), sha256=hashlib.sha256(raw).hexdigest(), **report)))
