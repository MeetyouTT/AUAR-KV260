"""Freeze local FPS findings, tested overlays and owner-only device plan."""
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    baseline=json.loads((HERE/'BASELINE.json').read_text(encoding='utf-8'))
    variants={}
    for fps in (16,24):
        root=HERE/('paired_'+str(fps));receipt=json.loads((root/'PAIRING_RECEIPT.json').read_text(encoding='utf-8'))
        tests=json.loads((root/'TEST_RESULTS.json').read_text(encoding='utf-8'))
        if not tests['successful'] or tests['tests_run']!=33 or tests['loaded_dependency_pin_mismatches']:
            raise ValueError('Matching rate and eye behavior tests required')
        patches=[];rows={}
        for relative,expected in receipt['files'].items():
            before=HERE/'before/aura'/relative;after=root/'aura'/relative
            if sha(before)!=baseline['files'][relative] or sha(after)!=expected:raise ValueError('Source changed after tests')
            rows[relative]=dict(before_sha256=sha(before),after_sha256=expected)
            patches.extend(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(keepends=True),
                after.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative))
        (root/'changes.patch').write_text(''.join(patches),encoding='utf-8')
        save(root/'SOURCE_MANIFEST.json',dict(schema='aura.native-rate-source-manifest.v1',
            fps=fps,files=rows,native_library_unchanged=baseline['native_library_sha256'],
            gui_config_changes=receipt['gui_config_changes'],production_modified=False))
        archive=HERE/('startup_rate_'+str(fps)+'_overlay.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
            for path in sorted((root/'aura').rglob('*')):
                if path.is_file():output.write(path,path.relative_to(root).as_posix())
            for name in ('PAIRING_RECEIPT.json','SOURCE_MANIFEST.json','TEST_RESULTS.json','changes.patch'):
                output.write(root/name,name)
        variants[str(fps)]=dict(archive=archive.name,sha256=sha(archive),bytes=archive.stat().st_size,
            source_manifest_sha256=sha(root/'SOURCE_MANIFEST.json'),
            selection_sha256=receipt['selection_sha256'],local_tests=33,
            loaded_dependency_pins=len(tests['loaded_display_dependency_pins']))
    live=json.loads((HERE/'LIVE_FPS_ANALYSIS.json').read_text(encoding='utf-8'))
    packages=json.loads((HERE/'performance/PACKAGES.json').read_text(encoding='utf-8'))
    probe=json.loads((HERE/'ui_timing_probe/HANDOFF.json').read_text(encoding='utf-8'))
    result=dict(schema='aura.native-rate-handoff.v1',status='LIVE_DROP_CONFIRMED_UI_PROBE_AND16_24_CANDIDATES_LOCAL_TESTED',
        base_startup_sha256=baseline['startup_sha256'],native_library_unchanged=baseline['native_library_sha256'],
        live_completed_frames=live['completed_frames'],live_elapsed_seconds=live['elapsed_seconds'],
        live_window_completion_rate=live['weighted_completion_rate'],live_rate_is_physical_fps=False,
        ui_probe_archive=dict(path='ui_timing_probe/ui_timing_probe.zip',sha256=sha(HERE/'ui_timing_probe/ui_timing_probe.zip')),
        ui_probe_source=probe['files'],variants=variants,performance_packages=packages['bundles'],
        live_analysis_sha256=sha(HERE/'LIVE_FPS_ANALYSIS.json'),review_sha256=sha(HERE/'REVIEW.txt'),
        priority_order=['Diagnose/fix long business UI stages at16 with narrow numeric probe',
            'Then isolate16/24 same-load native preview without PNG measurement I/O',
            'Then full-business short checks preserving audio/ACK/8-frame queue and ASR behavior'],
        native_priority_raised=False,audio_poll_or_ack_schedule_modified=False,
        motion_candidate_unchanged=True,feature_routes_unchanged=True,production_modified=False,
        device_actions=False,actual_fps_improvement_proven=False,physical24fps_acceptance_passed=False,
        latest_user_listening_preference_must_be_preserved=True)
    save(HERE/'HANDOFF.json',result)
    print(json.dumps(dict(status=result['status'],handoff_sha256=sha(HERE/'HANDOFF.json'),variants=variants)))


if __name__=='__main__':main()
