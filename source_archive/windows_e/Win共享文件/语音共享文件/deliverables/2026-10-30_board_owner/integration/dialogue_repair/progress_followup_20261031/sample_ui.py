"""Sample existing numeric UI/render diagnostics using the established metadata probe."""
import importlib.util
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
module_spec = importlib.util.spec_from_file_location('existing_metadata_probe', HERE.parent / 'probe.py')
probe = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(probe)
extra = '''
profile = state.get('avatar_renderer', {})
observed = {key:out[key] for key in ('observed_mono','startup_sha256','phase','playing','listening',
    'native','runtime_faults','audio_output','safe_capture')}
observed['ui_tick_ms'] = state.get('ui_tick_ms') if type(state.get('ui_tick_ms')) in (int,float) else None
observed['renderer_profile'] = scalar(profile.get('profile',{})) if isinstance(profile,dict) else {}
observed['renderer_timings_ms'] = scalar(profile.get('timings_ms',{})) if isinstance(profile,dict) else {}
print(json.dumps(observed))
'''
assert probe.REMOTE.count('print(json.dumps(out))') == 1
source = probe.REMOTE.replace('print(json.dumps(out))', extra)
script = 'import time\nSOURCE=' + repr(source) + '\nfor _ in range(20):\n exec(SOURCE)\n time.sleep(1)\n'
rows = [json.loads(line) for line in probe.ssh('python3 -B -', script, timeout=50).splitlines() if line.strip()]
output = HERE / ('ui_samples_' + str(time.time_ns()) + '.json')
with output.open('x', encoding='utf-8') as stream:
    json.dump(dict(samples=rows), stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(evidence=str(output), samples=len(rows),
                      startup_sha256=rows[0]['startup_sha256'],
                      ui_tick_ms=[row['ui_tick_ms'] for row in rows],
                      renderer_profile=rows[-1]['renderer_profile'],
                      renderer_timings_ms=rows[-1]['renderer_timings_ms'])))
