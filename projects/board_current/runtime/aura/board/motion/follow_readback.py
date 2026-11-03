"""Validate this boot's stopped receipt without expanding manual jog bounds."""
import hashlib,json
from pathlib import Path


def verified_stopped_face_command(config,state):
    try:
        cfg_path=Path(config['face_follow_config']).resolve(strict=True)
        cfg=json.loads(cfg_path.read_text())
        settings=Path(cfg['arguments']['zone-settings']).resolve(strict=True)
        if json.loads(settings.read_text()).get('board_boot_id')!=config['boot_id']:return False
        receipt=json.loads((settings.parent/'face-stopped-readback.json').read_text())
        path=Path(receipt['report']).resolve(strict=True);raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:return False
        report=json.loads(raw)
        allowed=[{'root':cfg['release_root'],'sha256':cfg['manifest_sha256']}]+cfg.get('stopped_readback_predecessors',[])
        selected=next((x for x in allowed if x['sha256']==report['consumer_manifest_sha256']),None)
        if selected is None:return False
        root=Path(selected['root']).resolve(strict=True);path.relative_to(root/'runs')
        manifest_raw=(root/'deployment-manifest.json').read_bytes()
        if hashlib.sha256(manifest_raw).hexdigest()!=selected['sha256']:return False
        for item in json.loads(manifest_raw)['files']:
            if hashlib.sha256(Path(item['destination']).read_bytes()).hexdigest()!=item['sha256']:return False
        stopped=report['result']['stopped'];limits=report['range_us']
        return (report['status'] in ('FINITE_FACE_EDGE_SESSION_STOPPED','CONTINUOUS_FACE_ZONE_STOPPED')
            and report['boot_id']==config['boot_id'] and report['consumer_manifest_sha256']==selected['sha256']
            and report['target_kind']=='face' and limits in ([1425,1505],[1400,1600],[500,2500])
            and state['flags']==0 and state['lease_left_ms']==0 and limits[0]<=state['width_us']<=limits[1]
            and all(stopped[k]==state[k] for k in
                ('flags','lease_left_ms','width_us','target_us','ack_seq','epoch','session','reference_us')))
    except (OSError,ValueError,KeyError,TypeError):return False
