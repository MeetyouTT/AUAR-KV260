from pathlib import Path
import json,hashlib,shutil,datetime
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 feedback=dict(schema='aura-animation-human-revision-request-1',host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verbatim='下层手臂幅度太大，优化幅度确保摆动自然',R2_human_visual_acceptance=False,required_change='Reduce lower/back arm excursion and speed; retain continuous inertia with less rebound',lower_arm_mapping='pose A: body_parts/全身変形基礎/腕LA_le, original sprites0059/0052; hanging lower arm rather than front chest hand',device_actions=0)
 save(HERE/'USER_FEEDBACK.json',feedback)
 before=HERE/'baseline/native';after=HERE/'candidate/native'
 for p in (BASE/'candidate_physics_v2/native').iterdir():
  if p.is_file():
   before.mkdir(parents=True,exist_ok=True);after.mkdir(parents=True,exist_ok=True)
   shutil.copyfile(p,before/p.name);shutil.copyfile(p,after/p.name)
 p=after/'secondary_motion.hpp';s=p.read_text()
 replacements={
 'maximum{3.6,1.9,1.6,1.2,10.5,7.5}':'maximum{3.6,1.9,1.6,1.2,4.0,7.5}',
 'weight*(6.5*wave(4.8,.4)+1.3*wave(9.3,1.1))':'weight*(2.6*wave(6.8,.4)+.45*wave(10.7,1.1))',
 'constexpr double omega=6.,damping=.58;':'const double omega=i==0?5.:6.,damping=i==0?.85:.58;',
 'velocity_[i]=std::clamp(velocity_[i],-16.,16.);':'const double speed_limit=i==0?6.:16.;\n   velocity_[i]=std::clamp(velocity_[i],-speed_limit,speed_limit);',
 '// Semi-implicit damped spring: 60 Hz, f~0.95 Hz, damping ratio .58.':'// 60 Hz damped springs. Lower arm: smaller/slower target, damping .85.\n  // Front chest arm retains the accepted R2 values (.58, 6 rad/s).'
 }
 for old,new in replacements.items():assert s.count(old)==1,old;s=s.replace(old,new)
 p.write_text(s,encoding='utf8')
 assert sha(before/'yuki_host.cpp')==sha(after/'yuki_host.cpp') and sha(before/'yuki_host.h')==sha(after/'yuki_host.h')
 save(HERE/'candidate/SOURCE_MANIFEST.json',dict(schema='aura-lower-arm-natural-r3-1',baseline_library_sha256='0c73b9389c11def8e93aab540f73f2c011abdf93f47d2a16f9a0bbadabf9f199',files={p.name:sha(p) for p in after.iterdir() if p.is_file()},only_changed_file='secondary_motion.hpp',only_changed_motion_channel='aura_arm_left',preserved=['shoulder pivot compensation','head and body channels','front/chest arm','hair and parts amplitudes','eye mouth audio owner TTL policies'],production_loaded=False))
 print('R3 candidate: lower-arm target ~40%, slower period6.8s, damping .85, speed cap6deg/s; other channels unchanged')
if __name__=='__main__':main()
