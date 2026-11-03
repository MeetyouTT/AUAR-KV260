from pathlib import Path
import json
root=Path(__file__).parent/'reference_controlled'
for mode,tag in (('rebuilt_combo','probe-combo'),('rebuilt_no_combo','probe-no-combo')):
    rig=json.loads((root/mode/'rig.json').read_text(encoding='utf8'))
    rig['expressions']['probe']={**rig['expressions']['normal'],'body_UD':30,'body_LR':-25,'head_UD':20,'head_LR':15}
    rig['idleTimeline']='';rig['poseTimelines']={'0':'','1':''}
    (root/(tag+'-rig.json')).write_text(json.dumps(rig,ensure_ascii=True),encoding='utf8')
print('EXTREME_PAIR_RIGS_READY')
