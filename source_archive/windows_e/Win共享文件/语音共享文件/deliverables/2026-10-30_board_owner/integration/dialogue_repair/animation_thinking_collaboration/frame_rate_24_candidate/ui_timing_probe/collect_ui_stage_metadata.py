"""Root-owned passive collection of fixed numeric UI/render fields.

Preparing/importing this module performs no connection or device operation.
The coordinator alone runs main after binding the current production entry.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent.parent.parent

REMOTE_EXTRA = '''
import math as _ui_math

def _ui_numbers(value, keys):
    if not isinstance(value, dict):
        return {}
    return {key:value[key] for key in keys if type(value.get(key)) in (int,float)
            and _ui_math.isfinite(value[key]) and 0 <= value[key] <= 9007199254740991}

def _ui_profile(value):
    value = value if isinstance(value, dict) else {}
    result = _ui_numbers(value, ('frames','window_seconds'))
    for key in ('core','compose_resize','jpeg','public','total','interval'):
        if isinstance(value.get(key), dict):
            result[key] = _ui_numbers(value[key], ('p50','p95','max'))
    return result

_ui_renderer = state.get('avatar_renderer', {})
_ui_renderer = _ui_renderer if isinstance(_ui_renderer, dict) else {}
observed = {key:out[key] for key in ('observed_mono','startup_sha256','phase','playing',
    'listening','native','runtime_faults','audio_output','safe_capture')}
observed.update(_ui_numbers(state, ('ui_tick_ms',)))
observed['ui_stage_timings_ms'] = _ui_numbers(state.get('ui_stage_timings_ms'),
    ('commands','controller_read','settings','runtime_widgets','business_widgets',
     'presentation','business_public'))
observed['renderer_profile'] = _ui_profile(_ui_renderer.get('profile'))
observed['renderer_timings_ms'] = _ui_numbers(_ui_renderer.get('timings_ms'),
    ('target_fps','core','compose_resize','jpeg','public','total','native_push','native_enqueue'))
print(json.dumps(observed))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-root-only', action='store_true', required=True)
    parser.add_argument('--samples', type=int, choices=range(2,41), default=20)
    args = parser.parse_args()
    probe_path = REPAIR/'probe.py'
    spec = importlib.util.spec_from_file_location('root_existing_metadata_probe', probe_path)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    if probe.REMOTE.count('print(json.dumps(out))') != 1:
        raise ValueError('Existing metadata probe requires coordinator review')
    source = probe.REMOTE.replace('print(json.dumps(out))', REMOTE_EXTRA)
    script = ('import time\nSOURCE=' + repr(source) + '\nfor _ in range(' + str(args.samples)
              + '):\n exec(SOURCE)\n time.sleep(1)\n')
    rows = [json.loads(line) for line in probe.ssh('python3 -B -', script,
            timeout=args.samples*2+10).splitlines() if line.strip()]
    if len(rows) != args.samples:
        raise ValueError('Incomplete numeric sample window')
    directory = HERE/'probe_results'
    directory.mkdir(exist_ok=True)
    output = directory/('ui_stages_'+str(time.time_ns())+'.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(dict(schema='aura.ui-stage-numeric-samples.v1', samples=rows,
            collector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            root_metadata_probe_sha256=hashlib.sha256(probe_path.read_bytes()).hexdigest(),
            raw_state_exported=False, audio_or_camera_opened_by_collector=False), stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(evidence=str(output), samples=len(rows),
        stage_samples=sum(bool(row['ui_stage_timings_ms']) for row in rows),
        ui_tick_ms=[row.get('ui_tick_ms') for row in rows])))


if __name__ == '__main__':
    main()
