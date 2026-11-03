import ast
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent;PREVIOUS=HERE/'py39_fix';NEW=HERE/'recovery_stability_20261102_v3'
assert not NEW.exists();NEW.mkdir()
shutil.copytree(HERE/'before',NEW/'before');shutil.copytree(PREVIOUS/'candidate',NEW/'candidate')
def edit(name,changes):
    p=NEW/'candidate'/name;s=p.read_text(encoding='utf-8')
    for old,new in changes:
        assert s.count(old)==1,(name,old,s.count(old));s=s.replace(old,new,1)
    ast.parse(s);p.write_text(s,encoding='utf-8',newline='')
edit('continuous_face_control.py',[
    ('    left_target_center_ratio: Optional[float] = None\n','    left_target_center_ratio: Optional[float] = None\n    rearm_stability_ms: int = 0\n'),
    ('        left=self.left_target_center_ratio\n',
     "        if type(self.rearm_stability_ms) is not int or not 0<=self.rearm_stability_ms<=500:\n            raise ValueError('Rearm stability must be an integer in 0..500ms')\n        left=self.left_target_center_ratio\n")])
helper='''    def reset_rearm_stability_progress(self):
        gate=self.rearm_stability_gate
        if gate is not None:
            gate.update(context=None,last_source=None,first_source_ms=None,first_received_ms=None,
                        distinct_sources=0,new_detection_seen=False,stable_source_ms=0,stable_wall_ms=0)

    def rearm_stability_ready(self,now_ms):
        gate=self.rearm_stability_gate
        if gate is None:return True
        c=self.controller
        # Only observe()'s newly admitted actual images count. This gate has
        # no source authority, hardware reference, lease or actuator state.
        if c.source is None or not c.new_source:return False
        if gate['context']!=c.context:
            self.reset_rearm_stability_progress();gate['context']=c.context
        source=c.source
        if gate['last_source'] is not None and (source[0]<=gate['last_source'][0] or source[1]<=gate['last_source'][1]):
            return False
        if gate['first_source_ms'] is None:
            gate['first_source_ms']=source[1];gate['first_received_ms']=now_ms
        gate['last_source']=source;gate['distinct_sources']+=1
        gate['stable_source_ms']=source[1]-gate['first_source_ms']
        gate['stable_wall_ms']=now_ms-gate['first_received_ms']
        gate['new_detection_seen']=(gate['new_detection_seen'] or
            type(c.anchor_stamp) is int and c.anchor_stamp>gate['interrupted_anchor_ms'])
        if (gate['distinct_sources']>=3 and gate['stable_source_ms']>=self.config.rearm_stability_ms
                and gate['stable_wall_ms']>=self.config.rearm_stability_ms and gate['new_detection_seen']):
            self.rearm_stability_passes+=1;self.rearm_stability_gate=None
            return True
        self.rearm_stability_waits+=1
        self.state='CONFIRMING';self.reason='WAITING_FOR_STABLE_REARM'
        return False

'''
edit('continuous_session.py',[
    ('        self.recenter_intent=None\n        self.brief_face_gap=False',
     '        self.recenter_intent=None\n        self.rearm_stability_gate=None\n        self.rearm_stability_waits=self.rearm_stability_passes=0\n        self.brief_face_gap=False'),
    ('    def status(self):\n',helper+'    def status(self):\n'),
    ("         pwm_output_started=self.epoch_output_started,\n",
     "         pwm_output_started=self.epoch_output_started,\n         rearm_stability_ms=self.config.rearm_stability_ms,rearm_stability_gate=(dict(self.rearm_stability_gate) if self.rearm_stability_gate is not None else None),\n         rearm_stability_waits=self.rearm_stability_waits,rearm_stability_passes=self.rearm_stability_passes,\n"),
    ('    def stop_segment(self,reason,*,normal=False):\n        self.retain_recenter_intent(reason)\n',
     '''    def stop_segment(self,reason,*,normal=False):
        previous=self.controller;had_output=self.epoch_output_started
        stop_details=dict(trigger_side=previous.recenter_trigger_side,
            target_center_ratio=previous.recenter_target_center_ratio,
            endpoint_us=self.current.get('target_us'),had_output=had_output,
            original_authority_deadline_ms=previous.authority_deadline_ms)
        if (self.config.hardware_slew_recenter and self.config.rearm_stability_ms
                and self.active and reason in RECENTER_RESUMABLE_REASONS):
            self.rearm_stability_gate=dict(reason=reason,interrupted_mono_ms=round(self.clock()*1000),
                interrupted_anchor_ms=previous.anchor_stamp if type(previous.anchor_stamp) is int else -1)
            self.reset_rearm_stability_progress()
        self.retain_recenter_intent(reason)
'''),
    ("self.segment_start=None;self.state='MONITORING';self.note(reason)\n",
     "self.segment_start=None;self.state='MONITORING';self.note(reason,emitted_width_us=self.current['width_us'],**stop_details)\n"),
    ('    def disconnected(self):\n        self.rearm.reset()\n',
     '    def disconnected(self):\n        self.reset_rearm_stability_progress()\n        self.rearm.reset()\n'),
    ('        if self.controller.stopped:\n            reason=self.controller.reason\n',
     '        if self.controller.stopped:\n            self.reset_rearm_stability_progress()\n            reason=self.controller.reason\n'),
    ("        if not value['new_source']:\n",
     "        if not value['new_source']:\n            if isinstance(packet,dict) and packet.get('state')!='READY':self.reset_rearm_stability_progress()\n"),
    ("            if not value['edge'] and not prearm:return self.status()\n",
     "            if not value['edge'] and not prearm:return self.status()\n            if not self.rearm_stability_ready(round(now*1000)):return self.status()\n")])
