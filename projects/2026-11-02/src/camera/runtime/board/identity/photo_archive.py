"""Opt-in face-only enrollment photos, separate from names and biometric vectors."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import uuid
from common.face_features import checked_png


def configuration(value):
    if (not isinstance(value,dict) or set(value)!={'enabled','directory','max_images_per_session'}
            or type(value['enabled']) is not bool or not isinstance(value['directory'],str)
            or not Path(value['directory']).expanduser().is_absolute()
            or type(value['max_images_per_session']) is not int
            or not 8<=value['max_images_per_session']<=256):
        raise ValueError('Invalid enrollment photo archive configuration')
    return dict(value)


class EnrollmentPhotoArchive:
    def __init__(self,config):
        self.config=configuration(config);self.root=Path(config['directory']).expanduser()
        self.lock=threading.RLock();self.document=None;self.active=None
        self.error='';self.error_count=0;self.last_error=''
        if not self.config['enabled']:return
        try:
            self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
            if self.root.is_symlink():raise ValueError('Archive root must be a real directory')
            latest=self.root/'latest.json'
            if latest.is_file():
                sid=json.loads(latest.read_text())['session_id'];self._session(sid)
                path=self.root/sid/'manifest.json'
                if path.stat().st_size>524288:raise ValueError('Oversized photo manifest')
                self.document=json.loads(path.read_text())
                if self.document['session_id']!=sid:raise ValueError('Photo manifest owner mismatch')
                if self.document['outcome']=='in_progress':
                    self.document['outcome']='interrupted';self._manifest()
        except (OSError,ValueError,KeyError,TypeError) as exc:self._failed(exc)

    @staticmethod
    def _session(sid):
        if not isinstance(sid,str) or not re.fullmatch('[0-9a-f]{32}',sid):raise ValueError('Invalid photo session')

    def _atomic(self,path,raw):
        if path.is_symlink():raise ValueError('Photo archive symlinks are not allowed')
        temporary=path.with_name(path.name+'.part-'+uuid.uuid4().hex)
        descriptor=os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            with os.fdopen(descriptor,'wb') as out:
                out.write(raw);out.flush();os.fsync(out.fileno())
            os.replace(temporary,path)
        finally:temporary.unlink(missing_ok=True)

    def _folder(self):return self.root/self.document['session_id']
    def _manifest(self):
        self._atomic(self._folder()/'manifest.json',json.dumps(self.document,ensure_ascii=False,
                     allow_nan=False,indent=2).encode('utf-8'))
    def _failed(self,exc):
        self.error=type(exc).__name__+': '+str(exc)[:160];self.last_error=self.error;self.error_count+=1
    def _owns(self,sid):return self.config['enabled'] and self.active==sid and self.document is not None

    def begin(self,sid,revision,threshold,margin,policy):
        with self.lock:
            if not self.config['enabled']:return False
            try:
                self._session(sid);(self.root/sid).mkdir(mode=0o700)
                self.document={'schema':'aura-enrollment-photos-1','session_id':sid,'outcome':'in_progress',
                    'database_revision_before':revision,'threshold':threshold,'ambiguity_margin':margin,
                    'template_policy':policy,'image_size':[112,112],'images':[],'selected':None,
                    'validation_frame_ids':[],'validation_scores':[],'truncated':False,'omitted_image_count':0,
                    'contains_full_camera_frames':False,'contains_embeddings_or_names':False}
                self._manifest();self._atomic(self.root/'latest.json',json.dumps({'session_id':sid}).encode())
                self.active=sid;self.error='';return True
            except (OSError,ValueError,TypeError,KeyError) as exc:self._failed(exc);return False

    def sample(self,sid,result,pose,decision,score=None,gap=None):
        with self.lock:
            if not self._owns(sid):return False
            try:
                if decision not in ('collect','front_selection','quality_rejected','pose_rejected',
                                    'validation_pass','validation_rejected'):raise ValueError('Invalid photo decision')
                raw=result.get('face_png');checked_png(raw);fid,stamp=result['fid'],result['stamp']
                if type(fid) is not int or fid<1 or type(stamp) is not int or stamp<0:raise ValueError('Invalid photo source')
                if any(row['frame_id']==fid for row in self.document['images']):return True
                if len(self.document['images'])>=self.config['max_images_per_session']:
                    self.document['truncated']=True;self.document['omitted_image_count']+=1;self._manifest();return False
                pose={k:float(pose[k]) for k in ('yaw','roll','pixels','eye_distance','blur')}
                if not all(math.isfinite(v) for v in pose.values()):raise ValueError('Invalid photo pose')
                if any(v is not None and (type(v) not in (int,float) or not math.isfinite(v)) for v in (score,gap)):
                    raise ValueError('Invalid photo score')
                filename='frame_%010d.png'%fid;self._atomic(self._folder()/filename,raw)
                self.document['images'].append({'filename':filename,'frame_id':fid,'captured_mono_ms':stamp,
                    'sha256':hashlib.sha256(raw).hexdigest(),'decision':decision,'pose':pose,
                    'score':score,'other_identity_gap':gap})
                self._manifest();self.error='';return True
            except (OSError,ValueError,TypeError,KeyError) as exc:self._failed(exc);return False

    def select(self,sid,candidate):
        with self.lock:
            if not self._owns(sid):return False
            try:
                raw=candidate.get('face_png');checked_png(raw);self._atomic(self._folder()/'selected.png',raw)
                self.document['selected']={'filename':'selected.png','frame_id':candidate['fid'],
                    'sha256':hashlib.sha256(raw).hexdigest()};self._manifest();self.error='';return True
            except (OSError,ValueError,TypeError,KeyError) as exc:self._failed(exc);return False

    def validated(self,sid,frame_ids,scores):
        with self.lock:
            if not self._owns(sid):return False
            try:
                if len(frame_ids)!=5 or len(set(frame_ids))!=5 or len(scores)!=5:
                    raise ValueError('Expected five independent validation photos')
                self.document['validation_frame_ids']=list(frame_ids)
                self.document['validation_scores']=list(scores);self._manifest();return True
            except (OSError,ValueError,TypeError) as exc:self._failed(exc);return False

    def finish(self,sid,outcome,revision=None,reason=''):
        with self.lock:
            if not self._owns(sid):return False
            try:
                if outcome not in ('committed','cancelled','failed','interrupted'):raise ValueError('Invalid photo outcome')
                self.document.update(outcome=outcome,database_revision_after=revision,reason=reason)
                self._manifest();self.active=None;self.error='';return True
            except (OSError,ValueError,TypeError) as exc:self._failed(exc);return False

    def health(self):
        with self.lock:
            return {'enabled':self.config['enabled'],'ready':self.config['enabled'] and not self.error,
                'directory':str(self.root),'active_session':self.active,
                'latest_session':self.document['session_id'] if self.document else None,
                'image_count':len(self.document['images']) if self.document else 0,
                'outcome':self.document['outcome'] if self.document else None,
                'error':self.error,'error_count':self.error_count,'last_error':self.last_error}
