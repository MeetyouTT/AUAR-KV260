"""Synthetic controller checks only; no actuator, device, VART or user data."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from continuous_face_control import EdgeConfig,FaceEdgeController
from common.motion_observation import PROTOCOL


def replay(values,config=None):
    c=FaceEdgeController('fixture-boot',1445,config=config or EdgeConfig());rows=[]
    for fid,center in enumerate(values,1):
        stamp=1000+50*fid
        p={'protocol_version':PROTOCOL,'source_kind':'fixture','target_kind':'face','board_boot_id':'fixture-boot',
          'service_epoch':'synthetic-service','camera_epoch':'synthetic-camera','state':'READY',
          'source_frame_id':fid,'source_mono_ms':stamp,'deadline_mono_ms':stamp+250,'frame_width':640,
          'frame_height':480,'mirror_horizontal':True,'target':{'track_id':1,'track_generation':1,
          'box':[640*center-40,100.,80.,80.],'score':.95}}
        rows.append(c.observe(p,stamp+20,allow_fixture=True))
    return rows


def main():
    moving=[.81+.004*i for i in range(20)];fast=replay(moving);still=replay([moving[-1]]*20)
    inward=replay([.90-.004*i for i in range(20)]+[.80])
    values=[.85]*10+[.93]+[.85]*12;smooth=replay(values);unfiltered=replay(values,EdgeConfig(median_window=1))
    inside=replay([.2,.4,.7,.8]*20)
    report={'status':'SYNTHETIC_FEEDBACK_REPLAY','real_hardware_commands':0,'physical_test':False,
       'fast_outward_requested_us_s':fast[-1]['requested_velocity_us_s'],
       'static_same_final_position_requested_us_s':still[-1]['requested_velocity_us_s'],
       'inward_before_boundary_requested_us_s':inward[-2]['requested_velocity_us_s'],
       'raw_inside_immediate_stop':inward[-1]['velocity_us_s']==0 and inward[-1]['pulse_us']==inward[-2]['pulse_us'],
       'single_spike_requested_with_median_us_s':smooth[10]['requested_velocity_us_s'],
       'single_spike_requested_without_median_us_s':unfiltered[10]['requested_velocity_us_s'],
       'inside_pulses_unchanged':all(r['pulse_us']==1445 for r in inside),
       'maximum_observed_velocity_us_s':max(abs(r['velocity_us_s']) for r in fast+smooth+unfiltered),
       'all_commands_in_authorized_range':all(1425<=r['pulse_us']<=1505 for r in fast+smooth+unfiltered)}
    assert report['fast_outward_requested_us_s']>report['static_same_final_position_requested_us_s']
    assert report['single_spike_requested_with_median_us_s']<report['single_spike_requested_without_median_us_s']
    assert report['raw_inside_immediate_stop'] and report['inside_pulses_unchanged'] and report['all_commands_in_authorized_range']
    print(json.dumps(report))


if __name__=='__main__':main()
