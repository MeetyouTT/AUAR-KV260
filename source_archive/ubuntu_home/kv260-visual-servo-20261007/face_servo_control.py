"""Bounded camera-error to pulse targets, with actual hardware acknowledgement.

No camera, hardware transport or ARM is created here. Relative values are
microseconds around a confirmed pulse, not falsely labelled physical degrees.
"""
import math
from fixed_view_mapping import FixedViewMapping, REFERENCE_X_PX


class FaceServoController:
    def __init__(self, driver, camera_epoch, *, max_offset_us=40, rate_us_s=40,
                 max_step_us=4, freshness_s=.25, submit_margin_s=.02, fixed_view_mapping=None):
        if (driver.reference is None or not camera_epoch or type(max_offset_us) is not int
                or not 1<=max_offset_us<=40 or type(max_step_us) is not int or not 1<=max_step_us<=4
                or not isinstance(rate_us_s,(int,float)) or not math.isfinite(rate_us_s) or not 0<rate_us_s<=40
                or not 0<submit_margin_s<freshness_s<=.25):
            raise ValueError('Confirmed driver reference and bounded bench parameters required')
        if driver.reference.camera_moves_with_axis:
            if fixed_view_mapping is not None:
                raise ValueError('Stationary-camera mapping cannot be used with an axis-mounted camera')
        elif not isinstance(fixed_view_mapping,FixedViewMapping) or not fixed_view_mapping.matches(driver.reference,camera_epoch):
            raise ValueError('An independent camera requires measured blue-line position mapping')
        self.fixed_view_mapping = fixed_view_mapping
        self.mode = 'FIXED_VIEW_POSITION' if fixed_view_mapping is not None else 'AXIS_CAMERA_CENTERING'
        self.reference_x_px = REFERENCE_X_PX
        self.driver,self.epoch=driver,camera_epoch
        self.origin=driver.reference.reference_us
        self.polarity=driver.reference.polarity
        self.low=max(1400,self.origin-max_offset_us)
        self.high=min(1600,self.origin+max_offset_us)
        self.rate,self.step=rate_us_s,max_step_us
        self.freshness,self.margin=freshness_s,submit_margin_s
        self.frame=-1;self.source_time=None;self.key=None;self.filtered=None;self.control_time=None
        self.accepted_us=self.origin
        self.requested_continuous=float(self.origin)
        self.stopped=False
        self.reason='AWAITING_CONFIRMED_FACE'

    def stop(self, reason):
        self.stopped=True;self.reason=reason
        self.driver.stop()
        return {'outcome':'STOPPED','reason':reason,'accepted_us':self.accepted_us}

    def observe(self, snapshot, width, height, now, boot_id):
        if self.stopped:
            return {'outcome':'REJECTED','reason':'EXPLICIT_RECOVERY_REQUIRED'}
        if (boot_id!=self.driver.boot_id or not isinstance(snapshot,dict)
                or snapshot.get('epoch')!=self.epoch or width!=640 or height!=480):
            return self.stop('CAMERA_CONTEXT_CHANGED')
        fid,source=snapshot.get('frame_id'),snapshot.get('observed_time')
        if (type(fid) is not int or fid<1 or not isinstance(source,(int,float))
                or isinstance(source,bool) or not math.isfinite(source)
                or not isinstance(now,(int,float)) or not math.isfinite(now)):
            return self.stop('INVALID_SOURCE')
        if fid<=self.frame or (self.source_time is not None and source<=self.source_time):
            return {'outcome':'REJECTED','reason':'NO_NEW_OBSERVATION'}
        self.frame,self.source_time=fid,source
        if not 0<=now-source<=self.freshness:
            return self.stop('STALE_SOURCE')
        if not isinstance(snapshot.get('tracks'),list):
            return self.stop('INVALID_TRACKS')
        targets=[t for t in snapshot['tracks'] if isinstance(t,dict)
                 and t.get('track_id')==snapshot.get('target_id')]
        if len(targets)!=1 or targets[0].get('visible') is not True or targets[0].get('confirmed') is not True:
            if self.key is not None:
                return self.stop('TARGET_LOST')
            return {'outcome':'WAITING','reason':'NO_CONFIRMED_FACE'}
        target=targets[0]
        if (target.get('frame_id')!=fid or target.get('observed_time')!=source
                or target.get('epoch')!=self.epoch or type(target.get('generation')) is not int
                or target['generation']<1 or type(target.get('track_id')) is not int or target['track_id']<1):
            return self.stop('INVALID_TARGET_EVIDENCE')
        box=target.get('box')
        if (not isinstance(box,(list,tuple)) or len(box)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in box)
                or not 1<box[0]<width-1 or not 1<box[1]<height-1 or min(box[2:])<20
                or box[0]+box[2]>=width-1 or box[1]+box[3]>=height-1
                or box[2]*box[3]>.4*width*height):
            return self.stop('FACE_QUALITY_OR_BORDER')
        score=target.get('score')
        if type(score) not in (int,float) or not math.isfinite(score) or not .9<=score<=1:
            return self.stop('FACE_CONFIDENCE')
        key=(target['track_id'],target['generation'])
        if self.key is not None and key!=self.key:
            return self.stop('TARGET_CHANGED')
        if self.key is None and (type(target.get('consecutive')) is not int or target['consecutive']<5):
            return {'outcome':'WAITING','reason':'NEED_FIVE_CONFIRMATIONS'}
        error=((box[0]+box[2]/2)-self.reference_x_px)/(width/2)
        if self.key is None:
            self.key,self.filtered,self.control_time=key,error,source
            return {'outcome':'WAITING','reason':'TARGET_INITIALIZED'}
        dt=source-self.control_time
        if not 0<dt<=.25:
            return self.stop('CONTROL_TIME_GAP')
        self.filtered+=(1-math.exp(-dt/.1))*(error-self.filtered)
        self.control_time=source
        if self.fixed_view_mapping is not None:
            # With a stationary camera, servo motion cannot reduce image error.
            # Compute an absolute mapped target, then slew towards it; never
            # integrate a stationary off-centre person's error indefinitely.
            mapped = self.origin if abs(self.filtered)<=.04 else self.fixed_view_mapping.target_us(
                self.reference_x_px + self.filtered*(width/2))
            goal = max(self.low,min(self.high,mapped))
            limit = min(self.step,self.rate*dt)
            delta = max(-limit,min(limit,goal-self.requested_continuous))
        else:
            velocity=0 if abs(self.filtered)<=.04 else self.polarity*self.rate*self.filtered
            delta=max(-self.step,min(self.step,velocity*dt))
        # Retain rounding residue only on ACCEPTED; a rejected write must not
        # advance the integrator or the accepted command.
        target_float=max(self.low,min(self.high,self.requested_continuous+delta))
        pulse=round(target_float)
        result=self.driver.submit(pulse,source,self.freshness,self.margin)
        if result['outcome']=='ACCEPTED':
            self.accepted_us=pulse;self.requested_continuous=target_float
        elif result['outcome']=='UNKNOWN':
            return self.stop('UNKNOWN_ACCEPTANCE')
        elif result.get('reason') in ('STALE_SOURCE','SUBMISSION_TOO_LATE','PERMISSION_OR_CONTEXT'):
            return self.stop(result['reason'])
        self.reason=result.get('reason',result['outcome'])
        return dict(result,source_frame_id=fid,source_observed_time=source,
                    error=self.filtered,dt_s=dt,relative_pulse_us=self.accepted_us-self.origin,
                    control_mode=self.mode,reference_x_px=self.reference_x_px)
