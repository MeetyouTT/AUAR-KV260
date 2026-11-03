"""Locate bounded VART startup delay using progress markers, no inference."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import urllib.request

assert os.uname().machine == 'aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
out = {'origins': {k: importlib.util.find_spec(k).origin for k in ('numpy', 'xir', 'vart')}}
allowed = {'XILINX_XRT', 'XLNX_VART_FIRMWARE', 'LD_LIBRARY_PATH', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'}
out['camera_runtime_environment'] = {k: v for k, v in (x.split('=', 1) for x in Path('/proc/987/environ').read_bytes().decode().split('\0') if '=' in x) if k in allowed}
code = '''import json,time
def mark(s):print(json.dumps({'phase':s,'time':time.monotonic()}),flush=True)
mark('start')
import numpy as np
mark('numpy_imported')
import xir
mark('xir_imported')
import vart
mark('vart_imported')
g=xir.Graph.deserialize('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/bee245f2a94e4d28/sface_engineering.xmodel')
mark('model_deserialized')
children=[s for s in g.get_root_subgraph().toposort_child_subgraph() if s.has_attr('device') and s.get_attr('device')=='DPU']
mark('before_runner_creation')
r=vart.Runner.create_runner(children[0],'run')
mark('runner_created')
'''
try:
    p = subprocess.run(['python3', '-u', '-B', '-c', code], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=24)
    out.update(exit_code=p.returncode, diagnostic_output=p.stdout.decode(errors='replace')[-3500:])
except subprocess.TimeoutExpired as exc:
    out.update(timeout=True, diagnostic_output=(exc.stdout or b'').decode(errors='replace')[-3500:])
try:
    with urllib.request.urlopen('http://127.0.0.1:8790/health', timeout=3) as r:
        s = json.load(r)
    out['camera'] = {k: s.get(k) for k in ('pid', 'service_epoch', 'detected_frames', 'observation_age_ms', 'camera_error', 'detector_error')}
except Exception as exc:
    out['camera_error_type'] = type(exc).__name__
print(json.dumps(out))
