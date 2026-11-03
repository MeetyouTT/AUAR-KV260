from inspect_baseline import *

def main():
    src=HERE/'baseline/native'
    dest=HERE/'candidate/native'
    dest.mkdir(parents=True,exist_ok=True)
    for p in src.iterdir():
        if p.is_file():shutil.copyfile(p,dest/p.name)
    path=dest/'yuki_host.cpp'
    text=path.read_text(encoding='utf-8')
    text=text.replace('#include "gentle_motion.hpp"','#include "gentle_motion.hpp"\n#include "facial_envelope.hpp"',1)
    text=text.replace('aura_yuki::GentleMotion gentle_motion;','aura_yuki::GentleMotion gentle_motion;\n aura_yuki::FacialEnvelope facial_envelope;',1)
    old='''  const bool closed=policy==YUKI_EYES_THINKING_CLOSED;
  const std::array<ParamId,3> ids{face[2],talk,face[1]};
  const std::array<bool,3> override{policy!=YUKI_EYES_AUTHORED,true,closed};
  const std::array<float,3> targets{closed?10.f:0.f,float(mouth),0.f};'''
    new='''  const bool closed=policy==YUKI_EYES_THINKING_CLOSED;
  const std::array<ParamId,3> ids{face[2],talk,face[1]};
  const float eye_weight=facial_envelope.closed_weight();
  const std::array<bool,3> override{eye_weight>0.f,true,closed};
  const std::array<float,3> targets{10.f,float(mouth),0.f};'''
    assert text.count(old)==1
    text=text.replace(old,new)
    old='''   const float difference=override[i]?targets[i]-(observed[i]-previous):0.f;'''
    new='''   const float authored=observed[i]-previous;
   // Blend towards thinking closure; otherwise retain authored expression and
   // blink, including during answers. No reset, extra scene, or new timer.
   const float target=i==0?authored+(targets[i]-authored)*eye_weight:targets[i];
   const float difference=override[i]?target-authored:0.f;'''
    assert text.count(old)==1
    text=text.replace(old,new)
    old='''  const auto eye_policy=h.control.expression&YUKI_EYES_MASK;
  const auto mood='''
    new='''  const auto eye_policy=h.control.expression&YUKI_EYES_MASK;
  h.facial_envelope.step(eye_policy==YUKI_EYES_THINKING_CLOSED ||
    (eye_policy==YUKI_EYES_ANSWER_OPEN && !live));
  const auto mood='''
    assert text.count(old)==1
    text=text.replace(old,new)
    path.write_text(text,encoding='utf-8',newline='\n')
    save(HERE/'candidate/SOURCE_MANIFEST.json',dict(schema='aura-animation-candidate-1',base_sources=load(HERE/'baseline/OFFLINE_SOURCE_BASELINE.json')['native_sources'],
        files={p.name:sha(p) for p in dest.iterdir() if p.is_file()},changed_behavior=['smooth thinking eye closure/reopening in existing author ticks','preserve original automatic blink during audible answer'],
        control_struct_unchanged=True,strict_audio_cancel_and_stale_gate_unchanged=True,production_loaded=False))
    print('Prepared candidate; original assets, gentle motion, sound and ABI retained')
if __name__=='__main__': main()
