from inspect_baseline import *

def main():
    root=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/animation_thinking_collaboration'
    before=HERE/'baseline/actual_native';before.mkdir(parents=True,exist_ok=True)
    dst=HERE/'candidate_physics/native';dst.mkdir(parents=True,exist_ok=True)
    for name in ('yuki_host.cpp','yuki_host.h'):
        p=root/'candidate/native'/name
        shutil.copyfile(p,before/name);shutil.copyfile(p,dst/name)
    assert sha(before/'yuki_host.cpp')=='ac91dc8a56024459a033163c198557f65effb32f6b4b3e68068425b518460c0e'
    receipt=load(root/'ACTUAL_NATIVE_BUILD_1793456935427236300.json')
    assert receipt['result']['library_sha256']=='b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2'
    save(HERE/'baseline/ACTUAL_LIBRARY_SOURCE_LINEAGE.json',dict(status='EXACT_SELECTED_B243_SOURCE_LINEAGE_RECONCILED',native_source_sha256=sha(before/'yuki_host.cpp'),selected_library_sha256=receipt['result']['library_sha256'],historical_build_receipt=str(root/'ACTUAL_NATIVE_BUILD_1793456935427236300.json'),fresh_device_receipt='FRESH_DEVICE_READ.json',unused_e2_source='Earlier minimal_motion_v3 was never the selected b243 library; baseline/native and eye candidate retained as unused exploration only'))
    p=dst/'yuki_host.cpp';s=p.read_text()
    s=s.replace('#include "gles2_renderer.hpp"','#include "gles2_renderer.hpp"\n#include "secondary_motion.hpp"',1)
    s=s.replace(' VariableSourceId facial_source{};',' VariableSourceId facial_source{};\n VariableSourceId secondary_source{};\n std::array<ParamId,6> secondary_ids{};\n aura_yuki::SecondaryMotion secondary_motion;',1)
    s=s.replace('  const std::array<VariableSourceDefinition,1> sources{{','  aura_yuki::bind_arm_swing(imported.asset);\n  const std::array<VariableSourceDefinition,2> sources{{',1)
    s=s.replace('{"aura_dialogue_face",{"face_eye_open","face_talk","face_mouth"}}','{"aura_dialogue_face",{"face_eye_open","face_talk","face_mouth"}},\n   {"aura_secondary_motion",{"head_LR","head_slant","body_LR","body_slant","aura_arm_left","aura_arm_right"}}',1)
    anchor='  if(!facial_source.valid())throw std::runtime_error("Yuki dialogue facial source missing");'
    assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'''
  secondary_source=program->animation().find_variable_source("aura_secondary_motion");
  if(!secondary_source.valid())throw std::runtime_error("Secondary motion source missing");
  for(std::size_t i=0;i<secondary_ids.size();++i){
   secondary_ids[i]=scene.find_variable(aura_yuki::SecondaryMotion::names[i]);
   if(!secondary_ids[i].valid())throw std::runtime_error("Secondary motion parameter missing");
  }''',1)
    anchor='  const bool live=h.answer_live();'
    assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'''
  const bool thinking=(h.control.expression&YUKI_EYES_MASK)!=YUKI_EYES_AUTHORED;
  const auto movement=h.secondary_motion.step(live?1:thinking?2:0);
  // Apply before the existing geometry/physics tick. Inertial arm state and
  // original hair/parts solvers survive every conversation/state change.
  for(std::size_t i=0;i<movement.size();++i){
   const auto result=h.instance->transition_difference(h.secondary_source,h.secondary_ids[i],movement[i]);
   if(!result)return result;
  }''',1)
    anchor='  checked(instance->advance(elapsed,{},AuthorTickHandler{this,author}));'
    assert s.count(anchor)==1
    s=s.replace(anchor,'''  PhysicsInputs physical;
  physical.hair_amplitude=1.35f;physical.parts_amplitude=1.4f;
  checked(instance->advance(elapsed,physical,AuthorTickHandler{this,author}));''',1)
    p.write_text(s,encoding='utf8',newline='\n')
    tests=HERE/'tests';tests.mkdir(exist_ok=True)
    test=(root/'tests/native_eye_gate.cpp').read_text(encoding='utf8').replace('#include "../candidate/native/yuki_host.cpp"','#include "yuki_host.cpp"')
    (tests/'native_original_policy.cpp').write_text(test,encoding='utf8')
    save(HERE/'candidate_physics/SOURCE_MANIFEST.json',dict(schema='aura-physics-arm-animation-1',baseline_source=sha(before/'yuki_host.cpp'),baseline_library=receipt['result']['library_sha256'],files={x.name:sha(x) for x in dst.iterdir() if x.is_file()},original_model_and_textures_unchanged=True,original_eye_mouth_audio_owner_policies_unchanged=True,production_loaded=False))
    print('Prepared physical secondary motion against actual b243 baseline')
if __name__=='__main__':main()
