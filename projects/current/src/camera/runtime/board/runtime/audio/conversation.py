"""Explicit full-voice transport using the existing recording generation gate."""
import http.client
import os
from pathlib import Path
import time
import uuid
from common.voice_wire import voice_reply,wav_payload,MAX_WAV
from board.runtime.audio.transcription import TranscriptionJobs,recognize

class ConversationJobs(TranscriptionJobs):
    def __init__(self,config,boot_id,cache_root):
        self.cache_root=Path(cache_root)
        self.cache_root.mkdir(parents=True,exist_ok=True)
        super().__init__(config,boot_id,transport=self.converse,include_voice=True)

    def converse(self,config,meta,pcm,timeout):
        deadline=time.monotonic()+timeout
        result=recognize(config,meta,pcm,timeout,endpoint='/v1/voice/converse')
        if not result.get('text'):return result
        value=voice_reply(result.get('voice_reply'))
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('Voice reply expired before audio download')
        connection=http.client.HTTPConnection(config['host'],config['port'],timeout=remaining)
        try:
            connection.request('GET','/v1/voice/audio/'+value['sha256']+'.wav')
            reply=connection.getresponse()
            if reply.status!=200:raise RuntimeError('Voice audio HTTP '+str(reply.status))
            raw=reply.read(MAX_WAV+1)
        finally:connection.close()
        wav_payload(value,raw)
        if time.monotonic()>=deadline:raise TimeoutError('Voice audio download expired')
        path=self.cache_root/(value['sha256']+'.wav')
        temporary=path.with_name(path.name+'.part-'+uuid.uuid4().hex)
        try:
            temporary.write_bytes(raw);os.replace(str(temporary),str(path))
        finally:
            if temporary.exists():temporary.unlink()
        result['voice_reply']=dict(value,path=str(path))
        return result
