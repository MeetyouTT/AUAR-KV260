"""Package only reviewed code and scalar evidence; never copy ELF/UART/identity data."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'delivery'
FILES=[
 'README.md','OPERATIONS.md','build_delivery.py','schedprobe.c','native_thread_probe.py','bench_schedprobe.py',
 'build_check.py','board_check.py','external_monitor.py','build_external.py','external_check.py',
 'recover_availability.py','trace_isolated.py','trace_vart.py',
 'preflight.json','board-result.json','check-manifest.json','external-result.json','external-manifest.json',
 'event-5788-raw.json','event-521-analysis.json','event-610-raw.json','recovery-result.json','recovery-launch.json',
 'CURRENT_STATE.json','final-audit.json','before-sface-second-fault-audit.json','cleanup-audit.json','trace-isolated-result.json','vart-phase-result.json',
 'exact-runtime/download-proof.json',
 'independent-review/ABI_AND_PROBE_REVIEW.md','independent-review/C_AND_ADAPTER_REVIEW.md',
 'independent-review/EVENT_5788_REVIEW.md','independent-review/EXTERNAL_PLAN_REVIEW.md',
 'independent-review/RECOVERY_CONTROL_REVIEW.md','independent-review/EXACT_ELF_REVIEW.md',
 'independent-review/UPROBE_ISOLATED_REVIEW.md','independent-review/VART_PHASE_CONTROLLER_REVIEW.md',
 'independent-review/review-provenance.json','independent-review/external-review-provenance.json',
 'independent-review/recovery-reviewed-manifest.json','independent-review/event-5788-recalculated.json',
 'independent-review/exact-elf-evidence.json','independent-review/exact-elf-review-manifest.json',
 'independent-review/verify_exact_elf.py','independent-review/test_schedprobe_review.py',
 'independent-review/test_adapter_review.py','independent-review/host-tests.log',
 'independent-review/adapter-tests-initial.log','independent-review/adapter-tests-final.log',
 'independent-review/test_uprobe_isolated_review.py','independent-review/uprobe-isolated-local-tests.log',
 'independent-review/uprobe-isolated-reviewed-manifest.json',
 'independent-review/test_vart_phase_review.py','independent-review/vart-phase-local-tests.log',
 'independent-review/vart-phase-reviewed-manifest.json',
 'independent-review/check_append_behavior.py','independent-review/append-behavior-result.txt',
 'failures/uprobe_isolated_r1/trace_isolated.py','failures/uprobe_isolated_r1/stage-result.json',
 'failures/uprobe_isolated_r2/trace_isolated.py','failures/uprobe_isolated_r2/stage-result.json',
 'failures/vart_phase_preflight_r1/trace_vart.py','failures/vart_phase_preflight_r1/stage-result.json',
]
EXTRA={
 'native_trace_capability.response.json':'/home/ghmd/aura-model-inventory-20261021/native_trace_capability.response.json',
 'native_trace_capability.status.json':'/home/ghmd/aura-model-inventory-20261021/native_trace_capability.status.json',
 'native_final_audit.py':'/home/ghmd/aura-model-inventory-20261021/native_final_audit.py',
 'native_final_audit.status.json':'/home/ghmd/aura-model-inventory-20261021/native_final_audit.status.json',
}

def main():
    OUT.mkdir(exist_ok=True)
    sources={name:ROOT/name for name in FILES}
    sources.update({name:Path(path) for name,path in EXTRA.items()})
    for name,source in sources.items():
        assert source.is_file(),source
        assert source.suffix not in ('.so','.zip','.gz','.sqlite3','.raw') and '.private.' not in source.name
        raw=source.read_bytes();raw.decode('utf8')
        if source.suffix=='.py':ast.parse(raw,filename=str(source))
        if source.suffix=='.json':json.loads(raw)
        target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    checks=[]
    for path in sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS'):
        checks.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(OUT)))
    (OUT/'SHA256SUMS').write_text('\n'.join(checks)+'\n')
    print(json.dumps({'files_hashed':len(checks),'output':str(OUT),'proprietary_elf_included':False}))

if __name__=='__main__':main()
