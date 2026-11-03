"""Accept a stopped face-test readback without expanding manual jog permission."""
import hashlib,json
from pathlib import Path

ROOT=Path('/home/root/aura-pan-current-20261024/463c9307')
GUI=ROOT/'gui-face-edge-v5/runtime/aura'


def verified_stopped_face_command(config, state):
    try:
        receipt=json.loads((ROOT/'face-stopped-readback.json').read_text())
        cfg=json.loads((GUI/'config/pan_face.local.json').read_text())
        root=Path(cfg['release_root']).resolve(strict=True)
        manifest_raw=(root/'deployment-manifest.json').read_bytes()
        if hashlib.sha256(manifest_raw).hexdigest()!=cfg['manifest_sha256']:return False
        for item in json.loads(manifest_raw)['files']:
            if hashlib.sha256(Path(item['destination']).read_bytes()).hexdigest()!=item['sha256']:return False
        path=Path(receipt['report']).resolve(strict=True);path.relative_to(root/'runs')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:return False
        report=json.loads(raw);stopped=report['result']['stopped']
        return (report['status']=='FINITE_FACE_EDGE_SESSION_STOPPED'
            and report['boot_id']==config['boot_id']
            and report['consumer_manifest_sha256']==cfg['manifest_sha256']
            and report['target_kind']=='face' and report['range_us']==[1425,1505]
            and state['flags']==0 and state['lease_left_ms']==0
            and 1425<=state['width_us']<=1505
            and all(stopped[k]==state[k] for k in
                ('flags','lease_left_ms','width_us','target_us','ack_seq','epoch','session','reference_us')))
    except (OSError,ValueError,KeyError,TypeError):return False
