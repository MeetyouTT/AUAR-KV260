"""Publish compiled engineering model and metrics, excluding reference tensors."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).parent
OUT = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-18_identity_dpu/engineering-bee245f2a94e4d28')
result = json.loads((ROOT/'compiled-engineering-result.json').read_text())
files = {
    'sface_engineering.xmodel': ROOT/'compiled-engineering/sface_engineering.xmodel',
    'compiled-result.json': ROOT/'compiled-engineering-result.json',
    'compiler-meta.json': ROOT/'compiled-engineering/meta.json',
    'quant_info.json': ROOT/'quantized-engineering/quant_info.json',
    'calibration-report.json': ROOT/'quantized-engineering/report-calib.json',
    'quantized-metrics.json': ROOT/'quantized-engineering/report-test.json',
    'integer-fixture-metrics.json': ROOT/'quantized-engineering/report-hardware-reference.json',
    'target_arch.json': Path('/home/ghmd/kv260-dpu41-control-20261001/test_bundle/provenance/hardware/arch.json'),
}
for name in ['reconstruct_sface.py', 'rewrite_sface_v2.py', 'quantize_sface.py', 'export_compile.py',
             'board_probe_dpu.py', 'run_uart.py', 'board_engineering_smoke.py', 'board_stage_smoke.py',
             'build_engineering_bundle.py', 'resume_transfer.py', 'verify_engineering_artifacts.py',
             'publish_engineering.py']:
    files['source/'+name] = ROOT/name
for name in ['quantize-calib.log', 'quantize-test.log', 'quantize-golden.log',
             'compile-engineering.log', 'export-compile.log', 'export-compile-retry.log']:
    files['logs/'+name] = ROOT/name
board_status = None
for phase in ['hardware-probe', 'hardware-probe-retry', 'transfer-state', 'board-smoke']:
    pointer = ROOT/('latest-'+phase+'.json')
    if not pointer.exists():
        continue
    status = json.loads(pointer.read_text())
    location = Path(status['evidence'])
    files['evidence/'+phase+'/status.json'] = location/'status.json'
    response = location/'response.json'
    if response.exists():
        files['evidence/'+phase+'/response.json'] = response
    if phase == 'board-smoke' and status['complete'] and response.exists():
        board_status = json.loads(response.read_text())
pointer = ROOT/'latest-resume-transfer.json'
if pointer.exists():
    files['evidence/resume-transfer-status.json'] = pointer
OUT.mkdir(parents=True, exist_ok=True)
entries = []
for relative, source in files.items():
    target = OUT/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    if target.exists():
        assert target.read_bytes() == data, 'Do not overwrite changed evidence: '+relative
    else:
        shutil.copyfile(source, target)
    assert target.read_bytes() == data
    entries.append({'path': relative, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
assert hashlib.sha256((OUT/'sface_engineering.xmodel').read_bytes()).hexdigest() == result['sha256']
verification = {
    'status': 'COMPILED_ENGINEERING_CANDIDATE_NOT_PRODUCTION_IDENTITY',
    'checked_utc': datetime.now(timezone.utc).isoformat(), 'files': entries,
    'model_sha256': result['sha256'], 'compiled_target': result['target_fingerprint'],
    'dpu_core_subgraphs': 1, 'non_dpu_operations': ['data-fix input', 'fix2float output'],
    'int8_quantization_and_compilation_completed': True,
    'representative_identity_calibration': False, 'independent_identity_accuracy_accepted': False,
    'board_engineering_smoke': board_status,
    'unified_dpu_scheduling_tested': False, 'real_enrollment_ui_accepted': False,
    'production_code_or_services_changed': False, 'fpga_bitstream_changed': False,
    'private_inputs_embeddings_or_identity_database_published': False,
    'reference_tensors_or_uart_raw_published': False,
}
(OUT/'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'shared_files_verified': len(entries), 'model_bytes': result['bytes'],
                  'board_engineering_smoke_status': board_status.get('status') if board_status else None,
                  'production_identity_accepted': False}, ensure_ascii=False))
