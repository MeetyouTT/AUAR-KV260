from pathlib import Path
import hashlib
import json
import struct
import zipfile

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence'
with zipfile.ZipFile(EVIDENCE/'evidence-final.zip') as archive:
    for member in archive.infolist():
        path=(EVIDENCE/member.filename).resolve()
        assert path.is_relative_to(EVIDENCE.resolve())
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(archive.read(member))

def read(name): return json.loads((ROOT/name).read_text(encoding='utf-8'))
baseline=read('evidence/cpu-audit.json')
candidate=read('evidence/candidate-cpu-audit.json')
final=read('evidence/final-state.json')
gpu=read('evidence/gpu-render-r2-result.json')
state=read('static-parameter-comparison.json')
provenance=read('asset-provenance.json')
source=Path(provenance['psb_source_read_only'])
source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==provenance['files'][0]['sha256']
images=sorted((EVIDENCE/'candidate-captures').glob('*.png'))+sorted((EVIDENCE/'static-reference-captures').glob('*.png'))
image_hashes={}
for path in images:
    data=path.read_bytes()
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II',data[16:24])==(423,438)
    image_hashes[path.relative_to(ROOT).as_posix()]=hashlib.sha256(data).hexdigest()
assert len(images)==43
assert baseline['structural_import_ok'] and baseline['compiled'] and not baseline['ok']
assert all(not t['ok'] and t['failed_author_tick']==0 for t in baseline['timelines'])
assert candidate['ok'] and len(candidate['timelines'])==20
assert final['protected_files_changed']==[] and final['ui_state_matches_baseline']
assert final['validation_workers']==[] and source_unchanged
assert gpu['returncode']==0 and gpu['ui_unchanged']
assert read('reference-cleanup.json')['reference_process_stopped']
report={
    'status':'FIRST_VALIDATION_COMPLETE_COMPATIBILITY_NOT_ACCEPTED',
    'client_date':'2026-10-30',
    'scope':'yuk_0 single character, isolated ARM validation; no production deployment',
    'upstream_commit':read('source-provenance.json')['commit'],
    'unmodified_core':{'import_ok':True,'compile_ok':True,'initial_pose_ok':False,
                      'timeline_pass':0,'timeline_count':20,'failure_tick':0,
                      'failure':'UnsupportedMask: source node260 is constrained by mask11 and included in mask11 source members'},
    'experimental_candidate':{'accepted':False,'change':'clear self-mask only on copied mask-source draw commands; retain cross-mask rejection',
                            'physics_enabled':True,'initial_pose_180_steps_ok':True,
                            'timeline_pass':20,'timeline_count':20,'steps_per_timeline':180,
                            'mask_source_semantics_certified':False},
    'board_diagnostic':{'cpu':'aarch64 C++ runtime','gpu':'Mali-400 MP / OpenGL ES 2.0',
                        'host':'offline frame export + Python ctypes GLES2 offscreen diagnostic',
                        'dynamic_captures':41,'matched_parameter_captures':2,'size':[423,438],
                        'real_time_gtk_integration_tested':False,'physical_display_fps_certified':False,
                        'lip_sync_to_actual_pcm_tested':False},
    'compatibility_gaps':{'self_mask_source_scope_unverified':True,
                          'nonempty_meshCombinator_nodes':43,'combinator_entries':122,
                          'combination_semantics_implemented_in_pinned_core':False,
                          'visual_and_idle_fidelity_certified':False},
    'static_parameter_checks':state['same_parameter_snapshots'],
    'static_check_limit':'normal matches 37 visible variables; shy face_mouth remains deferred at tick0. Physics internal state is not aligned. Image differences do not establish a single root cause.',
    'preservation':{'fixed_source_dependency_inputs_checked':final['protected_files_checked'],
                    'fixed_source_dependency_inputs_changed':[],
                    'source_psb_unchanged':source_unchanged,'production_ui_unchanged':True,
                    'production_deployed':False,'remaining_validation_workers':[],
                    'temporary_reference_service_closed':True},
    'failures_retained':['SFTP unavailable; legacy SCP used','initial compile runner 300s timeout; compilation completed without production changes',
                         'waiter refused overlapping compilation','exporter TimelineId namespace corrected',
                         'GLES2 cross-stage precision mismatch corrected'],
    'next_step':'resolve mask-source scope and meshCombinator semantics against original engine before final GLES2/GTK host or frame-rate acceptance',
    'artifacts':{'baseline':'evidence/cpu-audit.json','candidate':'evidence/candidate-cpu-audit.json',
                 'gpu':'evidence/gpu-render-r2-result.json','mask_analysis':'agent_audit/mask_failure_analysis.json',
                 'images':image_hashes,'binary_hashes':final['binary_hashes']}}
correction=ROOT/'nose_fix/verification.json'
if correction.exists():
    report['nose_color_correction']={k:v for k,v in json.loads(correction.read_text(encoding='utf-8')).items() if k!='frames'}
(ROOT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'captures_checked':len(images),'source_inputs_unchanged':True,'ui_unchanged':True},ensure_ascii=False))
