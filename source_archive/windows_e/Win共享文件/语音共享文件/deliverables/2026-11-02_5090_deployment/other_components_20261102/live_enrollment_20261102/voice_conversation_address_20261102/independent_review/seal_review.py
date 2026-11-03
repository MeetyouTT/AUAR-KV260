"""Seal local-only independent evidence without modifying product sources."""
import ast,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
pins=json.loads((HERE/'LOADED_SOURCE_PINS.json').read_text(encoding='utf-8'))
for name,pin in pins.items():assert sha(ROOT/'candidate_runtime'/name)==pin
for name,p in manifest['files'].items():
    assert sha(ROOT/'candidate_runtime'/name)==p['after_sha256']==pins[name]
    assert sha(ROOT/'baseline_runtime'/name)==p['before_sha256']
def files(root):
    return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
reference=ROOT.parent/'voice_threshold_035_production_entry_20261102/candidate_runtime'
before,after=files(reference),files(ROOT/'candidate_runtime')
assert before.keys()==after.keys() and len(after)==352
changed=sorted(n for n in before if before[n]!=after[n])
assert changed==sorted(manifest['files'])
def methods(path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    result={}
    for cls in tree.body:
        if isinstance(cls,ast.ClassDef):
            for f in cls.body:
                if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    result[cls.name+'.'+f.name]=ast.dump(f,include_attributes=False)
    return result
name='board/runtime/board_speaker_business.py'
a,b=methods(reference/name),methods(ROOT/'candidate_runtime'/name)
modified=[n for n in a.keys()&b.keys() if a[n]!=b[n]]
assert sorted(modified)==sorted('BoardSpeakerBusiness.'+n for n in ('__init__','_refresh_public','submit_analysis','reset'))
preserved=['_submit','_run','_call','route','turn','_self_match_query','_adopt_self_match','_clear_self_match',
           '_cancel_actor','analysis_result','cancel_analysis']
assert all(a['BoardSpeakerBusiness.'+n]==b['BoardSpeakerBusiness.'+n] for n in preserved)
unchanged=['tools/provisional_voice.py','tools/progressive_speaker.py','common/speaker_turns.py',
 'tools/speaker_device.py','common/speaker_identity.py','board/identity/store.py',
 'common/identity_links.py','tools/binding_hub_runtime.py','tools/production_board_business_gui.py',
 'tools/formal_yuki.py','tools/yuki_jobs_candidate.py','common/feature_intents.py']
assert all(before[n]==after[n] for n in unchanged)
cohorts={}
for name in ('INDEPENDENT_FINAL.xml','INDEPENDENT_WAIT_BOUNDARIES.xml'):
    doc=ET.parse(HERE/name).getroot()
    cases=list(doc.iter('testcase'))
    assert not list(doc.iter('failure')) and not list(doc.iter('error'))
    cohorts[name]=len(cases)
assert sum(cohorts.values())==32
verdict={
 'status':'PASS','scope':'offline independent synthetic composition and boundary tests',
 'candidate_files':manifest['files'],'tests_passed':32,'tests_failed':0,'cohorts':cohorts,
 'full_public_source_count':352,'only_changed_sources':changed,
 'actual_production_class':'ProductionGuiBoardBusiness',
 'physical_GTK_constructor_or_board_bootstrap_IO_executed':False,
 'actual_Runtime_constructor_formal_pair_Yuki_LIR_worker_used':True,
 'recording_stream_playback_ACK_rearm_tested':True,
 'first_ordinary_capture_encodes':1,'first_ordinary_named_store_match_calls':1,
 'field_calibrated':False,'identity_verified':False,'personal_memory_allowed':False,
 'threshold':.35,'margin':.1,'enrollment_consistency':.6,'anonymous_threshold':.9,
 'original_three_query_worker_path_AST_unchanged':True,
 'original_worker_methods_AST_unchanged':preserved,
 'other_original_components_byte_unchanged':unchanged,
 'product_files_edited_by_reviewer':0,'device_endpoint_model_or_real_identity_data_accessed':False,
 'limitations':[
  'Models/ASR/VAD/capture/audio output and private face readback are synthetic IO; real recognition accuracy and natural LLM wording are not asserted.',
  'Later turns may use the adopted conversation address before background analysis of that turn finishes. A different speaker may be addressed with the previous name on that turn; accepted negative evidence clears subsequent context. It remains an address candidate, not authentication.',
  'A short first sentence cannot pass the unchanged 3s PCM/2.5s VAD gate; it receives normal dialogue and the next valid sentence retries acquisition.',
  'Physical native GTK startup and GPU/render performance were not executed; root owns guarded deployment and real-world acceptance.'
 ],
 'historical_evidence':['INDEPENDENT_V1.xml','INDEPENDENT_V1_TARGETED_FIXTURE_CORRECTED.xml','INDEPENDENT_V2.xml'],
 'fixture_corrections':[
  'Two synthetic source-fixture writes originally hit the unchanged GuardedStore current-capture guard. Fixture setup was corrected to use the original synthetic Store on its owning worker; production guards and registration behavior were not changed.',
  'The original budget test input exceeded capacity before the address note; it was shortened to a valid near-capacity input.',
  'The original model tests relabeled only the inner synthetic encoder. Final tests mutate the canonical device GuardedEncoder fields, which the production guard correctly checks.',
  'An intermediate targeted rerun failed collection because source SHA changed during root edits. Strict source assertions were retained and updated to the root-announced final four-file pins.'
 ]}
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(verdict,indent=2)+'\n',encoding='utf-8')
report='''Independent review: PASS, 32/32 offline tests.

The actual production factory class and its own speaker-attach override were
used with full BoardBusinessRuntime construction, the actual formal pair,
instance-bound Yuki Jobs/LIR routing, original sole speaker worker, Device,
Store and Provisional matcher. A first valid ordinary statement performs one
encode and one named Store.match, then supplies its registered display_name
to the first LLM message context. Subsequent same-conversation use can proceed
while the next encoder is blocked. Actual Recording -> Streaming -> playback
receipt -> ACK -> rearm was exercised for two ordinary turns without reset.

The suite covers five daily identity questions, first/follow-up short speech,
effective unknown and ambiguous matches, conversation/source/model/dimension
change, reset/cancel during inference, completed-but-not-adopted cancellation,
late old-owner adoption, pending and adopted TTL, explicit profile exclusion,
retry without another encode, strict original three-sample registration plus
final confirmation, queries during active registration, public metadata and
private-cache audio/closure exclusion, near-capacity context budgeting and
unchanged explicit history handling. Two additional waiter tests demonstrate
prompt exit on cancellation and the unchanged 12s analysis deadline even while
the encoder remains blocked.

Candidate source assertions remained enabled. Across 352 public source files,
only the four root-manifest product files differ. Existing worker submit/run/
call/route/turn/self-match/adoption/cancellation/analysis methods listed in
REVIEW_VERDICT.json remain AST-identical. Original enrollment, quality,
Provisional matcher, named Store, identity-link registry, production factory,
formal pair, Yuki route and grammar modules remain byte-identical.

All models, ASR/VAD, audio capture/output, face readback and identity databases
were synthetic. No board, endpoint, real voice or private identity source was
accessed, and the reviewer modified no product files. This validates context
delivery and control boundaries; it does not measure real-world match accuracy,
real LLM natural wording, physical GUI/native startup or GPU performance.

The address is a volatile nonauthorizing conversation candidate. The actual
threshold .35 / margin .1 / registration consistency .6 and field_calibrated
false remain; no linked person or private-memory grant is created. A later
capture's negative match may arrive after cached-address output starts, so it
can clear later context but cannot retract already played audio. The user has
reported the current scenario contains only that user; speaker-change accuracy
has not been accepted. A short first sentence still uses ordinary dialogue
without a name until a quality-passing sentence arrives.

Historical V1/V2 XML is preserved. Fixture corrections and the changed-source
collection guard are described explicitly in REVIEW_VERDICT.json; they were
not hidden by weakening product guards or source assertions.
'''
(HERE/'REVIEW.txt').write_text(report,encoding='utf-8')
print(json.dumps({'status':'PASS','tests_passed':32,'verdict_sha256':sha(HERE/'REVIEW_VERDICT.json'),
 'report_sha256':sha(HERE/'REVIEW.txt'),'worker_existing_methods_changed':sorted(modified)},indent=2))
