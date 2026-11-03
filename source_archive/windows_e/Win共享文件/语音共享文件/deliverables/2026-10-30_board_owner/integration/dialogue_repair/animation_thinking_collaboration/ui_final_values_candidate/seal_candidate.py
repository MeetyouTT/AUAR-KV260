"""Seal locally tested sources; never changes the running application."""
import ast
import contextlib
import copy
import difflib
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

import replay_common as replay
import test_final_values as tests

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def functions(path):
    result={}
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node,ast.FunctionDef):result[node.name]=node
        elif isinstance(node,ast.ClassDef):
            for child in node.body:
                if isinstance(child,ast.FunctionDef):result[node.name+'.'+child.name]=child
    return result


class RemoveDiagnosticAssignment(ast.NodeTransformer):
    def visit_Assign(self,node):
        if (len(node.targets)==1 and ast.unparse(node.targets[0])=="state['ui_widget_writes']"
                and ast.unparse(node.value)=='dict(self._ui_widget_writes)'):
            return None
        return node


def main():
    baseline=json.loads((HERE/'BASELINE.json').read_text(encoding='utf-8'))
    mapping=json.loads((HERE.parent.parent/'release_v18_newboot_candidate/newboot_evidence/source_mapping.json').read_text(encoding='utf-8'))
    pins={};patch=[]
    for relative,expected in baseline['before_pins'].items():
        before,after=HERE/'before/aura'/relative,HERE/'candidate/aura'/relative
        if sha(before)!=expected or mapping['component_pins'][relative]!=expected:raise ValueError(relative)
        pins[relative]=sha(after)
        patch.extend(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(keepends=True),
            after.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative))
    before=functions(HERE/'before/aura/tools/board_avatar_gtk.py')
    after=functions(HERE/'candidate/aura/tools/board_avatar_gtk.py')
    changed=[name for name in before if ast.dump(before[name])!=ast.dump(after[name])]
    if set(changed)!={'BoardAvatarStage.refresh_runtime','BoardAvatarStage.tick'} or set(after)!=set(before):
        raise ValueError('Unexpected GTK method change')
    normalized=RemoveDiagnosticAssignment().visit(copy.deepcopy(after['BoardAvatarStage.tick']))
    if ast.dump(normalized)!=ast.dump(before['BoardAvatarStage.tick']):raise ValueError('Tick control changed')
    before_business=functions(HERE/'before/aura/tools/production_business_ui.py')
    after_business=functions(HERE/'candidate/aura/tools/production_business_ui.py')
    if ([name for name in before_business if ast.dump(before_business[name])!=ast.dump(after_business[name])]
            !=['project_business_ui'] or set(after_business)-set(before_business)!={'_write_widget'}):
        raise ValueError('Unexpected business/security function change')
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    (HERE/'TEST_LOG.txt').write_text(stream.getvalue(),encoding='utf-8')
    loaded={};mismatches=[]
    for name,value in tuple(sys.modules.items()):
        file=getattr(value,'__file__',None)
        if not file:continue
        path=Path(file)
        try:relative=path.resolve().relative_to(replay.FIXTURE.RUNTIME.resolve()).as_posix()
        except ValueError:continue
        if path.suffix!='.py':continue
        loaded[relative]=sha(path)
        if loaded[relative]!=mapping['component_pins'].get(relative):mismatches.append(relative)
    old,new=replay.make_stage(tests.OLD),replay.make_stage(tests.NEW)
    replay.refresh(old,replay.state(),tests.OLD_BUSINESS);replay.refresh(new,replay.state(),tests.NEW_BUSINESS)
    old_trace,new_trace=replay.trace_applied(old,tests.OLD),replay.trace_applied(new,tests.NEW)
    old_count,new_count=old.writes(),new.writes()
    replay.refresh(old,replay.state(),tests.OLD_BUSINESS);replay.refresh(new,replay.state(),tests.NEW_BUSINESS)
    counts=dict(baseline_guarded_applied=sum(old_trace.values()),candidate_guarded_applied=sum(new_trace.values()),
        baseline_all_widget_mutations=old.writes()-old_count,candidate_all_widget_mutations=new.writes()-new_count,
        scope='One stable repeated production refresh, synthetic widgets, real GTK/business functions; not FPS')
    report=dict(schema='aura.ui-final-values-tests.v1',successful=result.wasSuccessful() and not mismatches,
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
        final_state_combinations=72,identity_condition_combinations=8,product_pins=pins,
        loaded_dependency_pins=loaded,loaded_dependency_mismatches=mismatches,mutation_replay=counts,
        tick_control_ast_unchanged=True,security_capture_classifier_ast_unchanged=True,
        frozen_fixture_sha256=sha(HERE.parent/'ui_responsiveness_v18/test_ui_responsiveness.py'),
        device_access=False,gtk_or_egl_opened=False,private_data_or_models_opened=False,
        physical_fps_or_control_latency_passed=False)
    (HERE/'TEST_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if not report['successful']:raise ValueError('Validation failed')
    (HERE/'changes.patch').write_text(''.join(patch),encoding='utf-8')
    handoff=dict(schema='aura.ui-final-values-handoff.v1',status='LOCAL8_TESTS_PASS_READY_FOR_ROOT_REVIEW_NOT_DEPLOYED',
        base_startup_sha256=baseline['startup_sha256'],boot_id=baseline['boot_id'],before_pins=baseline['before_pins'],
        candidate_pins=pins,product_sources=2,target_fps=16,
        preserved=['currently visible UI','latest listening preference','native/pair/X11 cache','command timing',
                   'audio/ACK/8-frame queues/ASR','new-boot recovery/H01/speakerclose/memoryr2'],
        threads_timers_or_device_actions_added=False,production_modified=False,tests_run=result.testsRun,
        final_state_combinations=72,identity_condition_combinations=8,loaded_dependency_pins=len(loaded),
        mutation_replay=counts,actual_fps_improvement_proven=False,
        paired_cpu_wall_analysis='SAVED_EVIDENCE_ANALYSIS.json',
        counter_scope_change='ui_widget_writes now includes guarded production_business_ui work',
        collector_unchanged=True,root_must_recheck_current_source_pins=True,
        root_next_steps=['Keep current UI running until a root-owned integration window',
            'Merge the two reviewed source increments together and update current startup component pins',
            'Sample same-load native completions and full UI wall/thread CPU without extra pressure',
            'Verify pause/cancel/error/toast and actual capture/ACK; keep queue capacity and thread priorities unchanged',
            'If repeated writes disappear but FPS remains low, use root thread/CPU/capture evidence to find waits'])
    (HERE/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n',encoding='utf-8')
    names=('BASELINE.json','HANDOFF.json','TEST_RESULTS.json','TEST_LOG.txt','changes.patch','REVIEW.txt',
        'BASELINE_SETTER_REPLAY.json','SAVED_EVIDENCE_ANALYSIS.json','test_final_values.py','replay_common.py')
    manifest=dict(product_pins=pins,auxiliary_pins={name:sha(HERE/name) for name in names})
    (HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive=HERE/'ui_final_values_overlay.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as output:
        for relative in pins:output.write(HERE/'candidate/aura'/relative,'aura/'+relative)
        for name in (*names,'SOURCE_MANIFEST.json'):output.write(HERE/name,name)
    print(json.dumps(dict(status=handoff['status'],archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
        handoff_sha256=sha(HERE/'HANDOFF.json'),product_pins=pins,tests_run=result.testsRun,
        loaded_dependency_pins=len(loaded),mutation_replay=counts)))


if __name__=='__main__':main()
