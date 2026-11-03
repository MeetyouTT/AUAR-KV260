"""Deterministic command-only replay. No camera, network or MMIO imports."""
import argparse,copy,hashlib,json,math,sys
from pathlib import Path
from types import SimpleNamespace


def replay(root,library):
    sys.path[:0]=[str(root),str(root.parent)]
    from common.motion_observation import PROTOCOL
    from continuous_face_control import EdgeConfig
    from continuous_session import ContinuousSession
    from trajectory import Trajectory
    solver=Trajectory(library,hashlib.sha256(library.read_bytes()).hexdigest())

    class Device:
        def __init__(self,clock):
            self.clock=clock;self.pulse=self.accepted_target_us=1469
            self.armed=self.active=False;self.reason=0;self.epoch=1;self.session=1;self.ack_seq=0
            self.deadline=self.reference_time=None;self.commands=[];self.arms=self.stops=self.finishes=0
        def status(self):
            if self.active and self.clock()>=self.deadline:self.active=self.armed=False;self.reason=4
            return dict(flags=(15 if self.active else 14 if self.armed else 0)|(self.reason<<4),
                width_us=self.pulse,target_us=self.pulse,session=self.session,epoch=self.epoch,
                ack_seq=self.ack_seq,reference_us=1469,reason=self.reason,armed=self.armed,
                lease_left_ms=max(0,int((self.deadline-self.clock())*1000)) if self.active else 0)
        def confirm_and_arm(self,reference,session,epoch,**options):
            self.armed=True;self.active=False;self.reason=0;self.session=session;self.epoch=epoch
            self.reference_time=self.clock();self.ack_seq=0;self.arms+=1
        def submit(self,target,stamp,freshness_s=.25,margin_s=.02):
            self.status()
            assert self.armed and self.reference_time<stamp<=self.clock()
            assert 1400<=target<=1600 and abs(target-self.pulse)<=4
            lease=math.floor((stamp+freshness_s-self.clock()-margin_s)*1000)
            assert lease>=3
            previous=self.pulse;self.pulse=self.accepted_target_us=target
            self.active=True;self.ack_seq+=1;self.deadline=self.clock()+lease/1000.
            assert self.deadline<=stamp+freshness_s and self.deadline<=stamp+.25
            self.commands.append(dict(time_s=self.clock(),source_s=stamp,target_us=target,
                delta_us=target-previous,lease_deadline_s=self.deadline))
            return dict(outcome='ACCEPTED',lease_ms=lease,readback=self.status())
        def stop(self):
            self.armed=self.active=False;self.reason=0;self.stops+=1;return self.status()
        def finish(self):self.finishes+=1;return self.stop()

    class Scene:
        def __init__(self):
            self.now=10.;self.fid=0;self.packets={};self.last=None
            self.device=Device(lambda:self.now)
            self.session=ContinuousSession(self.device,'fixture-boot',EdgeConfig(left_ratio=.1),
                lambda pulse:SimpleNamespace(reference_us=pulse),trajectory=solver,
                clock=lambda:self.now,allow_fixture=True)
        def wait(self,ticks=4):
            for _ in range(ticks):self.now+=.02;self.session.tick()
        def image(self,center=.5,*,state='READY',anchor_age_ms=100,**changes):
            self.fid+=1;stamp=int(self.now*1000)-60
            packet=dict(protocol_version=PROTOCOL,source_kind='fixture',target_kind='face',
                board_boot_id='fixture-boot',service_epoch='camera-service',camera_epoch='camera',
                state=state,source_frame_id=self.fid,source_mono_ms=stamp,deadline_mono_ms=stamp+250,
                frame_width=640,frame_height=480,mirror_horizontal=True,
                face_detection_mono_ms=int(self.now*1000)-anchor_age_ms,
                target=dict(track_id=1,track_generation=1,box=[max(0.,center*640-40),100.,80.,80.],score=.95))
            if state!='READY':
                packet.update(target=None,source_frame_id=None,source_mono_ms=None,deadline_mono_ms=None)
                packet['face_tracking']=dict(version=11,error='',reason='FACE_TEMPLATE_VISIBLE_CLIP')
            packet.update(changes)
            self.last=copy.deepcopy(packet)
            if packet['state']=='READY':self.packets[stamp]=copy.deepcopy(packet)
            self.session.step(packet)
        def feed(self,centers):
            for center in centers:self.image(center);self.wait()
        def result(self,name):
            state=self.session.status();commands=self.device.commands
            for command in commands:
                packet=self.packets[round(command['source_s']*1000)]
                anchor_deadline=(packet['face_detection_mono_ms']+500)/1000.
                # Report rather than hide a legacy contract violation.
                command['anchor_overrun_ms']=max(0.,1000*(command['lease_deadline_s']-anchor_deadline))
            result=dict(name=name,scope='synthetic images and fake device; real Ruckig math',
                elapsed_s=round(self.now-10.,3),arms=self.device.arms,accepted_commands=len(commands),
                target_changes=sum(c['delta_us']!=0 for c in commands),final_target_us=self.device.pulse,
                maximum_displacement_us=max([abs(c['target_us']-1469) for c in commands] or [0]),
                maximum_step_us=max([abs(c['delta_us']) for c in commands] or [0]),
                maximum_anchor_overrun_ms=round(max([c['anchor_overrun_ms'] for c in commands] or [0]),3),
                fatal=state['fatal'],active=state['active'],reason=state['reason'],events=state['events'],
                correction_budget_releases=state.get('correction_budget_releases'),
                last_commands=commands[-12:])
            stopped=self.session.close()['readback']
            assert stopped['flags']==0 and stopped['lease_left_ms']==0
            result['closed_stopped']=True
            return result

    scenes=[]
    s=Scene();s.feed([.5]*100);scenes.append(s.result('inside_no_motion'))
    s=Scene();s.feed([.79]*10);s.feed([.808,.804]*50);scenes.append(s.result('right_line_tremor'))
    for name,outside,inside in [('right_single_inside',.85,.8),('left_single_inside',.15,.18)]:
        s=Scene();s.feed([.5]*10)
        for _ in range(6):s.feed([outside]*24+[inside])
        scenes.append(s.result(name))
    s=Scene();s.feed([.5]*10)
    for _ in range(4):s.feed([.85]*24+[.7]*8)
    scenes.append(s.result('stable_return_allows_later_correction'))
    s=Scene();s.feed([.85]*20);s.image(state='EXPIRED');s.wait(2);s.image(.85);s.wait()
    scenes.append(s.result('brief_refresh_without_deadline_extension'))
    s=Scene();s.feed([.85]*20)
    for _ in range(12):s.image(state='EXPIRED');s.wait(1)
    scenes.append(s.result('refresh_never_renews_frozen_source'))
    s=Scene();s.feed([.85]*20);s.wait(16);scenes.append(s.result('no_new_frames_stop'))
    for state in ['NO_TARGET','MULTIPLE_FACES']:
        s=Scene();s.feed([.85]*20);s.image(state=state);s.wait(2);scenes.append(s.result(state.lower()+'_stop'))
    s=Scene();s.feed([.85]*20);s.image(.85,board_boot_id='new-boot');s.wait(2)
    scenes.append(s.result('new_boot_is_rejected'))
    s=Scene();s.feed([.85]*20);s.image(.85,target_kind='body');s.wait(2)
    scenes.append(s.result('body_is_rejected'))
    s=Scene();s.feed([.85]*20);s.image(.85,anchor_age_ms=450);s.wait(1);s.wait(4)
    scenes.append(s.result('old_anchor_cannot_use_full_image_lease'))
    return dict(scope='offline-only command replay; no camera, service, board or MMIO access',
        controller_root=str(root),host_trajectory_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
        software_bounds_us=[1400,1600],source_ttl_ms=250,anchor_ttl_ms=500,margin_ms=20,
        image_age_at_arrival_ms=60,image_interval_ms=80,control_tick_ms=20,scenarios=scenes)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--controller-root',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--host-library',type=Path,default=Path(__file__).resolve().parents[1]/'ps_trajectory_v1/libaura_trajectory_compat_host.so')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=replay(a.controller_root.resolve(),a.host_library.resolve())
    with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(a.output),scenarios=len(report['scenarios']),board_accessed=False)))


if __name__=='__main__':main()
