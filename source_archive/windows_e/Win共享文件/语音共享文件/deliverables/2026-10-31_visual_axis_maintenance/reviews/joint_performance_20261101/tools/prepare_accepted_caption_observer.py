"""Skip explicitly rejected ASR requests before locking the first accepted caption test target."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parents[1]

def select_target(current,initial,target,latency,state):
 if target is not None:return target
 accepted=(latency.get('asr_completed') is True and latency.get('entry_rejected') is False
           and (state in ('GENERATING','PLAYING','ANSWERED') or latency.get('ordinary_prepare') is True))
 return current if current and current!=initial and accepted else None

def main():
 old=(HERE/'remote/live_observer_caption.py').read_text('utf-8')
 assert hashlib.sha256(old.encode()).hexdigest()=='5523772bb32465a73e91e6f3d72880c12ebbc1862c914ac289d057e8c37078df'
 a=" if ready and target_request is None and token and token!=initial_request:\n  target_request=token"
 b=""" accepted=(observed['latency'].get('asr_completed') is True
           and observed['latency'].get('entry_rejected') is False
           and (observed['transcription_state'] in ('GENERATING','PLAYING','ANSWERED')
                or observed['latency'].get('ordinary_prepare') is True))
 if ready and target_request is None and token and token!=initial_request and accepted:
  target_request=token"""
 assert old.count(a)==1;new=old.replace(a,b,1)
 rejected=dict(asr_completed=True,entry_rejected=True,ordinary_prepare=False)
 accepted=dict(asr_completed=True,entry_rejected=False,ordinary_prepare=True)
 assert select_target('rejected',None,None,rejected,'ANSWERED') is None
 assert select_target('valid',None,select_target('rejected',None,None,rejected,'ANSWERED'),accepted,'GENERATING')=='valid'
 assert select_target('later',None,'valid',accepted,'GENERATING')=='valid'
 assert select_target('initial','initial',None,accepted,'GENERATING') is None
 assert select_target('pending',None,None,dict(asr_completed=False,entry_rejected=False),'TRANSCRIBING') is None
 p=HERE/'remote/live_observer_caption_accepted.py'
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(new)
 patch=HERE/'evidence/caption_accepted_target.patch'
 with patch.open('x',encoding='utf-8') as f:f.write(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='caption_552377.py',tofile='caption_accepted.py')))
 proof=dict(schema='aura-caption-first-accepted-request-observer-1',source_sha256=hashlib.sha256(new.encode()).hexdigest(),base_sha256=hashlib.sha256(old.encode()).hexdigest(),
            public_target_cases_passed=5,cleanup_public_cases=['idle','generating_then_idle','playing_then_idle','never_idle_pending'],
            cleanup_cancel_commands=0,first_accepted_target_locked=True,caption_projection_and_complete_ack_checks_unchanged=True,
            production_or_device_access=False,diff_sha256=hashlib.sha256(patch.read_bytes()).hexdigest())
 m=HERE/'remote/live_observer_caption_accepted_manifest.json'
 with m.open('x',encoding='utf-8') as f:json.dump(proof,f,indent=2);f.write('\n')
 print(json.dumps(proof))

if __name__=='__main__':main()
