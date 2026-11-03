"""Seal local evidence and pointers, with the candidate still ROOT_REVIEW_PENDING."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import xml.etree.ElementTree as ET

D = Path(__file__).resolve().parent
H = D.parent
BASE = H / 'candidate_m03_v90_stage/public_runtime_v90'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))


def results(name):
    root = ET.parse(D/name).getroot()
    cases = root.findall('.//testcase')
    return dict(path=name,sha256=sha(D/name),tests=len(cases),
        failures=sum(c.find('failure') is not None for c in cases),
        errors=sum(c.find('error') is not None for c in cases))


manifest = json.loads((D/'SOURCE_MANIFEST.json').read_bytes())
assert sha(D/'SOURCE_MANIFEST.json') == '6db50db1d9c211dc9935465b8ef5038d852c552e2cc288b8352cbb9febe8b7c0'
assert len(manifest['files']) == 3
mapping = json.loads((H/'candidate_m03_v90_stage/source_mapping.v90.json').read_bytes())
for relative,row in manifest['files'].items():
    assert sha(BASE/relative) == row['before_sha256'] == mapping['component_pins'][relative]
    assert sha(D/'after'/relative) == row['sha256']
source_paths = {p.relative_to(D/'after').as_posix() for p in (D/'after').rglob('*.py') if p.is_file()}
assert source_paths == set(manifest['files'])
assert not any(p.is_symlink() for p in (D/'after').rglob('*'))
non_sources = sorted(p.relative_to(D/'after').as_posix() for p in (D/'after').rglob('*') if p.is_file() and p.suffix!='.py')
assert all('/__pycache__/' in '/'+p and p.endswith('.pyc') for p in non_sources)

core = results('OWNER_CHECK_REGRESSION_01.xml')
visual = results('VISUAL_REGRESSION_FINAL.xml')
combined_tests = results('M03_COMPOSITION_02.xml')
baseline = results('BASELINE_FROZEN_FINAL.xml')
foreign_negative = results('OWNER_CHECK_NEGATIVE_01.xml')
assert (core['tests'],core['failures'],core['errors']) == (79,0,0)
assert (visual['tests'],visual['failures'],visual['errors']) == (103,0,0)
assert (combined_tests['tests'],combined_tests['failures'],combined_tests['errors']) == (48,0,0)
assert (baseline['tests'],baseline['failures'],baseline['errors']) == (9,8,0)
assert (foreign_negative['tests'],foreign_negative['failures'],foreign_negative['errors']) == (8,8,0)

before_ast = ast.parse((BASE/'board/runtime/board_business.py').read_bytes())
after_ast = ast.parse((D/'after/board/runtime/board_business.py').read_bytes())
removed = 0
for node in ast.walk(after_ast):
    if isinstance(node,ast.Call):
        old = len(node.keywords)
        node.keywords = [k for k in node.keywords if k.arg != 'gallery_provider']
        removed += old-len(node.keywords)
assert removed == 1 and ast.dump(before_ast) == ast.dump(after_ast)
before_speaker = ast.parse((BASE/'board/runtime/board_speaker_business.py').read_bytes())
after_speaker = ast.parse((D/'after/board/runtime/board_speaker_business.py').read_bytes())
def methods(tree):
    cls = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BoardSpeakerBusiness')
    return {n.name:ast.dump(n) for n in cls.body if isinstance(n,ast.FunctionDef)}
bm,am = methods(before_speaker),methods(after_speaker)
unchanged = sorted(set(bm)-{'__init__','submit_analysis','health'})
assert set(bm)==set(am) and all(bm[name]==am[name] for name in unchanged)
dump(D/'SOURCE_SCOPE_PROOF.json',dict(
    full_business_AST_restored_after_removing_exactly_one_gallery_provider_keyword=True,
    board_speaker_methods_changed=['__init__','submit_analysis','health'],
    board_speaker_other_methods_AST_identical=unchanged,
    calibration_threshold_enrollment_turn_route_close_reset_unchanged=True,
    GTK_audio_model_budget_schema_and_profile_authorization_sources_changed=False))

m03 = H/'candidate_m03_v90_stage'
frozen = {
    'SOURCE_MANIFEST.json':'cd462e0e26e5d41291afea66b8e598b7fcece0560ebe56257b2f79a132e7f820',
    'arm_public_worker.py':'fdd4fcc2a91d60ccd23040931d2633c3a08775c3a77213a21e4ee6c7688e9e68',
    'STAGING_MANIFEST.json':'58d1803a3e8820412f5923978202bb8c7ef46f2d9e7c14e27b328c187c6b2220',
    'after/board/runtime/board_business.py':'b336371df9584740d81b499d5191873c97bb8971343b0084e0c7b584d793f02e'}
assert all(sha(m03/rel)==digest for rel,digest in frozen.items())
first = json.loads((m03/'LAYOUT_V2_VERIFICATION.json').read_bytes())
assert sha(m03/'actual_arm_1793497883540736200.json') == first['preserved_first_ARM_receipt_sha256']
arm_path = m03/'actual_arm_layout2_1793499608505810500.json'
arm = json.loads(arm_path.read_bytes())
assert arm['process_exit_code']==0 and arm['public_stderr']==''
assert arm['result']['status']=='PASS' and arm['result']['tests']==8
assert arm['result']['verification']['hashed_components']==379 and arm['result']['verification']['live_all379_checked']
assert arm['result']['temporary_stores_removed'] and arm['result']['new_threads_remaining']==0

composition = {}
for relative,row in manifest['files'].items():
    source = D/'combined_with_frozen_M03'/relative if relative=='board/runtime/board_business.py' else D/'after'/relative
    composition[relative] = dict(source=str(source),before_sha256=row['before_sha256'],sha256=sha(source),bytes=source.stat().st_size)
for relative in ('board/runtime/history_delete.py','tools/production_memory_presentation.py'):
    source = m03/'after'/relative
    row = json.loads((m03/'SOURCE_MANIFEST.json').read_bytes())['files'][relative]
    assert sha(source) == row['sha256']
    composition[relative] = dict(source=str(source),before_sha256=row['before_sha256'],sha256=sha(source),bytes=source.stat().st_size)
dump(D/'COMBINED_M03_SOURCE_MANIFEST.json',dict(schema='aura.m03-identity-cooperation.composed-sources.v1',
    status='REVIEW_PREVIEW_NOT_DEPLOYED',files=composition,tests=combined_tests,
    frozen_M03_package_modified=False,other_root_stability_fixes_not_included=True))
original = (m03/'after/board/runtime/board_business.py').read_text(encoding='utf-8').splitlines(keepends=True)
composed = (D/'combined_with_frozen_M03/board/runtime/board_business.py').read_text(encoding='utf-8').splitlines(keepends=True)
(D/'M03_PROVIDER_ONLY.diff').write_bytes(''.join(difflib.unified_diff(original,composed,
    fromfile='M03-b336/board/runtime/board_business.py',tofile='combined/board/runtime/board_business.py')).encode('utf-8'))

dump(D/'OWNER_CHECK_LOCAL_RESOLUTION.json',dict(status='LOCAL_FIXED_ROOT_REVIEW_PENDING',
    before_manifest_sha256=sha(D/'owner_check_review_before/SOURCE_MANIFEST.json'),
    after_manifest_sha256=sha(D/'SOURCE_MANIFEST.json'),before_negative=foreign_negative,after_regression=core,
    fix='validate_packet(packet,meta) before ingest_gallery or any gallery/version/link mutation',
    root_independent_review='../../performance_review_newboot/identity_cooperation_review/test_independent_counterexamples.py',
    root_independent_replay_complete=False))

artifacts = ['SOURCE_MANIFEST.json','CANDIDATE.diff','MERGE_PROOF.json','SOURCE_SCOPE_PROOF.json',
    'COMBINED_M03_SOURCE_MANIFEST.json','M03_PROVIDER_ONLY.diff','REVIEW_AND_HANDOFF.txt',
    'PUBLIC_COUNTEREXAMPLES_FROZEN.py','test_identity_cooperation.py','test_m03_composition.py','run_tests.py',
    'BASELINE_FROZEN_FINAL.xml','OWNER_CHECK_NEGATIVE_01.xml','OWNER_CHECK_REGRESSION_01.xml',
    'VISUAL_REGRESSION_FINAL.xml','OLD_KERNEL_GATE_BASELINE.xml','M03_COMPOSITION_02.xml','OWNER_CHECK_LOCAL_RESOLUTION.json']
handoff = dict(schema='aura.identity-cooperation-v90.handoff.v1',
    status='ROOT_REVIEW_PENDING_V90_FROZEN_V19_ACTUAL_REBASE_REQUIRED',deployed=False,
    baseline_startup_sha256=manifest['baseline_startup_sha256'],
    planned_root_v19_startup_sha256='de7772b898378d2263b0809d18c095a60585a672690371d2f072b2e04c2f574f',
    planned_v19_not_verified_or_rebound_here=True,persistent_listening_preference='root-reported false/PAUSED; unchanged here',
    source_manifest_sha256=sha(D/'SOURCE_MANIFEST.json'),source_files=3,
    transfer_only_manifest_source_paths=True,non_source_bytecode_excluded=non_sources,
    report='REVIEW_AND_HANDOFF.txt',regression=core,visual_regression=visual,composition=combined_tests,
    groups_overlap=True,core_breakdown=dict(new_cases=47,frozen9_repeated=9,original_speaker=16,original_v3=7),
    known_original_test_deselected='test_board_mode_cannot_bypass_board_kernel_lock_on_windows; unchanged baseline fails for missing migration receipt',
    owner_check_before_failure_preserved=True,root_independent_review_pending=True,
    M03_actual_ARM_root_evidence=dict(path=str(arm_path),sha256=sha(arm_path),status='PASS',tests=8),
    M03_frozen_hashes_verified=frozen,
    operational_limits=dict(real_device=False,real_model=False,real_private_store=False,production_write=False,
        speaker_calibration=False,threshold_change=False,new_profile_grants=False),
    remaining_gaps=['completed-link natural unlink/relink requires exact original identity selection and confirmation',
        'unlinked standalone face/voice records may still receive visitor answer in unified query',
        'unrestricted model text may make a false claim but cannot create link/authorization state',
        'live historical evidence_errors6 and visual errors104 not diagnosed by this local run'],
    artifacts={name:sha(D/name) for name in artifacts})
dump(D/'HANDOFF.json',handoff)
latest_path = H/'LATEST_FEATURE_HANDOFF.json'
latest = json.loads(latest_path.read_bytes())
latest['status'] = handoff['status']
latest['latest_identity_cooperation'] = dict(handoff='identity_cooperation_v90/HANDOFF.json',
    handoff_sha256=sha(D/'HANDOFF.json'),source_manifest_sha256=sha(D/'SOURCE_MANIFEST.json'),
    status=handoff['status'],root_independent_review_pending=True,source_files=3,deployed=False)
latest['latest_v90_staging'].update(actual_ARM_status='PASS_8_FULL379_EXIT0_STDERR_EMPTY',
    actual_ARM_layout_v2_executed=True,actual_ARM_tests_passed=8,
    actual_ARM_evidence='candidate_m03_v90_stage/'+arm_path.name,actual_ARM_evidence_sha256=sha(arm_path))
latest['latest_root_instruction']['priority'] = 'Root v19 stability release first; identity v90 candidate frozen pending independent review and actual v19 rebase; preserve false/PAUSED.'
dump(latest_path,latest)
print(json.dumps(dict(status=handoff['status'],handoff_sha256=sha(D/'HANDOFF.json'),source_manifest_sha256=sha(D/'SOURCE_MANIFEST.json'))))
