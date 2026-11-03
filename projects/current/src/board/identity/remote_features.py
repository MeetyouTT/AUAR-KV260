"""LAN face-only feature client; caller still owns source expiry and matching."""
import hashlib
import http.client
import json
import uuid
from common.face_features import PROTOCOL,MODEL_ID,checked_meta,checked_reply,encode_meta

class RemoteFaceFeatures:
    def __init__(self,config):
        if (not isinstance(config,dict) or set(config)!={'kind','host','port','timeout_ms'}
                or config['kind']!='windows_sface' or config['host']!='192.168.50.1'
                or config['port']!=8792 or type(config['timeout_ms']) is not int
                or not 100<=config['timeout_ms']<=1000):raise ValueError('Invalid Windows feature endpoint')
        self.config=config

    def feature(self,png,target,fid,stamp):
        meta={'protocol':PROTOCOL,'model_id':MODEL_ID,'request_id':uuid.uuid4().hex,'target':target,
              'frame_id':fid,'captured_mono_ms':stamp,'sha256':hashlib.sha256(png).hexdigest()}
        checked_meta(meta,png)
        c=self.config;connection=http.client.HTTPConnection(c['host'],c['port'],timeout=c['timeout_ms']/1000)
        try:
            connection.request('POST','/v1/identity/face-features',body=png,
                headers={'Content-Type':'image/png','X-Aura-Face':encode_meta(meta)})
            response=connection.getresponse();raw=response.read(16385)
            if response.status!=200 or len(raw)>16384:raise OSError('Windows face features unavailable')
            return checked_reply(json.loads(raw),meta)
        finally:connection.close()
