"""Write an offline independent-review artifact; no candidate or device mutation."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPT = HERE.parent
OUT = OPT.parent
CANDIDATE = OPT / 'camera/validate_fresh_final_history_readonly.py'
EXPECTED_SHA = 'e92d8b0c461ff060d2e6d5e0aceef81c13ad1580cc3f66ad118b27c805b9f102'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert digest(CANDIDATE) == EXPECTED_SHA
aliases = json.loads((HERE / 'FRESH_HISTORY_ALIAS_NEGATIVES.json').read_text(encoding='utf-8'))
assert aliases['candidate_sha256'] == EXPECTED_SHA
assert aliases['unexpected_alias_acceptances'] == 3
test_record = json.loads((OPT / 'camera/FRESH_FINAL_HISTORY_TESTS.json').read_text(encoding='utf-8'))
assert test_record['candidate_sha256'] == EXPECTED_SHA

inputs = [
    CANDIDATE,
    OUT / 'maintenance_original_axis_20261101/checkpoint_review/validate_current_final_complete_readonly.py',
    OPT / 'camera/CAMERA_NORMAL_STOP_REUSE.json',
    OPT / 'camera/FRESH_FINAL_HISTORY_TESTS.json',
    OPT / 'camera/FRESH_FINAL_HISTORY_TESTS.log',
    OPT / 'camera/test_fresh_final_history_readonly.py',
    HERE / 'check_fresh_history_source_aliases.py',
    HERE / 'FRESH_HISTORY_ALIAS_NEGATIVES.json',
]

positives = [
    {
        'area': 'Original readers and Native exclusion',
        'evidence_lines': [122, 329, 382, 393, 407],
        'finding': 'The actual CLI pins the original four Python sources; fresh -B -I -S and aarch64 guards precede exact original module execution in a sealed board namespace. It calls original load_business_checkpoint without a now_ns override, then original _sealed_source for current and every v2 archive and _legacy_source for the terminal. No NativeContext instance, aura CDLL construction, restore or consume call is present. Seed/Recovery ctypes structures in pure validators are not NativeContext.',
        'result': 'STATIC_PASS',
    },
    {
        'area': 'Current owner, normal stop, time and counter domains',
        'evidence_lines': [160, 215, 298, 329],
        'finding': 'Fresh kernel/owner/startup/stop-intent/result pins are tied to the stopped owner. Both services must be inactive/dead with MainPID 0, no job and successful normal exit. The camera infinite-stop protection is checked, old owner births must be absent and live Native/VART/DPU/MMIO owners cause HOLD. Current source boot/PID/birth and stop/capture monotonic bounds are checked. All declared current SFace/optional/Native/recovery lower bounds are checked within the current domain, with probe-success progress limited to unchanged fault/attempt generation.',
        'result': 'STATIC_PASS',
    },
    {
        'area': 'Exact complete history and manifest scope',
        'evidence_lines': [254, 267, 354],
        'finding': 'The expected archive manifest concatenates a fresh prefix and accepted ordered segments exactly. Chain traversal checks each exact ordered row, raw archive SHA, edge boot/source checkpoint identity, duplicate paths/boots, canonical v2 checkpoint SHA and original archived semantics. It requires an exact terminal legacy anchor at the expected count, preserving lower-bound/unknown-tail scope, and refuses bounded traversal or early terminal truncation. Archived counters are not added to or required as current lower bounds. The current manifest is tied to the actual stopped-owner run config; archived manifests remain tied to their own archive provenance.',
        'result': 'STATIC_PASS_WITH_SOURCE_INDEPENDENCE_BLOCKER_BELOW',
    },
    {
        'area': 'Read-only behavior and failure path',
        'evidence_lines': [88, 153, 407],
        'finding': 'Snapshot reads use O_RDONLY, NOFOLLOW, bounded regular files and per-path before/after identities, then recheck every input. The adapter has no marker/seed/checkpoint/database/model write, service mutation, network or hardware command. Its only systemctl use is show. Failure reports HOLD without recovery. This local review and its isolated probes did not execute guard, original_modules or the board CLI.',
        'result': 'STATIC_PASS',
    },
]

blocker = {
    'id': 'CURRENT_FINAL_SOURCE_ALIAS',
    'severity': 'BLOCKS_INDEPENDENT_HISTORY_PROVENANCE_CLAIM',
    'candidate_lines': [196, 198, 199, 262, 266],
    'finding': 'The source-reference exclusion only compares path strings. Snapshot validates each source pin but does not reject another path with the pending-final SHA, nor a reserialized current checkpoint or an envelope containing it. The history head can therefore be sourced from the very pending final it is intended to check independently.',
    'negative_cases': aliases['results'][1:],
    'reproduction': {
        'script': str(HERE / 'check_fresh_history_source_aliases.py'),
        'method': 'Import the existing public in-memory fixture without invoking its unittest runner. For each case create a fresh fixture, change only source_bindings.head to a separately pinned representation of the pending final and recompute the provenance receipt pin. Call candidate.validate_inputs. Use the same synthetic legacy SHA substitution as the existing fixture. The unchanged baseline and all three aliases are accepted.',
        'scope': 'This proves acceptance at the source-independence gate, not a successful real board CLI run. The checkpoint, expected head, archive list and remaining semantic-chain inputs are unchanged. A real hardlink was not created; same-byte separate-path copy acceptance was reproduced.',
        'candidate_unchanged_before_after': True,
        'board_or_proc_io': False,
        'tests_run': 4,
    },
    'minimal_recommendation_no_patch_applied': [
        'Reject any source reference whose SHA equals a forbidden pending-final or stop-result pin, in addition to existing path exclusions. Include all other existing forbidden object pins where available. This catches accidental copies and hardlink aliases without a general signature framework.',
        'Before dereferencing the JSON pointer, reject a source object with schema aura-native-protection-checkpoint-2 whose seed boot_id, source_pid and source_birth_ticks identify the current stopped camera run. Apply the same check to a checkpoint object in the supported/known envelope shape (the reproduced case uses its checkpoint member). This catches the demonstrated different-format and envelope aliases while permitting older-boot or older-owner archive receipts. Add these three directed cases to the source-reference boundary tests.',
        'Keep a real fresh receipt explicitly captured and pinned by root before the stop, using original public metadata plus previously accepted ordered history receipts. Do not manufacture independent provenance by copying the pending final into a thin receipt. The source/receipt producer is part of the trusted operational procedure; a thin wrapper does not prove authenticity against a malicious root.',
    ],
    'threat_boundary': 'This is an accidental self-attestation/provenance-routing check. No claim is made that a script controlled by root can authenticate metadata against a malicious root who can rewrite all files and pins. No broad signing or hostile-root defense is requested.',
}

report = {
    'schema': 'aura-fresh-history-independent-review-1',
    'reviewer': 'gtk_cpu_optimize child agent, independent local source review',
    'candidate_sha256': EXPECTED_SHA,
    'verdict': 'HOLD_CURRENT_FINAL_SOURCE_ALIAS',
    'deployment_or_board_validation_authorized_by_this_report': False,
    'scope': 'Offline static comparison and four isolated public in-memory source-reference probes only. Original existing 16-test evidence was inspected, not rerun. Candidate source was not edited. No SSH, board query/load, service/GUI/camera/axis action, database/model access or original_modules execution occurred.',
    'inputs': [{'path': str(path), 'sha256': digest(path)} for path in inputs],
    'existing_test_evidence': test_record,
    'positive_findings': positives,
    'blockers': [blocker],
    'nonblocking_observation': 'The adapter permits stop_intent_mono_ns <= captured_mono_ns whereas the original comparison used strict <. This review has not demonstrated a real monotonic-clock false pass from equality; the reproduced source-alias gap alone determines HOLD.',
    'remaining_before_real_pass': [
        'Patch and independently recheck only the source-alias boundary with the directed negative cases; preserve original readers, exact chain, current counter-domain and normal-stop checks.',
        'Root must supply genuinely fresh current boot/owner/config/manifest/stop pins, original pre-stop bounds and independently captured ordered history provenance. Unknown values may not be inferred from the pending final.',
        'A real later run still requires exclusive writer freeze, successful original normal stops and fresh ARM -B -I -S execution. This local result does not assert any current board service or owner state.',
    ],
    'candidate_modified': False,
    'board_actions': [],
}

text_report = '''Independent offline review: HOLD_CURRENT_FINAL_SOURCE_ALIAS

Candidate: camera/validate_fresh_final_history_readonly.py
SHA256: e92d8b0c461ff060d2e6d5e0aceef81c13ad1580cc3f66ad118b27c805b9f102

The original reader/ABI, current owner/normal-stop/counter checks, exact complete
ordered archive traversal, terminal legacy semantics and read-only failure path
are preserved in the reviewed source. Archived counters stay in their own domain;
the current manifest is matched to the stopped owner's actual run config rather
than imposed on the history. Existing 16-test public synthetic evidence was read,
not rerun. Neither this review nor the isolated probes ran the board CLI, loader,
guard, NativeContext, services, models or hardware.

One source-independence blocker remains. referenced_value() at line 196 excludes
only path strings (line 198; forbidden set at 262). A separate source pin can name
the pending final's bytes or its same-owner semantic document at another path.
The provenance history head can consequently attest to itself. Snapshot does not
reject same-content aliases across paths.

Four directed public in-memory probes were run:
  baseline original receipt: accepted, expected
  same SHA separately pinned sealed-final copy: accepted, unexpected
  different JSON formatting of the same current final: accepted, unexpected
  envelope with checkpoint member containing the same current final: accepted,
    unexpected
Only source_bindings.head and its enclosing provenance pin were changed; the
current checkpoint, expected head and archive list were not changed. This proves
acceptance at validate_inputs, not an actual real-board complete CLI success.
No OS hardlink was created. The same-byte different-path copy is concrete.
Reproducer: validation/check_fresh_history_source_aliases.py
Evidence: validation/FRESH_HISTORY_ALIAS_NEGATIVES.json

Minimal recommendation, not applied here:
  1. Also reject source-pin SHA aliases of the pending final and stop-result
     (plus other existing forbidden pins where available), regardless of path.
  2. Before applying a source JSON pointer, reject an aura-native-protection-
     checkpoint-2 source identifying the current stopped boot/PID/birth, including
     the supported checkpoint envelope shape. Keep older boot/owner legitimate
     archive provenance usable. Add the three demonstrated cases as boundaries.
  3. Root must still capture and pin original public metadata before normal stop,
     joining it to previously accepted ordered history receipts. A thin receipt
     copied from the pending final is not independent provenance.

This addresses accidental self-attestation, not a hostile root who controls all
metadata and pins. No signature framework or general root-forgery defense is
implied. A real receipt's producer is part of the trusted operating procedure.

Nonblocking observation: adapter accepts stop_intent <= capture, whereas the old
reference used strict <. No real-clock false pass from equality was demonstrated;
the source-alias defect alone causes HOLD.

Candidate unchanged; all work local. Device ownership remains with the identity
chat. Do not use this report as a current-board readiness or stop/restore permit.
'''

with (HERE / 'FRESH_HISTORY_INDEPENDENT_REVIEW.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
with (HERE / 'FRESH_HISTORY_INDEPENDENT_REVIEW.txt').open('x', encoding='utf-8') as stream:
    stream.write(text_report)
assert digest(CANDIDATE) == EXPECTED_SHA
print(json.dumps({'verdict': report['verdict'], 'candidate_sha256': EXPECTED_SHA,
                  'outputs': [{'path': str(HERE / filename), 'sha256': digest(HERE / filename)}
                              for filename in ('FRESH_HISTORY_INDEPENDENT_REVIEW.json',
                                               'FRESH_HISTORY_INDEPENDENT_REVIEW.txt')]}))
