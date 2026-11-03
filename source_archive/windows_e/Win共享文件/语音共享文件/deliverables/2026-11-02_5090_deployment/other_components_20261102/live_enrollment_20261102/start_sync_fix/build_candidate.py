"""Build one local enrollment-source candidate from the verified production bytes."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2]
baseline = OUT/'identity_dialogue_collaboration/baseline/board/identity/voice_enrollment.py'
raw = baseline.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '83796dd78c57555ea66eeb2b745a89f8b3670945a4406176cb3486111d9466b8'
source = raw.decode('utf-8')
original = source
anchor = 'from board.interaction.ui_contract import millis,validate_snapshot,identity_completion'
assert source.count(anchor) == 1
source = source.replace(anchor, anchor + ',validate_ack')
tree = ast.parse(source)
klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'VoiceEnrollment')
method = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == '_start_simple')
lines = source.splitlines(True)
replacement = '''    def _start_simple(self,current,*,is_current=lambda:True):
        epoch=self.epoch;owner=copy.deepcopy(self.owner);bound_id=''
        previous=current['modules']['identity'].get('enrollment_sampling',{}).get('session_id','')
        started=self.clock();publish_until=min(self.until,started+2.5)
        def discard():
            # Never reset/cancel a later local workflow or an unrelated token.
            if (epoch==self.epoch and self.owner==owner
                    and self.sampling_id in ('',bound_id)):
                self.reset()
        try:
            if not is_current():raise InterruptedError('Stale sampling start')
            params={'target':copy.deepcopy(self.selected_target(current))}
            if self.replace_id:params.update(replace_person_id=self.replace_id,db_version=owner[3])
            now=self.now_ms()
            command={'protocol_version':'aura-ui-1','board_boot_id':self.boot,
                'service_epoch':current['service_epoch'],'command_id':'voice-'+uuid.uuid4().hex,
                'ui_epoch':epoch,'ui_generation':0,'context':current['context'],
                'snapshot_sequence':current['sequence'],'issued_mono_ms':now,
                'deadline_mono_ms':now+2500,'action':'identity_sample_start','params':params}
            ack=self.command(command)  # Exactly once; an unknown outcome is never resent.
            accepted=validate_ack(ack,command,self.now_ms())
            if accepted['accepted'] is not True:raise ValueError('Sampling start rejected')
            # UiServices publishes a cached status about every 0.6s. Accepted
            # does not contain a sampling ID, so wait within the original command
            # window for its new, target-bound token rather than reading once.
            for _ in range(50):
                latest=validate_snapshot(self.snapshot(),self.boot,self.now_ms())
                if epoch!=self.epoch or self.owner!=owner:
                    raise InterruptedError('Sampling workflow replaced')
                actual=self.owner_of(latest)
                if (latest['source_kind']!='actual' or actual[:2]!=owner[:2]
                        or actual[3]!=owner[3] or latest['context']!=current['context']):
                    raise ValueError('Sampling source changed')
                sample=latest['modules']['identity'].get('enrollment_sampling',{})
                session_id=sample.get('session_id','')
                if session_id and session_id!=previous:
                    if sample.get('bound_target')!=owner[2]:
                        raise ValueError('Sampling target binding changed')
                    # Retain only this proved target-bound token before any later
                    # stage/current/deadline check can fail and need cancellation.
                    if self.sampling_id not in ('',session_id):
                        raise InterruptedError('Sampling token replaced')
                    self.sampling_id=bound_id=session_id
                    if not is_current():raise InterruptedError('Sampling request cancelled')
                    if self.clock()>=publish_until:raise ValueError('Sampling publication expired')
                    if actual!=owner or sample.get('stage') not in ('collect','front'):
                        raise ValueError('Sampling did not start for the original owner')
                    self.stage='sampling';self.authorized=True;self.until=started+90
                    return speech.result('sample_auto')
                if not is_current():raise InterruptedError('Sampling request cancelled')
                remaining=publish_until-self.clock()
                if remaining<=0:break
                time.sleep(min(.05,remaining))
            raise ValueError('Sampling status was not published before the original deadline')
        except InterruptedError:
            discard();raise
        except (OSError,ValueError,KeyError,TypeError,RuntimeError):
            discard();return speech.result('sample_failed')

'''
source = ''.join(lines[:method.lineno-1]) + replacement + ''.join(lines[method.end_lineno:])
anchor = "if self.stage=='authorize':return self._start_simple(current)"
assert source.count(anchor) == 1
source = source.replace(anchor, "if self.stage=='authorize':return self._start_simple(current,is_current=is_current)")
ast.parse(source)
target = HERE/'candidate/board/identity/voice_enrollment.py'
target.parent.mkdir(parents=True, exist_ok=True)
with target.open('x', encoding='utf-8', newline='\n') as handle:
    handle.write(source)
with (HERE/'CANDIDATE.diff').open('x', encoding='utf-8') as handle:
    handle.writelines(difflib.unified_diff(original.splitlines(True), source.splitlines(True),
                                         fromfile='a/board/identity/voice_enrollment.py',
                                         tofile='b/board/identity/voice_enrollment.py'))
manifest={'schema':'aura-enrollment-start-publish-sync-local-candidate-1',
    'file':'board/identity/voice_enrollment.py','before_sha256':hashlib.sha256(raw).hexdigest(),
    'after_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'production_changed':False,'start_commands_maximum':1,'publish_window_maximum_seconds':2.5,
    'sampling_timeout_extended':False,'quality_models_thresholds_or_consent_changed':False}
with (HERE/'CANDIDATE_MANIFEST.json').open('x',encoding='utf-8') as handle:
    json.dump(manifest,handle,ensure_ascii=False,indent=2);handle.write('\n')
print(json.dumps(manifest))
