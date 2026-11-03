"""Retain the original follower; latch a distinct target for left episodes."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
BEFORE=HERE/'before';AFTER=HERE/'candidate'
assert not AFTER.exists();shutil.copytree(BEFORE,AFTER)
changes={}
def patch(name,replacements):
    p=BEFORE/name;source=p.read_text(encoding='utf-8')
    for old,new,count in replacements:
        assert source.count(old)==count,(name,old,source.count(old))
        source=source.replace(old,new)
    ast.parse(source)
    (AFTER/name).write_bytes(source.encode('utf-8'))
    changes[name]={'before':hashlib.sha256(p.read_bytes()).hexdigest(),
                   'after':hashlib.sha256((AFTER/name).read_bytes()).hexdigest()}

patch('continuous_face_control.py',[
    ('    target_center_ratio: float = .5\n','    target_center_ratio: float = .5\n    left_target_center_ratio: float | None = None\n',1),
    ("            raise ValueError('Valid recenter mode and central band inside trigger lines required')\n",
     "            raise ValueError('Valid recenter mode and central band inside trigger lines required')\n"
     "        left=self.left_target_center_ratio\n"
     "        if left is not None and (type(left) not in (int,float) or not math.isfinite(left)\n"
     "                or not 0<left<1 or (self.recenter_on_edge and not\n"
     "                    self.left_ratio<left-self.center_tolerance_ratio<left+self.center_tolerance_ratio<self.right_ratio)):\n"
     "            raise ValueError('Valid left stop target inside trigger lines required')\n",1),
    ("        self.recenter_direction=0;self.recenter_phase='WAITING_TRIGGER'\n",
     "        self.recenter_direction=0;self.recenter_phase='WAITING_TRIGGER'\n"
     "        self.reset_recenter_target()\n\n"
     "    def reset_recenter_target(self):\n"
     "        self.recenter_trigger_side=0\n"
     "        self.recenter_target_center_ratio=self.config.target_center_ratio\n",1),
    ("'target_center_ratio':self.config.target_center_ratio,'target_center':self.config.target_center_ratio,",
     "'target_center_ratio':self.recenter_target_center_ratio,'target_center':self.recenter_target_center_ratio,\n"
     "                'recenter_trigger_side':self.recenter_trigger_side,\n"
     "                'configured_target_center_ratio':self.config.target_center_ratio,\n"
     "                'configured_left_target_center_ratio':self.config.left_target_center_ratio,",1),
    ('        self.raw_left_ratio=previous.raw_left_ratio\n',
     '        self.raw_left_ratio=previous.raw_left_ratio\n'
     '        self.recenter_trigger_side=previous.recenter_trigger_side\n'
     '        self.recenter_target_center_ratio=previous.recenter_target_center_ratio\n',1),
    ('                        target=self.config.target_center_ratio\n',
     '                        target=self.recenter_target_center_ratio\n',1),
    ('        c=self.config\n        crossed=',
     '        c=self.config\n'
     '        if not self.recenter_active and not inside:\n'
     '            self.recenter_trigger_side=-1 if left_outside else 1\n'
     '            self.recenter_target_center_ratio=(c.left_target_center_ratio\n'
     '                if left_outside and c.left_target_center_ratio is not None else c.target_center_ratio)\n'
     '        target=self.recenter_target_center_ratio\n        crossed=',1),
])
p=AFTER/'continuous_face_control.py';source=p.read_text(encoding='utf-8')
a=source.index('    def recenter_decision(');b=source.index('    def single_pass_decision(',a)
body=source[a:b];assert body.count('c.target_center_ratio')==8
# The first reference is the explicit right/default selection. All following
# completion/distance decisions use the latched episode target.
first=body.index('else c.target_center_ratio')+len('else c.target_center_ratio')
body=body[:first]+body[first:].replace('c.target_center_ratio','target')
source=source[:a]+body+source[b:]
a=source.index('    def single_pass_decision(');body=source[a:]
assert body.count('c.target_center_ratio')==2
body=body.replace('        c=self.config\n','        c=self.config\n        target=self.recenter_target_center_ratio\n',1)
body=body.replace('c.target_center_ratio','target');source=source[:a]+body
ast.parse(source);p.write_bytes(source.encode('utf-8'));changes[p.name]['after']=hashlib.sha256(p.read_bytes()).hexdigest()

patch('continuous_session.py',[
    ("original_side=c.recenter_direction,phase=c.recenter_phase)",
     "original_side=c.recenter_direction,phase=c.recenter_phase,\n"
     "                                  trigger_side=c.recenter_trigger_side,target_center_ratio=c.recenter_target_center_ratio)",1),
    ('self.controller.recenter_active=False;return True',
     'self.controller.recenter_active=False;self.controller.reset_recenter_target();return True',3),
    ('        self.controller.recenter_active=True;self.controller.recenter_completed=False\n',
     '        self.controller.recenter_active=True;self.controller.recenter_completed=False\n'
     "        self.controller.recenter_trigger_side=intent.get('trigger_side',0)\n"
     "        self.controller.recenter_target_center_ratio=intent.get('target_center_ratio',self.config.target_center_ratio)\n",1),
    ('target_center_ratio=self.config.target_center_ratio,',
     'target_center_ratio=self.controller.recenter_target_center_ratio,',1),
])
patch('run_face_motion.py',[
    ("    p.add_argument('--target-center-ratio',type=float,default=.5)\n",
     "    p.add_argument('--target-center-ratio',type=float,default=.5)\n"
     "    p.add_argument('--left-target-center-ratio',type=float,default=None)\n",1),
    ('target_center_ratio=a.target_center_ratio,center_tolerance_ratio=.03)',
     'target_center_ratio=a.target_center_ratio,left_target_center_ratio=a.left_target_center_ratio,center_tolerance_ratio=.03)',1),
    ("'recenter_on_edge':config.recenter_on_edge,'target_center_ratio':config.target_center_ratio,",
     "'recenter_on_edge':config.recenter_on_edge,'target_center_ratio':config.target_center_ratio,\n"
     "        'left_target_center_ratio':config.left_target_center_ratio,",1),
])
assert len(changes)==3
(HERE/'PATCH_REVIEW.json').write_text(json.dumps({'changes':changes,'remaining_22_files_unchanged':True,
    'left_stop_target':.40,'right_stop_target':.45,'tolerance':.03,'trigger_settings_changed':False,
    'hardware_slew_and_source_deadlines_changed':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps(changes))
