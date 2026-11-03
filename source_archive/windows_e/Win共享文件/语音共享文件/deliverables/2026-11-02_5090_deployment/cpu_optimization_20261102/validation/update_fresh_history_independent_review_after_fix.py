"""Update only our own local review artifacts after the directed alias recheck."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPT = HERE.parent
NEW_SHA = '5ca99d4231c686de0f89dac5792299bec13af517a5c6e2b8f73c4cc66b9285c9'
OLD_SHA = 'e92d8b0c461ff060d2e6d5e0aceef81c13ad1580cc3f66ad118b27c805b9f102'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


candidate = OPT / 'camera/validate_fresh_final_history_readonly.py'
assert digest(candidate) == NEW_SHA
probes_path = HERE / 'FRESH_HISTORY_ALIAS_FIX_INDEPENDENT_PROBES.json'
probes = json.loads(probes_path.read_text(encoding='utf-8'))
assert probes['candidate_sha256'] == NEW_SHA and probes['passed'] and probes['cases_run'] == 8
json_path = HERE / 'FRESH_HISTORY_INDEPENDENT_REVIEW.json'
text_path = HERE / 'FRESH_HISTORY_INDEPENDENT_REVIEW.txt'
assert digest(json_path) == '7d6a925d7414514e49a54c2882e0db6d7c574e8aa3d59caafad8391b42f2967f'
assert digest(text_path) == '46348b6c00f460553571a45c36a77741683f624de098cce0066b48ac93b27b39'
report = json.loads(json_path.read_text(encoding='utf-8'))
for path in (json_path, text_path):
    with (HERE / (path.name + '.e92.before.bin')).open('xb') as handle:
        handle.write(path.read_bytes())

previous_blocker = report['blockers'][0]
previous_blocker['status'] = 'RESOLVED_BY_5ca99_SOURCE_ALIAS_GATE'
previous_blocker['applies_to_candidate_sha256'] = OLD_SHA
previous_blocker['resolution'] = {
    'candidate_sha256': NEW_SHA,
    'new_gate_lines': [196, 214, 217, 219, 283],
    'finding': 'Source pins are now excluded by pending-final/stop-result/provenance SHA as well as path. Before any JSON pointer traversal, an iterative walk through bounded decoded JSON dictionaries/lists rejects v2 checkpoint objects identifying the current stopped boot/PID/birth, including checkpoint envelopes. No signature framework or metadata authentication claim is added.',
    'independent_probe_evidence': {'path': str(probes_path), 'sha256': digest(probes_path),
        'cases_run': 8, 'passed': True, 'results': probes['results']},
    'diff_evidence': {'path': str(HERE / 'FRESH_HISTORY_ALIAS_FIX_INDEPENDENT_DIFF.txt'),
        'sha256': digest(HERE / 'FRESH_HISTORY_ALIAS_FIX_INDEPENDENT_DIFF.txt')},
    'all_other_functions_and_top_level_ast_unchanged': True,
    'changed_existing_functions': probes['changed_existing_function_names'],
    'new_functions': probes['new_function_names'],
}
report['previous_candidate_sha256'] = OLD_SHA
report['candidate_sha256'] = NEW_SHA
report['verdict'] = 'PASS_OFFLINE_SOURCE_ALIAS_FIX'
report['scope'] = 'Prior offline independent static review plus a small-diff review and eight independent public in-memory source-reference probes against 5ca99. The original16 suite was not rerun. No candidate source edit, CLI, guard, original_modules, SSH, board/proc/device/service/marker/database/model operation occurred.'
report['blockers'] = []
report['resolved_findings'] = [previous_blocker]
report['independent_fix_probes'] = probes
report['existing_test_evidence_applicability'] = 'The existing16-test report belongs to e92 and remains historical evidence. AST comparison proves original reader/guard/current-domain/chain implementations and all other non-source-gate code unchanged; only the source-reference gate is covered by the new eight independent directed probes. Neither evidence is a real board CLI pass.'
for item in report['inputs']:
    if Path(item['path']) == candidate:
        item['sha256'] = NEW_SHA
for path in (
    OPT / 'camera/fresh_history_alias_fix/validate_fresh_final_history_readonly.py.e92.before.bin',
    OPT / 'camera/FRESH_HISTORY_ALIAS_FIX_PROBES.json',
    HERE / 'check_fresh_history_source_aliases_fixed.py',
    probes_path,
    HERE / 'FRESH_HISTORY_ALIAS_FIX_INDEPENDENT_DIFF.txt',
    HERE / 'FRESH_HISTORY_INDEPENDENT_REVIEW.json.e92.before.bin',
    HERE / 'FRESH_HISTORY_INDEPENDENT_REVIEW.txt.e92.before.bin',
):
    report['inputs'].append({'path': str(path), 'sha256': digest(path)})
for item in report['positive_findings']:
    if item['area'] == 'Exact complete history and manifest scope':
        item['result'] = 'STATIC_PASS'
    if item['area'] == 'Original readers and Native exclusion':
        item['evidence_lines'] = [122, 350, 403, 414, 428]
    elif item['area'] == 'Current owner, normal stop, time and counter domains':
        item['evidence_lines'] = [160, 235, 320, 350]
    elif item['area'] == 'Exact complete history and manifest scope':
        item['evidence_lines'] = [274, 288, 375]
    elif item['area'] == 'Read-only behavior and failure path':
        item['evidence_lines'] = [88, 153, 428]
report['remaining_before_real_pass'] = [
    'Root must supply genuinely fresh current boot/owner/config/manifest/stop pins, original pre-stop bounds and independently captured ordered history provenance. Unknown values may not be inferred from the pending final. The receipt producer remains trusted; a wrapper copied from a final is not authenticated by this fix.',
    'A later real run still requires exclusive writer freeze, successful original normal stops and fresh ARM -B -I -S execution. This offline PASS does not assert current board readiness or grant device ownership.',
]
with json_path.open('w', encoding='utf-8') as handle:
    json.dump(report, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
text_path.write_text('''Independent offline review: PASS_OFFLINE_SOURCE_ALIAS_FIX

Reviewed candidate SHA256:
5ca99d4231c686de0f89dac5792299bec13af517a5c6e2b8f73c4cc66b9285c9
Previous e92 review and its HOLD evidence remain in local .e92.before.bin copies.

The source-alias blocker is resolved in this offline scope. Independent review of
the exact diff confirms one new function (reject_current_checkpoint_source) and
changes only to referenced_value and validate_inputs. All other function and
top-level ASTs, including original reader/loader, guard, current bounds and full
ordered archive traversal, are identical to e92. The original source-reference
path and JSON-pointer rules are preserved, with new source SHA exclusions and a
checkpoint-object gate before dereferencing a pointer.

Eight independent directed public in-memory probes passed:
  baseline receipt: accepted
  same SHA final copy: rejected by SHA alias gate
  reserialized same-owner final: rejected by checkpoint-object gate
  same-owner final inside checkpoint envelope: rejected by checkpoint-object gate
  same SHA stop-result copy: rejected by SHA alias gate
  same boot, different PID source: accepted
  same boot/PID, different birth source: accepted
  prior-boot archive checkpoint envelope: accepted
The three original final-alias cases therefore fail at the intended source gate,
while demonstrated older/different-owner sources remain usable. No candidate
file was modified by the reviewer. The JSON walk only visits decoded JSON dicts
and lists; real source files remain subject to the existing bounded snapshot.

Independent evidence:
  FRESH_HISTORY_ALIAS_FIX_INDEPENDENT_PROBES.json
  FRESH_HISTORY_ALIAS_FIX_INDEPENDENT_DIFF.txt
  check_fresh_history_source_aliases_fixed.py

The original16 test suite was not rerun and its report still belongs to e92.
Unchanged AST plus these directed probes supports the limited offline result;
it is not a real board CLI or current-owner/readiness result. NativeContext,
original_modules, guard, SSH, services, proc, camera, axis, DB and model paths were
not executed. No stop/start/restore permission or device ownership is implied.

Root must still capture and pin genuine original public metadata before normal
stop and combine it with previously accepted ordered history receipts. The fix
addresses accidental current-final self-attestation; it does not authenticate
metadata against a malicious root who controls all source files and pins. A thin
receipt does not substitute for that trusted capture procedure.

Nonblocking observation from the prior review remains: adapter stop_intent <=
capture differs from original strict <; no real-clock false pass was demonstrated.
No new blocker was found within this requested small-diff/source-alias scope.
''', encoding='utf-8')
assert digest(candidate) == NEW_SHA
print(json.dumps({'candidate_sha256': NEW_SHA, 'verdict': report['verdict'],
    'outputs': [{'path': str(path), 'sha256': digest(path)} for path in (json_path, text_path, probes_path)]}))
