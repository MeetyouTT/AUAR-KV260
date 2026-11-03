"""One-byte-range candidate; the original release stays untouched."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = HERE/'original/tools/board_camera_preview.py'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '6e697c16f7ae264dff56b6b35f38da4b531ea13026b69a7c8bdbfb1960a6afcd'
before = b'videoconvert ! videoscale ! video/x-raw,width='
after = b'videoscale ! videoconvert ! video/x-raw,width='
assert raw.count(before) == 1 and after not in raw
candidate = raw.replace(before,after)
assert candidate.replace(after,before) == raw
ast.parse(candidate.decode('utf-8'))
destination = HERE/'candidate/tools/board_camera_preview.py'
destination.parent.mkdir(parents=True,exist_ok=True)
with destination.open('xb') as stream:stream.write(candidate)
patch = ''.join(difflib.unified_diff(raw.decode().splitlines(True),candidate.decode().splitlines(True),fromfile='original/tools/board_camera_preview.py',tofile='candidate/tools/board_camera_preview.py'))
with (HERE/'pipeline_swap.diff').open('x',encoding='utf-8') as stream:stream.write(patch)
report = {'status':'CANDIDATE_READY_GST_EQUIVALENCE_AND_PERFORMANCE_PENDING',
    'component':'tools/board_camera_preview.py',
    'original_sha256':hashlib.sha256(raw).hexdigest(),
    'candidate_sha256':hashlib.sha256(candidate).hexdigest(),
    'changed_byte_ranges':1,'change':'Scale BGR at source format before converting to X11 sink format.',
    'preserved':['640x480 BGR input','output width/height','original default interpolation and aspect policy',
        'native X11 sink','queue and appsrc bounds','250ms stale-source drop','frame/owner identity',
        'source PTS and frame id','epoch reset','reference invalidation','multi-output lifetime locks',
        'JPEG fallback','all GTK/avatar/voice/identity/memory logic'],
    'performance_gain_claimed':False,'deployed':False}
with (HERE/'CANDIDATE_MANIFEST.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
