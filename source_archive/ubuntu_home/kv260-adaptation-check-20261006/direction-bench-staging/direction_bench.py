"""Bounded direction demonstration, not calibrated pointing or formal tracking."""
import math
class DirectionBench:
 def __init__(self,boot,epoch,reference=1500,polarity=-1):
  if not boot or not epoch or reference!=1500 or polarity!=-1:raise ValueError('Exact direction-test context required')
  self.boot,self.epoch=boot,epoch;self.origin=reference;self.polarity=polarity
  self.last_frame=0;self.last_source=None;self.key=None;self.accepted=reference
 def observe(self,status,now):
  if status.get('boot_id')!=self.boot or status.get('epoch')!=self.epoch or not status.get('mirror_horizontal') or status.get('capture_size')!=[640,480]:
   return {'kind':'STOP','reason':'CAMERA_CONTEXT_CHANGED'}
  if status.get('error') or status.get('stopped'):return {'kind':'STOP','reason':'CAMERA_FAILURE'}
  s=status.get('snapshot') or {};source=s.get('observed_time');fid=s.get('frame_id')
  if type(source) not in (float,int) or not math.isfinite(source) or type(fid) is not int:
   return {'kind':'WAIT' if self.key is None else 'STOP','reason':'INVALID_SOURCE'}
  if not 0<=now-source<=.25:return {'kind':'WAIT' if self.key is None else 'STOP','reason':'STALE_SOURCE'}
  if fid<=self.last_frame:return {'kind':'WAIT','reason':'NO_NEW_FRAME'}
  if s.get('epoch')!=self.epoch:return {'kind':'STOP','reason':'SNAPSHOT_CONTEXT'}
  if self.last_source is not None and source<=self.last_source:return {'kind':'STOP','reason':'FROZEN_SOURCE_TIME'}
  visible=[t for t in s.get('tracks',[]) if t.get('visible') and t.get('confirmed')]
  targets=[t for t in visible if t.get('track_id')==s.get('target_id')]
  if len(visible)!=1 or len(targets)!=1:return {'kind':'WAIT' if self.key is None else 'STOP','reason':'LOST_OR_AMBIGUOUS'}
  t=targets[0];key=(t.get('track_id'),t.get('generation'))
  if self.key is not None and key!=self.key:return {'kind':'STOP','reason':'TARGET_CHANGED'}
  if type(t.get('consecutive')) is not int or t['consecutive']<5:return {'kind':'WAIT','reason':'CONFIRMING_TARGET'}
  if t.get('epoch')!=self.epoch or t.get('frame_id')!=fid or t.get('observed_time')!=source:return {'kind':'STOP','reason':'TARGET_EVIDENCE_MISMATCH'}
  b=t.get('box');score=t.get('score')
  if not isinstance(b,(list,tuple)) or len(b)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in b):
   return {'kind':'STOP','reason':'INVALID_BOX'}
  x,y,w,h=b
  if x<=1 or y<=1 or w<20 or h<20 or x+w>=639 or y+h>=479 or w*h>.6*640*480 or type(score) not in (int,float) or not .9<=score<=1:
   return {'kind':'WAIT' if self.key is None else 'STOP','reason':'FACE_QUALITY'}
  dt=0 if self.last_source is None else source-self.last_source
  if self.key is not None and not 0<dt<=.25:return {'kind':'STOP','reason':'CONTROL_TIME_GAP'}
  center=x+w/2;error=center-320
  # Fixed camera: bounded absolute bench offset, never accumulated image error.
  goal=self.origin if abs(error)<=12.8 else self.origin+self.polarity*20*max(-1,min(1,error/160))
  step=0 if self.key is None else min(4,40*dt)  # Existing conservative limits; no tuning.
  target=round(self.accepted+max(-step,min(step,goal-self.accepted)))
  self.key=key;self.last_frame=fid;self.last_source=source
  return {'kind':'COMMAND','target_us':target,'source_time':source,'frame_id':fid,'center_x':center,
          'goal_us':goal,'desired_direction':'COUNTERCLOCKWISE' if error<-12.8 else 'CLOCKWISE' if error>12.8 else 'CENTER'}
 def accept(self,target):self.accepted=target
