from common import *
if __name__=='__main__':
 # These are lifecycle implementations, freshly bound by R3 expected.json and
 # a new stage/handoff. R2 transaction intents and fingerprints are not replayed.
 for old,new in [('gui_maintenance.py','gui_lifecycle_r3.py'),('readiness.py','readiness_r3.py'),('measure_live.py','measure_live_r3.py'),('publish_animation.py','publish_r3.py'),('final_handoff_probe.py','final_probe_r3.py')]:
  text=(BASE/old).read_text(encoding='utf8')
  if old=='gui_maintenance.py':text=text.replace('avatar-R2-','avatar-R3-')
  if old=='publish_animation.py':text=text.replace('avatar-R2-','avatar-R3-').replace('ANIMATION_R2_CAS_APPLIED_GUI_STOPPED','ANIMATION_R3_CAS_APPLIED_GUI_STOPPED')
  (HERE/new).write_text(text,encoding='utf8')
 text=(BASE/'pbuffer_preview.py').read_text(encoding='utf8')
 text=text.replace("'baseline','candidate_physics'", "'baseline','candidate_physics'")
 text=text.replace("HERE/'build/libaura_yuki.so'", "HERE/'build/libaura_yuki.so'")
 # Add pose selection for both authored arm layouts, retaining all timing/math.
 text=text.replace("p.add_argument('--capture',action='store_true');", "p.add_argument('--pose',type=int,choices=(0,1),default=0);p.add_argument('--capture',action='store_true');")
 text=text.replace('0x200 if answer else 0,0,.8','0x200 if answer else 0,args.pose,.8')
 (HERE/'preview_r3.py').write_text(text,encoding='utf8')
 # Readiness only inspects the new publication in the current R3 stage.
 save(HERE/'validation/OFFLINE_HOST_UNAVAILABLE.json',dict(status='UBUNTU_NUMERIC_BUILD_HOST_UNAVAILABLE',reason='Configured SSH BindAddress192.168.137.1 unavailable; no network configuration changed',fallback='Compile the same pure C++ numerical comparator inside granted ARM build, no GPU/audio/GUI opening'))
 print('New R3 helper sources prepared; all transactions use the new R3 stage')
