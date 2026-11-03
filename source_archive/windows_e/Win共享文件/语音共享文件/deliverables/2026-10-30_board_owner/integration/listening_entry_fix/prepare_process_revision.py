"""Assemble the frozen source-only process/listening revision for root review."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
BASE=HERE.parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def main():
    sources={}
    manifest=json.loads((BASE/'production_frontend_process_candidate/overlay_manifest.json').read_text(encoding='utf-8'))
    expected={
        'aura/board/runtime/audio/board_frontend_process.py':'8b5db6681e7ae1dd7040ab9aa2247ba59efb515286feebed5956034a6993dd63',
        'aura/tools/production_board_business_gui.py':'911ee09873a84d4c4c176e3798749a1813bee4d42dd05c6fc0ed108c6c7cfe2a',
        'aura/tools/production_frontend_selection.py':'bfef18d9ccd06e39357f5f375e6dc4c1d5d187bed51787e78206018658bb1a1b',
    }
    for rel,item in manifest['files'].items():
        assert item['sha256']==expected[rel]
        path=BASE/'production_frontend_process_candidate/after'/rel
        raw=path.read_bytes();assert sha(raw)==item['sha256'];ast.parse(raw,feature_version=(3,9))
        sources[rel.removeprefix('aura/')]=dict(source=path.relative_to(PROJECT).as_posix(),sha256=item['sha256'],before_sha256=item['before_sha256'])
    listening=BASE/'listening_cancel_rearm/after/aura/tools/production_listening.py'
    pin='b11e4a1fab51f91fc6e8b59901bbedc13c9fc5616411a191e6e801a14df26d47'
    assert sha(listening.read_bytes())==pin
    sources['tools/production_listening.py']=dict(source=listening.relative_to(PROJECT).as_posix(),sha256=pin,before_sha256='d5f9dd7bbb978962a49be633325c6d66580da323f17384f1ca423bc76475e3fe')
    diagnostics=BASE/'safe_capture_diagnostics/after/aura/tools/production_business_ui.py'
    assert sha(diagnostics.read_bytes())=='06d5cdc920e69acf0314c3c17d03fd1d84a9b6e44b39756b287a89582196dd8d'
    text=diagnostics.read_text(encoding='utf-8')
    before="_FRONTEND_NUMBERS = ('frames', 'processed_samples', 'last_roundtrip_ms', 'max_roundtrip_ms')"
    after="""_FRONTEND_NUMBERS = ('frames', 'processed_samples', 'last_roundtrip_ms', 'max_roundtrip_ms',
    'worker_pid', 'worker_generation', 'ipc_rpc_last_ms', 'ipc_rpc_max_ms', 'ipc_rpc_total_ms',
    'worker_frame_wall_last_ms', 'worker_frame_wall_max_ms', 'worker_frame_wall_total_ms',
    'worker_frame_cpu_last_ms', 'worker_frame_cpu_max_ms', 'worker_frame_cpu_total_ms')"""
    assert text.count(before)==1;text=text.replace(before,after)
    before="'VISUAL_SPEECH_NOT_BOUND', 'TARGET_CHANGED', 'NO_VALID_INITIAL_SPEECH'))"
    assert text.count(before)==1;text=text.replace(before,"'VISUAL_SPEECH_NOT_BOUND', 'TARGET_CHANGED', 'NO_VALID_INITIAL_SPEECH', 'CURRENT_TURN_CANCELLED'))")
    before="('enabled', 'closed', 'capture_lease_closed')))"
    assert text.count(before)==1;text=text.replace(before,"('enabled', 'closed', 'capture_lease_closed', 'worker_process_alive')))")
    raw=text.encode();ast.parse(raw,feature_version=(3,9))
    output=HERE/'after/aura/tools/production_business_ui.py';output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw)
    module={};exec(compile(raw,str(output),'exec'),module)
    assert module['_numbers']({'worker_pid':123,'ipc_rpc_last_ms':float('nan'),'worker_frame_cpu_total_ms':'private','unknown':'private'},module['_FRONTEND_NUMBERS'])=={'worker_pid':123}
    assert module['_flags']({'worker_process_alive':True},('worker_process_alive',))=={'worker_process_alive':True}
    assert 'CURRENT_TURN_CANCELLED' in module['_REASONS']
    sources['tools/production_business_ui.py']=dict(source=output.relative_to(PROJECT).as_posix(),sha256=sha(raw),before_sha256='c7a1c7b6e6259c1fb74be831d7272704fb20119c86345b50b79234d5f3adf973')
    revision=dict(stage='automatic-listening-v2-process',before_startup_sha256='509a7caa1fa4b8eade458462a95784d411620078dc08888eaca4a31e81a91470',
        before_manifest_sha256='955ec9c5bef3b7f96b2be1c0854c8da474623fe276561738d4446dc2dd58d5bb',
        business_options=dict(frontend_process=True,frontend_optimization='baseline',capture_priority_nice=-10,frontend_threads=1),sources=sources,
        queue_frames=8,model_or_threshold_changes=False,worker_gate_only=True,source_only=True)
    (HERE/'process_revision.json').write_text(json.dumps(revision,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='SOURCE_REVISION_PREPARED',files={r:x['sha256'] for r,x in sources.items()},diagnostic_projection_checks=3)))

if __name__=='__main__':main()
