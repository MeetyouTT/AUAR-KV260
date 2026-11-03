"""Validate and package local UI sources; no device or production operation."""
import ast
import contextlib
import difflib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile


HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent.parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def methods(path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    result={}
    for node in tree.body:
        if isinstance(node,ast.FunctionDef):result[node.name]=ast.dump(node)
        elif isinstance(node,ast.ClassDef):
            for method in node.body:
                if isinstance(method,ast.FunctionDef):result[node.name+'.'+method.name]=ast.dump(method)
    return result


def main():
    baseline=json.loads((HERE/'BASELINE.json').read_text(encoding='utf-8'))
    mapping=json.loads((REPAIR/'release_v18_candidate/v18_evidence/source_mapping.json').read_text(encoding='utf-8'))
    files={}
    for relative,expected in baseline['before_pins'].items():
        if sha(HERE/'before/aura'/relative)!=expected or mapping['component_pins'][relative]!=expected:
            raise ValueError('Reviewed baseline changed: '+relative)
        files[relative]=sha(HERE/'candidate/aura'/relative)
    old=methods(HERE/'before/aura/tools/board_avatar_gtk.py')
    new=methods(HERE/'candidate/aura/tools/board_avatar_gtk.py')
    changed=[name for name in old if old[name]!=new.get(name)]
    expected=['BoardAvatarStage.refresh_runtime','BoardAvatarStage.refresh_settings','BoardAvatarStage.tick']
    if sorted(changed)!=sorted(expected) or set(new)-set(old)!={'BoardAvatarStage._ui_set'}:
        raise ValueError('Unexpected GTK behavior changed')
    old_display=methods(HERE/'before/aura/tools/x11_display_activity.py')
    new_display=methods(HERE/'candidate/aura/tools/x11_display_activity.py')
    if old_display['DisplayActivity.tick']!=new_display['DisplayActivity.tick']:
        raise ValueError('Wake cadence changed')
    module=load('ui_responsiveness_validation',HERE/'test_ui_responsiveness.py')
    collector=load('ui_collector_validation',HERE/'test_collector_whitelist.py')
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(module),
                              unittest.defaultTestLoader.loadTestsFromModule(collector)])
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (HERE/'TEST_LOG.txt').write_text(stream.getvalue(),encoding='utf-8')
    loaded={};mismatches=[]
    for name,value in tuple(sys.modules.items()):
        location=getattr(value,'__file__',None)
        if not location:continue
        path=Path(location)
        try:relative=path.resolve().relative_to(module.RUNTIME.resolve()).as_posix()
        except ValueError:continue
        if path.suffix!='.py':continue
        digest=sha(path);loaded[relative]=digest
        if mapping['component_pins'].get(relative)!=digest:mismatches.append(relative)
    old_stage,new_stage=module.FakeStage(module.BEFORE),module.FakeStage(module.AFTER)
    module.render(old_stage,module.state_for());module.render(new_stage,module.state_for())
    before_old,before_new=old_stage.writes(),new_stage.writes()
    for _ in range(10):
        module.render(old_stage,module.state_for());module.render(new_stage,module.state_for())
    counts=dict(stable_refreshes=10,baseline_mutations=old_stage.writes()-before_old,
        candidate_mutations=new_stage.writes()-before_new,
        scope='Real refresh_settings/refresh_runtime methods with synthetic widgets; not full GTK or business UI FPS')
    tests=dict(schema='aura.ui-responsiveness-tests.v1',successful=result.wasSuccessful() and not mismatches,
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
        product_files=files,loaded_runtime_dependency_pins=loaded,loaded_dependency_mismatches=mismatches,
        six_control_states_match_v18=True,same_refresh_pause_cancel_error_checks=True,
        complete_callback_includes_synthetic_publish_wait=True,widget_mutations=counts,
        gtk_or_egl_opened=False,audio_camera_or_models_opened=False,device_access=False,
        real_fps_or_control_latency_passed=False)
    (HERE/'TEST_RESULTS.json').write_text(json.dumps(tests,indent=2)+'\n',encoding='utf-8')
    if not tests['successful']:raise ValueError('Validation failed; see TEST_RESULTS/TEST_LOG')
    patch=[]
    for relative in files:
        before=(HERE/'before/aura'/relative).read_text(encoding='utf-8').splitlines(keepends=True)
        after=(HERE/'candidate/aura'/relative).read_text(encoding='utf-8').splitlines(keepends=True)
        patch.extend(difflib.unified_diff(before,after,fromfile='a/'+relative,tofile='b/'+relative))
    (HERE/'changes.patch').write_text(''.join(patch),encoding='utf-8')
    handoff=dict(schema='aura.ui-responsiveness-handoff.v1',status='LOCAL16_TESTS_PASS_DEVICE_VALIDATION_PENDING',
        base_startup_sha256=baseline['startup_sha256'],base_manifest_sha256=baseline['source_manifest_sha256'],
        before_pins=baseline['before_pins'],candidate_pins=files,
        changed_gtk_methods=changed,new_gtk_method='BoardAvatarStage._ui_set',guarded_setter_calls=54,
        target_fps=16,native_pair_unchanged=True,audio_ack_and_command_cadence_unchanged=True,
        background_threads_or_timers_added=False,product_sources=2,
        synthetic_tests=16,loaded_dependency_pins=len(loaded),loaded_dependency_mismatches=mismatches,
        widget_mutations=counts,tests_sha256=sha(HERE/'TEST_RESULTS.json'),patch_sha256=sha(HERE/'changes.patch'),
        collector_sha256=sha(HERE/'collect_ui_stage_metadata.py'),
        complete_callback_field='ui_callback_previous: previous completed full refresh, including publish; sequence and completed_mono identify it',
        source_sample_sha256='b23fcc4915e0ff52071a02c5d39b4f90fd797d2b138fdcaaca1309faaeb1dde8',
        observed_sample_window='Saved before coordinator observed a later board reboot; not a current-boot observation',
        source_sample_boot_id=mapping.get('boot_id'),
        root_must_recheck_current_entry=True,preserve_latest_listener_preference=True,
        production_modified=False,device_access=False,actual_fps_improvement_proven=False,
        review='REVIEW.txt',root_steps=['Recheck current source pins and new boot/entry; preserve H01/speakerclose/memoryr2',
            'Merge only these two source increments; keep FPS16/native pair unchanged',
            'Use root-owned normal-close/update source startup pins/ready sequence',
            'Use new numeric collector; compare full-callback previous, per-stage wall/CPU, setters, completed frames and audio safety',
            'If remaining stalls are display sync/sysfs/hidden widgets, use measured substage to choose next narrow repair'])
    (HERE/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n',encoding='utf-8')
    manifest=dict(product_files=files,auxiliary_files={name:sha(HERE/name) for name in
        ('HANDOFF.json','BASELINE.json','TEST_RESULTS.json','TEST_LOG.txt','changes.patch','REVIEW.txt',
         'collect_ui_stage_metadata.py','test_collector_whitelist.py','test_ui_responsiveness.py')})
    (HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive=HERE/'ui_responsiveness_v18_overlay.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as output:
        for relative in files:output.write(HERE/'candidate/aura'/relative,'aura/'+relative)
        for name in (*manifest['auxiliary_files'],'SOURCE_MANIFEST.json'):output.write(HERE/name,name)
    print(json.dumps(dict(status=handoff['status'],archive=str(archive),archive_sha256=sha(archive),
        archive_bytes=archive.stat().st_size,handoff_sha256=sha(HERE/'HANDOFF.json'),
        product_files=files,tests=tests['tests_run'],loaded_dependency_pins=len(loaded),widget_mutations=counts)))


if __name__=='__main__':main()
