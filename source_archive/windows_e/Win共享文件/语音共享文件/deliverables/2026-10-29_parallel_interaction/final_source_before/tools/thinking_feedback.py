"""Prepare one selected-voice feedback clip on the PC, outside the turn path."""
import hashlib
from pathlib import Path
from common.voice_wire import PROTOCOL,REVISION,voice_reply

TEXT='我想一下，再回答你。'


def prepare(models):
    generated=models.voice.generate(TEXT)
    raw=Path(generated['path']).read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    target=models.root/'audio'/(sha+'.wav')
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():target.write_bytes(raw)
    value=voice_reply({'protocol':PROTOCOL,'source_kind':'actual','engine':'omnivoice','revision':REVISION,
                      'num_step':16,'reply_text':TEXT,'emotion':'neutral','sha256':sha,'bytes':len(raw),
                      'duration_seconds':generated['duration_seconds']})
    if value['duration_seconds']>5:raise ValueError('Thinking cue unexpectedly long')
    models.feedback_assets={'thinking':value}
