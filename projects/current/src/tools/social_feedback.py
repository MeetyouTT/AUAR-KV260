"""Prepare short selected-voice social cues outside the live turn path."""
import hashlib
import threading
import uuid
from pathlib import Path
from common.voice_wire import PROTOCOL,REVISION,voice_reply

def prepare(models,*,deadline=None):
    assets={}
    for key,text in (('arrival','嗯？'),('invitation','想和我聊点什么呀？')):
        generated=(models.voice.generate(text) if deadline is None else
            models.voice.generate_bounded(text,deadline=deadline,cancelled=threading.Event(),request_id='startup-cue-'+uuid.uuid4().hex));raw=Path(generated['path']).read_bytes()
        sha=hashlib.sha256(raw).hexdigest();target=models.root/'audio'/(sha+'.wav')
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():target.write_bytes(raw)
        value=voice_reply({'protocol':PROTOCOL,'source_kind':'actual','engine':'omnivoice','revision':REVISION,
            'num_step':16,'reply_text':text,'emotion':'neutral','sha256':sha,'bytes':len(raw),'duration_seconds':generated['duration_seconds']})
        if value['duration_seconds']>5:raise ValueError('Social cue exceeds playback bound')
        assets[key]=value
    models.social_assets=assets
