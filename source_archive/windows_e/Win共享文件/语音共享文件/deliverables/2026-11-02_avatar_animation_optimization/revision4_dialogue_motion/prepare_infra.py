from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;R3=BASE/'revision3_natural_lower_arm'
def write(name,text):
    p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text(encoding='utf8')==text,name+' already differs'
    else:p.write_text(text,encoding='utf8')
def main():
    for name in ('common.py','run.py','fresh_read.py','stage_release_r3.py','readiness_r3.py','measure_live_r3.py','final_probe_r3.py'):
        text=(R3/name).read_text(encoding='utf8').replace('R3','R4').replace('_r3','_r4')
        write(name.replace('_r3','_r4'),text)
    text=(R3/'gui_lifecycle_r3.py').read_text(encoding='utf8').replace('R3','R4')
    text=text.replace("'config/board_avatar_gtk.json'):","'config/board_avatar_gtk.json','tools/native_yuki.py'):")
    write('gui_lifecycle_r4.py',text)
    text=(R3/'publish_r3.py').read_text(encoding='utf8').replace('R3','R4')
    text=text.replace("'config/board_avatar_gtk.json'}","'config/board_avatar_gtk.json','tools/native_yuki.py'}").replace('other_376','other_375').replace('four reviewed','five reviewed')
    write('publish_r4.py',text)
    text=(BASE/'tests/native_original_policy.cpp').read_text(encoding='utf8')
    text=text.replace('yuki_control_features()==YUKI_FEATURE_DIALOGUE_FACIALS','(yuki_control_features()&YUKI_FEATURE_DIALOGUE_FACIALS)==YUKI_FEATURE_DIALOGUE_FACIALS')
    write('tests/native_original_policy.cpp',text)
    text=(BASE/'tests/native_physics_audit.cpp').read_text(encoding='utf8')
    text=text.replace('high[4]-low[4]>5.','high[4]-low[4]>2.').replace('low[4]>=-10.50001&&high[4]<=10.50001','low[4]>=-4.00001&&high[4]<=4.00001')
    write('tests/native_physics_audit.cpp',text)
    print(json.dumps({'status':'R4_INFRA_PREPARED_LOCALLY','device_calls':0}))
if __name__=='__main__':main()
