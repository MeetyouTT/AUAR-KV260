"""Load only the own pinned range config when a new manual child starts."""
import hashlib,json
from pathlib import Path

def current_config(base,*,aura=None):
    aura=Path(aura) if aura is not None else Path(__file__).resolve().parents[2]
    path=aura/'config/pan_manual.local.json';startup=aura.parents[1]/'startup/config.json'
    raw=path.read_bytes();pins=json.loads(startup.read_text())['component_sha256']
    if hashlib.sha256(raw).hexdigest()!=pins.get('config/pan_manual.local.json'):
        raise RuntimeError('Current manual config does not match the own GUI pin')
    value=json.loads(raw)
    if (any(value.get(k)!=base.get(k) for k in ('boot_id','fdt_sha256','face_follow_config','enabled'))
            or value.get('enabled') is not True or value.get('maximum_step_us')!=20
            or value.get('maximum_duration_s')!=2
            or not 500<=value['manual_minimum_us']<value['manual_maximum_us']<=2500):
        raise RuntimeError('Manual config platform or bounded scope changed')
    return value
