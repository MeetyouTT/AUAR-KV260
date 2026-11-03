"""Three isolated v90 source edits; never edits the source snapshot or frozen M03."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

D = Path(__file__).resolve().parent
H = D.parent
BASE = H / 'candidate_m03_v90_stage/public_runtime_v90'
MAPPING = H / 'candidate_m03_v90_stage/source_mapping.v90.json'
mapping = json.loads(MAPPING.read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def edit(raw, old, new):
    ending = '\r\n' if b'\r\n' in raw else '\n'
    a = old.replace('\n', ending).encode('utf-8')
    b = new.replace('\n', ending).encode('utf-8')
    assert raw.count(a) == 1, old
    return raw.replace(a, b)


relative = 'board/runtime/board_business.py'
business_before = (BASE / relative).read_bytes()
assert sha(business_before) == '482e250cf42cecd21358f4159a9550e4b384c3c223ee1f367e3c1d796423a198'
old_wiring = '''                visual=self.identity_handler._visual(job), is_current=is_current,
                cancel_event=cancel_event, deadline=job.deadline, on_evidence=evidence)'''
new_wiring = '''                visual=self.identity_handler._visual(job), is_current=is_current,
                gallery_provider=lambda: self.identity_handler._gallery(job),
                cancel_event=cancel_event, deadline=job.deadline, on_evidence=evidence)'''
business_after = edit(business_before, old_wiring, new_wiring)
changes = {relative: business_after}

relative = 'tools/provisional_voice.py'
raw = (BASE / relative).read_bytes()
raw = edit(raw,
    "    if text.strip(' 。！!？?') not in ('我是谁','你知道我是谁吗','听声音我是谁','你认识我的声音吗'):return None",
    "    from common.voice_enrollment import identity_query_requested\n"
    "    if not identity_query_requested(text) and text.strip(' 。！!？?') not in ('听声音我是谁','你认识我的声音吗'):return None")
changes[relative] = raw

relative = 'board/runtime/board_speaker_business.py'
raw = (BASE / relative).read_bytes()
raw = edit(raw,
    '    def submit_analysis(self,meta,pcm,conversation_id,*,visual=None,on_evidence=None,**kwargs):',
    '    def submit_analysis(self,meta,pcm,conversation_id,*,visual=None,gallery_provider=None,on_evidence=None,**kwargs):')
raw = edit(raw,
    '''        cid = validate_conversation_id(conversation_id); meta = context(meta,pcm)
        visual = validate_visual(visual,meta) if visual is not None else unavailable(meta)
        key = meta['board_boot_id'],meta['session_id'],meta['request_id']''',
    '''        cid = validate_conversation_id(conversation_id); meta = context(meta,pcm)
        visual = validate_visual(visual,meta) if visual is not None else unavailable(meta)
        if gallery_provider is not None and not callable(gallery_provider):
            raise ValueError('Local read-only gallery provider must be callable')
        key = meta['board_boot_id'],meta['session_id'],meta['request_id']''')
raw = edit(raw,
    '''            value = binding.precomputed_analysis(meta,cid,visual) if binding is not None else None
            if value is None:
                analyzer = self.hub.progressive_speaker''',
    '''            value = binding.precomputed_analysis(meta,cid,visual) if binding is not None else None
            if value is None:
                observed_visual = visual
                if binding is not None and gallery_provider is not None:
                    # Read/hash only on the original sole CPU worker, never the
                    # foreground route or GTK tick. This is observation only:
                    # no enrollment router, consent, template or grant is made.
                    try:
                        packet = gallery_provider()
                        if not self._current():
                            raise InterruptedError('Face observation no longer owns the capture')
                        if observed_visual['state'] == 'FACE_AT_CAPTURE_BOUNDARIES':
                            age = round(self.clock()*1000)-observed_visual['evidence']['source_end_ms']
                            if not 0 <= age < 3000:
                                observed_visual = unavailable(meta,'VISUAL_EXPIRED_BEFORE_ANALYSIS')
                        reference = None
                        if packet is not None:
                            from common.face_binding_wire import validate_packet
                            packet = validate_packet(packet,meta)
                            digest = binding.ingest_gallery(packet)['packet_sha256']
                            reference = binding._gallery_for(meta,digest)
                        binding._face_reference(meta,observed_visual,reference)
                    except InterruptedError:
                        raise
                    except (OSError,ValueError,KeyError,TypeError,TimeoutError,sqlite3.Error):
                        # A bad/missing face readback cannot invent a face name
                        # or suppress an otherwise valid independent voice.
                        binding._face_reference(meta,observed_visual,None)
                analyzer = self.hub.progressive_speaker''')
raw = edit(raw,
    '                    face = binding.face_naming_proof(meta,visual)',
    '                    face = binding.face_naming_proof(meta,observed_visual)')
raw = edit(raw,
    '                               voice=voice,visual=visual,anonymous=alias,identity=identity)',
    '                               voice=voice,visual=observed_visual,anonymous=alias,identity=identity)')
raw = edit(raw,
    "        self.jobs = {}; self.latest = OrderedDict(); self.results = OrderedDict()",
    "        self.jobs = {}; self.latest = OrderedDict(); self.results = OrderedDict()\n"
    "        self.last_evidence_error = None")
raw = edit(raw,
    '''                except Exception:
                    with self.lock:
                        self.counts['evidence_errors'] += 1''',
    '''                except Exception as exc:
                    name = type(exc).__name__
                    error = (name if name in ('PermissionError','TimeoutError','ValueError','TypeError',
                        'RuntimeError','OSError','ClockUnavailable') else
                        'SQLiteError' if isinstance(exc,sqlite3.Error) else 'OtherError')
                    with self.lock:
                        self.counts['evidence_errors'] += 1
                        self.last_evidence_error = dict(stage='evidence_callback',error=error)''')
raw = edit(raw,
    '                        data_origin=self.data_origin,queued_or_active=len(self.jobs),maximum_job_slots=2,',
    '                        data_origin=self.data_origin,queued_or_active=len(self.jobs),maximum_job_slots=2,\n'
    '                        last_evidence_error=copy.deepcopy(self.last_evidence_error),')
changes[relative] = raw

files = {}
diffs = []
for relative, raw in sorted(changes.items()):
    before = (BASE / relative).read_bytes()
    assert sha(before) == mapping['component_pins'][relative]
    target = D / 'after' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    files[relative] = dict(before_sha256=sha(before), sha256=sha(raw), bytes=len(raw))
    diffs.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),raw.decode().splitlines(keepends=True),
        fromfile='before/'+relative,tofile='after/'+relative))
(D / 'CANDIDATE.diff').write_bytes(''.join(diffs).encode('utf-8'))

def ast_node(raw, name):
    return next(n for n in ast.parse(raw).body if getattr(n, 'name', None) == name)

assert ast.dump(ast_node(business_before,'create_board_business_runtime')) == ast.dump(ast_node(business_after,'create_board_business_runtime'))
m03 = H / 'candidate_m03_v90_stage/after/board/runtime/board_business.py'
assert sha(m03.read_bytes()) == 'b336371df9584740d81b499d5191873c97bb8971343b0084e0c7b584d793f02e'
merged = edit(m03.read_bytes(),old_wiring,new_wiring)
target = D / 'combined_with_frozen_M03/board/runtime/board_business.py'
target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes(merged)
assert edit(merged,new_wiring,old_wiring) == m03.read_bytes()
proof = dict(schema='aura.identity-cooperation-v90.merge-proof.v1',
    v90_business_before_sha256=sha(business_before), identity_only_business_sha256=sha(business_after),
    frozen_M03_business_sha256=sha(m03.read_bytes()), combined_business_sha256=sha(merged),
    reverse_identity_wiring_restores_frozen_M03_bytes=True, cold_bootstrap_factory_AST_unchanged=True,
    GTK_or_audio_sources_modified=False, frozen_M03_sources_modified=False)
(D / 'MERGE_PROOF.json').write_bytes((json.dumps(proof,indent=2)+'\n').encode())
manifest = dict(schema='aura.identity-cooperation-v90.candidate.v1',status='LOCAL_CANDIDATE_NOT_DEPLOYED',
    baseline_startup_sha256=mapping['startup_sha256'],baseline_mapping_sha256=sha(MAPPING.read_bytes()),
    baseline_source_manifest_sha256=mapping['source_manifest_sha256'],files=files,
    speaker_calibration_changed=False,thresholds_changed=False,new_enrollment_or_profile_grant=False,
    gallery_readback_worker='existing single board-speaker-cpu',M03_frozen=True,
    cold_boot_factory_AST_unchanged=True,GTK_or_audio_sources_modified=False)
(D / 'SOURCE_MANIFEST.json').write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(files=len(files),manifest_sha256=sha((D/'SOURCE_MANIFEST.json').read_bytes()),
    combined_business_sha256=sha(merged))))