edit('run_face_motion.py',[
    ("    p.add_argument('--left-target-center-ratio',type=float,default=None)\n",
     "    p.add_argument('--left-target-center-ratio',type=float,default=None)\n    p.add_argument('--rearm-stability-ms',type=int,default=0)\n"),
    ('left_target_center_ratio=a.left_target_center_ratio,center_tolerance_ratio=.03)',
     'left_target_center_ratio=a.left_target_center_ratio,rearm_stability_ms=a.rearm_stability_ms,center_tolerance_ratio=.03)'),
    ("        'left_target_center_ratio':config.left_target_center_ratio,\n",
     "        'left_target_center_ratio':config.left_target_center_ratio,\n        'rearm_stability_ms':config.rearm_stability_ms,'rearm_stability_minimum_distinct_sources':3,\n        'rearm_stability_requires_new_detection':True,\n")])
for name in ('test_left_episode.py','run_pure_suite.py'):
    s=(PREVIOUS/name).read_text(encoding='utf-8')
    if name=='test_left_episode.py':s=s.replace("if k!='left_target_center_ratio'","if k not in ('left_target_center_ratio','rearm_stability_ms')")
    (NEW/name).write_text(s,encoding='utf-8')
review=json.loads((PREVIOUS/'INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
review.update(schema='aura-left-stop40-rearm-stability-source-review-3',reviewer='primary continuation source review',
    status='STATIC_SOURCE_PASS_PENDING_PURE_TESTS_NOT_PUBLISHED',
    change='Opt-in 150ms/3 distinct admitted-image recovery gate plus new detection anchor after protective interruption; no source authority or TTL change')
for r in review['records']:
    r['after']=hashlib.sha256((NEW/'candidate'/r['file']).read_bytes()).hexdigest();r['unchanged']=r['before']==r['after']
assert sum(not r['unchanged'] for r in review['records'])==3
(NEW/'INDEPENDENT_REVIEW.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
print(json.dumps({r['file']:r['after'] for r in review['records'] if not r['unchanged']},indent=2))
