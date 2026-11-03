"""Frontal-face readiness from fresh shared-camera metadata, no identity lookup."""
from board.interaction.ui_contract import validate_snapshot


def read_attention(snapshot,boot_id,now_ms):
    try:
        value=validate_snapshot(snapshot,boot_id,now_ms)
        if value['source_kind']!='actual' or value['modules'].get('camera',{}).get('state')!='READY':
            return None,'VISUAL_UNAVAILABLE'
        identity=value['modules']['identity']
        a=identity.get('face_attention')
        if identity.get('face_count')!=1:return None,'NO_SINGLE_FACE'
        if not a or not a['frontal']:return None,'NOT_FRONTAL'
        if not 0<=now_ms-a['captured_mono_ms']<min(a['ttl_ms'],1000):return None,'STALE_FACE'
        key=a['target']
        return {'key':(value['service_epoch'],key['camera_epoch'],key['track_id'],key['track_generation']),
                'frame_id':a['frame_id'],'stamp':a['captured_mono_ms']},'FRONTAL_FACE'
    except (ValueError,KeyError,TypeError):return None,'VISUAL_UNAVAILABLE'


class AttentionGate:
    def __init__(self,boot_id):
        self.boot_id=boot_id;self.reset()

    def reset(self):
        self.key=None;self.first=None;self.last=None;self.frames=0

    def observe(self,snapshot,now_ms):
        current,reason=read_attention(snapshot,self.boot_id,now_ms)
        if current is None:self.reset();return None,reason
        if self.key!=current['key']:
            self.key=current['key'];self.first=current['stamp'];self.last=None;self.frames=0
        if current['frame_id']!=self.last:
            self.last=current['frame_id'];self.frames+=1
        stable=self.frames>=2 and current['stamp']-self.first>=600
        return (current if stable else None),'READY' if stable else 'WAITING_STABLE_FACE'
