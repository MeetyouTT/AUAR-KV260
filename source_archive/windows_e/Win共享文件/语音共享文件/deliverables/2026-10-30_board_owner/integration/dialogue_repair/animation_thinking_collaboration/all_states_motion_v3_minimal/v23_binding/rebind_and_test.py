"""Bind the frozen motion proposal and facial tests to final v23, locally."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest

HERE=Path(__file__).resolve().parent
MOTION=HERE.parent
ANIM=MOTION.parent
REPAIR=ANIM.parent
STARTUP='d848dc90cf9a890fb8bc66b2c494b78c2ae39a7e22a4743fe0ab917ca3edbae8'
MANIFEST='8e4d3a90f20520c518f28fa12cbf9093f17405f4d9ed2bb9edf2ac46890d496a'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence=REPAIR/'release_v23_memory_summary_candidate/memory_summary_evidence'
    mapping=json.loads((evidence/'source_mapping.json').read_text(encoding='utf-8'))
    spec=json.loads((evidence/'spec.json').read_text(encoding='utf-8'))
    ready=json.loads((evidence/'ready.json').read_text(encoding='utf-8'))
    installed=json.loads((evidence/'installed.json').read_text(encoding='utf-8'))
    for value in (mapping,spec):
        if value['startup_sha256']!=STARTUP or value['source_manifest_sha256']!=MANIFEST:
            raise ValueError('Final v23 identity differs')
    if ready.get('status')!='PRODUCTION_BOARD_BUSINESS_READY' or mapping.get('status')!='SUMMARY_SOURCE_AND_SERVICE_VERIFIED':
        raise ValueError('Actual ready/source proof required')
    package=json.loads((MOTION/'PACKAGE_RECEIPT.json').read_text(encoding='utf-8'))
    if sha(MOTION/package['archive'])!=package['sha256']:raise ValueError('Frozen source package changed')
    native=json.loads((MOTION/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    for relative,row in native['files'].items():
        if sha(MOTION/'candidate'/relative)!=row['after_sha256']:raise ValueError('Native candidate changed')
    old=json.loads((MOTION/'BASELINE_V22.json').read_text(encoding='utf-8'))
    tested=json.loads((MOTION/'LOCAL_TEST_RESULTS.json').read_text(encoding='utf-8'))
    for name,expected in old['pair_pins'].items():
        if mapping['component_pins'].get(name)!=expected:raise ValueError('Pair source changed: '+name)
    runtime=HERE/'local_test_runtime';runtime.mkdir(exist_ok=False)
    for relative,expected in tested['loaded_dependency_pins'].items():
        if mapping['component_pins'].get(relative)!=expected:raise ValueError('v23 dependency changed: '+relative)
        source=MOTION/'local_test_runtime'/relative
        if sha(source)!=expected:raise ValueError('Local source differs: '+relative)
        target=runtime/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    target=runtime/'config/yuki_pair.formal.json';target.parent.mkdir(exist_ok=True)
    shutil.copyfile(MOTION/'before/aura/config/yuki_pair.formal.json',target)
    sys.path.insert(0,str(runtime));sys.dont_write_bytecode=True
    suite=unittest.defaultTestLoader.discover(str(ANIM/'tests'),pattern='test_thinking_animation.py')
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (HERE/'GATE_TEST_LOG.txt').write_text(log.getvalue(),encoding='utf-8')
    loaded={};mismatches=[]
    for name,module in tuple(sys.modules.items()):
        file=getattr(module,'__file__',None)
        if not file:continue
        path=Path(file)
        try:relative=path.resolve().relative_to(runtime.resolve()).as_posix()
        except ValueError:continue
        if path.suffix!='.py':continue
        loaded[relative]=sha(path)
        if loaded[relative]!=mapping['component_pins'].get(relative):mismatches.append(relative)
    previous=json.loads((REPAIR/'release_v22_camera_rebind_candidate/camera_rebind_evidence/source_mapping.json').read_text(encoding='utf-8'))
    changes={name:dict(before=previous['component_pins'].get(name),after=digest)
        for name,digest in mapping['component_pins'].items() if previous['component_pins'].get(name)!=digest}
    protected=set(changes)
    if protected & set(loaded):raise ValueError('Protected memory sources unexpectedly entered the facial fixture')
    report=dict(schema='aura.minimal-motion-v23-gate-validation.v1',successful=result.wasSuccessful() and not mismatches,
        final_v23_startup_sha256=STARTUP,final_v23_source_manifest_sha256=MANIFEST,
        evidence_sha256={name:sha(evidence/name) for name in ('spec.json','ready.json','installed.json','source_mapping.json')},
        evidence_statuses=dict(ready=ready['status'],source=mapping['status'],installed=installed.get('status')),
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
        loaded_dependency_pins=loaded,loaded_dependency_mismatches=mismatches,
        pair_pins=old['pair_pins'],protected_v23_changes_not_copied_or_modified=changes,
        frozen_source_package_sha256=package['sha256'],native_candidate_compiled_or_executed=False,
        native_library_unchanged=old['pair_pins']['tools/libaura_yuki.so'],
        device_access=False,model_or_build_service_started=False,microphone_or_audio_device_opened=False,
        production_modified=False,physical_fps_or_cpu_benefit_proven=False)
    (HERE/'V23_GATE_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(successful=report['successful'],tests=result.testsRun,dependencies=len(loaded),
        mismatches=mismatches,protected_v23_changed_files=list(changes),startup=STARTUP)))
    if not report['successful']:raise SystemExit(1)


if __name__=='__main__':main()
