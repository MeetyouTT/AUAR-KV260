"""Freeze an explicit small source/evidence allowlist; no assets, models or secrets."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
AURA = PROJECT / 'aura'


def main():
    candidate = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
    tested = json.loads((HERE / 'board_focused.json').read_text(encoding='utf-8'))['source_text_sha256']
    sources = [*candidate['changes'], 'tests/framework/test_portrait_offload.py']
    packaged = []
    for relative in sources:
        source = HERE / 'candidate_source' / relative if relative == 'tools/board_avatar_gtk.py' else AURA / relative
        if relative == 'tools/board_avatar_gtk.py':
            layout = json.loads((HERE / 'layout_deployment.json').read_text(encoding='utf-8'))
            assert layout['status'] == 'COMMITTED'
            assert json.loads((HERE / 'full_gtk_layout.json').read_text(encoding='utf-8'))['passed']
            assert hashlib.sha256(source.read_text(encoding='utf-8').encode()).hexdigest() == candidate['gui_text_sha256'] == layout['gui_text_sha256']
        else:
            assert hashlib.sha256(source.read_text(encoding='utf-8').encode()).hexdigest() == tested[relative], relative
        target = HERE / 'source/aura' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        packaged.append(target)
    for relative in ('start_voice.ps1', 'start_portrait.ps1'):
        target = HERE / 'source' / relative
        shutil.copyfile(PROJECT / relative, target)
        packaged.append(target)
    names = '''README.md CONTINUE.md PROGRESS.json automation_receipt.json
        candidate.json snapshot_verification.json context_refresh.json
        board_tests.json board_focused.json windows_tests_verified.json tests.xml
        full_gtk_smoke.json live_headless.json outage_probe.json host_recovery.json
        original_audio_recovery.json deployment_failed_expiry.json follow_wait_state.json windows_health_final.json
        host_config.json host_entry.py host_health.py start_host.ps1 stop_host.ps1 recover_host.py
        prepare_candidate.py refresh_context.py sync_candidate.py verify_board.py run_tests.py smoke_ui.py
        live_headless.py deploy_ui.py step_fps.py capture_board.py outage_probe.py live_ui_outage_remote.py
        check_wait.py windows_health.py package_release.py
        deployment.json fps_steps.json fps_persisted.json muted_speech_probe.json live_ui_outage.json
        follow_pause.json layout_preparation.json full_gtk_layout.json layout_deployment.json rollback_check.json
        deploy_layout.py prepare_layout.py smoke_layout.py persist_fps.py muted_speech_probe.py rollback_ui.py
        capture_settings.py verify_final.py finish_docs.py final_verification.json native_screen.png native_avatar.jpg native_settings.png
        layout_deployment.log layout_deployment_retry.log'''.split()
    for name in names:
        path = HERE / name
        assert path.is_file(), name
        packaged.append(path)
    packaged.extend(path for path in (HERE / 'renderer_snapshot').rglob('*') if path.is_file())
    manifest = {'scope': 'Windows CPU rendering deployed at 16fps; native sink, muted PCM and actual UI fallback evidence; human acceptance pending',
                'validation': 'Core SHA matches ARM focused tests; GUI layout SHA separately verified by hidden GTK bounds and guarded native 16fps trial', 'files': {}}
    for path in sorted(packaged):
        relative = path.relative_to(HERE).as_posix()
        assert path.stat().st_size < 2_000_000, relative
        manifest['files'][relative] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest_path = HERE / 'SOURCE_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    archive = HERE / 'source_and_evidence.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in packaged:
            bundle.write(path, path.relative_to(HERE).as_posix())
        bundle.write(manifest_path, manifest_path.name)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len(bundle.namelist()) == len(packaged) + 1
    print(json.dumps({'files': len(packaged), 'zip_bytes': archive.stat().st_size,
                      'zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
