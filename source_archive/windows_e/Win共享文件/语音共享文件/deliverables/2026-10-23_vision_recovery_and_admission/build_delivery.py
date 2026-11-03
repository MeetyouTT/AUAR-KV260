"""Export reviewed code/scalar evidence only; no weights/ELF/UART/private stores."""
import ast,difflib,hashlib,json,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SF=Path('/home/ghmd/aura-sface-recovery-20261023')
FLOOR=Path('/home/ghmd/aura-admission-floor-20261023')
OUT=ROOT/'delivery'
FILES={name:ROOT/name for name in (
    'README.md','OPERATIONS.md','VALIDATION.md','CURRENT_STATE.json','final-audit.json',
    'promotion-result.json','resource-result.json','phase-result.json','phase-summary.json',
    'deployment-manifest.json','isolated-manifest.json','baseline-manifest.json',
    'deploy_control.py','protected_rollback_entry.py','build_deployment.py','board_promote.py',
    'build_isolated.py','board_isolated.py','run_tests.py','control.py','handoff.py','live_checks.py',
    'build_delivery.py','resource_snapshot.py','trace_optional_phases_vision.py',
    'fresh-boot-tests.log','handoff-compatibility-tests.log','sface-compatibility-tests.log',
    'controller-tests.log','resource-gate-tests.log','combined-regressions.log','combined-regressions-final.log',
    'captured-fault-analysis.json','actual-yunet-recovery.json','trace_wait_sched.py','probe8_isolated.py',
    'probe8-isolated-result.json','wait-sched-parser-tests.log','scheduler-limits.json',
    'analyze_wait_sched.py','download_wait_report.py','wait-sched-result.json','wait-sched-analysis.json',
    'trace_wait_sched_offload.py','trace_wait_sched_nice.py','download_offload_trace.py',
    'offload-baseline-report.json','offload-baseline-result.json','offload-baseline-analysis.json',
    'nice-trial-report.json','nice-trial-result.json','nice-trial-analysis.json','nice-restore-tests.log',
    'second-fault-summary.json','final-cleanup.json','current-final.json','previous-final-audit.json')}
FILES.update({
 'phase-main-180.json':SF/'phase-result.json','phase-main-600.json':SF/'phase-600-result.json',
 'phase-vision-180.json':SF/'phase-vision-result.json',
 'trace_optional_phases.py':SF/'trace_optional_phases.py',
 'trace_optional_phases_180.py':SF/'trace_optional_phases_180.py',
 'RUNNER_FINDINGS.md':SF/'RUNNER_FINDINGS.md','runner-symbols.json':SF/'runner-symbols.json',
 'runner-recovery-proof.json':SF/'runner-recovery-proof.json',
 'upstream-reference/provenance.json':SF/'upstream-reference/provenance.json',
 'history/sface-promotion.json':SF/'promotion-result.json',
 'history/admission-promotion.json':FLOOR/'promotion-result.json',
 'history/admission-resource.json':FLOOR/'resource-result.json',
 'history/independent-core-review.md':SF/'independent-review/CORE_INJECTION_REVIEW.md',
 'history/independent-core-manifest.json':SF/'independent-review/core-reviewed-manifest.json',
 'history/independent-core-injection-r1.log':SF/'independent-review/core-injection-r1.log',
 'history/independent-core-injection-r2.log':SF/'independent-review/core-injection-r2.log',
 'history/entry-review.md':SF/'independent-review/ENTRY_AND_HANDOFF_REVIEW.md',
 'history/resource-refused.json':ROOT/'failures/resource_nonzero_counter/result.json',
 'history/resource-refused-source.py':ROOT/'failures/resource_nonzero_counter/resource_snapshot.py',
 'history/newboot-read.json':SF/'newboot-read.json',
 'history/oldboot-preflight.json':SF/'preflight.json',
 'history/oldboot-transfer-refused.json':Path('/home/ghmd/aura-dpu-vision-20261021/uart/20261023T220659.053705Z/status.json'),
 'isolated-171.json':SF/'board-isolated-r1-result.json',
 'isolated-26.json':SF/'board-final-isolated-result.json',
 'isolated-61.json':Path('/home/ghmd/aura-post-power-20261022/transfer-admission_floor_isolated/result.json'),
 'isolated-68.json':Path('/home/ghmd/aura-post-power-20261022/transfer-vision_persistent_isolated/result.json'),
 'software-recovery-198.log':SF/'software-regressions-newboot.log',
 'phase-parser-tests.log':SF/'phase-parser-tests.log',
 'vision-cleanup-tests.log':SF/'vision-cleanup-tests.log',
 'admission-floor-tests.log':FLOOR/'floor-tests.log',
 'final_audit.py':Path('/home/ghmd/aura-model-inventory-20261021/vision_persistent_audit.py')})

def main():
    OUT.mkdir(exist_ok=True)
    selected=dict(FILES)
    for folder in ('candidate/aura','baseline/aura','tests','admission_candidate'):
        for source in (ROOT/folder).rglob('*.py'):
            if '__pycache__' not in source.parts:selected[str(source.relative_to(ROOT))]=source
    for name,source in selected.items():
        assert source.is_file(),source
        assert '.private.' not in source.name
        raw=source.read_bytes();raw.decode('utf8')
        if source.suffix=='.py':ast.parse(raw,filename=str(source))
        if source.suffix=='.json':json.loads(raw)
        target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    patch=[]
    original=SF/'baseline/aura'
    for name in sorted(json.loads((ROOT/'deployment-manifest.json').read_text())['candidate_pins']):
        a=original/name;b=ROOT/'candidate/aura'/name
        before=a.read_text().splitlines(True) if a.exists() else []
        patch.extend(difflib.unified_diff(before,b.read_text().splitlines(True),fromfile='original/'+name,tofile='candidate/'+name))
        if a.exists():
            target=OUT/'original_reference'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(a.read_bytes())
    (OUT/'runtime-changes.patch').write_text(''.join(patch))
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in ('SHA256SUMS','delivery-verification.json'))
    assert all(p.suffix not in ('.so','.sqlite3','.raw','.png','.jpg','.wav','.gz','.xmodel','.onnx') for p in files)
    proof={'verified_files':len(files),'python_files':sum(p.suffix=='.py' for p in files),
        'json_files':sum(p.suffix=='.json' for p in files),'no_model_binary_uart_or_biometric_file':True,
        'windows_received_confirmed':False}
    (OUT/'delivery-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
    files.append(OUT/'delivery-verification.json')
    (OUT/'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT)) for p in sorted(files))+'\n')
    print(json.dumps(proof))

if __name__=='__main__':main()
