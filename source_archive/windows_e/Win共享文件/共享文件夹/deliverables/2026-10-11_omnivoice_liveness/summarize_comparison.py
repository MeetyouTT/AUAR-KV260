"""Summarize this small local audition; never infer subjective quality."""
import json
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
result = {'scope': 'RTX 5060 Ti local complete synthesis; small sample; not first audible latency or board performance',
          'human_listening_status': 'pending', 'engines': {}}
for name in ('qwen', 'omnivoice_16', 'omnivoice_32'):
    report = json.loads((HERE/'runs'/name/'report.json').read_text(encoding='utf-8'))
    assert report['status'] == 'COMPLETE' and len(report['clips']) == 8
    clips = report['clips']
    warm = [c for c in clips if not c['first_after_load']]
    item = {'clips': len(clips), 'warm_clips': len(warm),
            'warm_generation_seconds_range': [min(c['generation_seconds'] for c in warm), max(c['generation_seconds'] for c in warm)],
            'warm_generation_seconds_median': median(c['generation_seconds'] for c in warm),
            'warm_rtf_range': [min(c['rtf'] for c in warm), max(c['rtf'] for c in warm)],
            'warm_rtf_median': median(c['rtf'] for c in warm),
            'first_after_load': [{'id': c['id'], 'generation_seconds': c['generation_seconds']} for c in clips if c['first_after_load']],
            'peak_pytorch_allocated_gib': max(c['peak_cuda_allocated_bytes'] for c in clips)/(1024**3),
            'max_raw_clipping_fraction': max(c['raw_clipping_fraction'] for c in clips)}
    result['engines'][name] = item
(HERE/'comparison_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
