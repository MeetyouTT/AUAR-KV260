"""Exercise exact temporary cleanup AST against public generating/playing/idle states."""
from pathlib import Path
import ast,difflib,hashlib,json,time
from types import SimpleNamespace as NS
HERE=Path(__file__).resolve().parents[1]

def main():
 path=HERE/'tools/start_live_one_turn.py';text=path.read_text('utf-8');tree=ast.parse(text)
 source=next(n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='REMOTE' for t in n.targets))
 fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='settle_and_pause_after_observation')
 cases=[]
 for mode in ('idle','generating_then_idle','playing_then_idle','never_idle'):
  now=NS(value=0.);calls=[];reads=NS(n=0)
  def get_json(port,url):
   reads.n+=1;active=mode=='never_idle' or mode!='idle' and reads.n<4
   playing=active and mode=='playing_then_idle'
   return dict(playing=playing,phase='SPEAKING' if playing else 'THINKING' if active else 'IDLE',
               local_transcription=dict(state='PLAYING' if playing else 'GENERATING' if active else 'IDLE'),handsfree_dialogue=dict(enabled=True))
  def sleep(dt):now.value+=dt
  ns=dict(time=NS(monotonic=lambda:now.value,sleep=sleep),get_json=get_json,ui_command=calls.append)
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<exact-public-cleanup-ast>','exec'),ns)
  result=ns['settle_and_pause_after_observation']()
  assert calls==([] if mode=='never_idle' else [dict(type='conversation_toggle')])
  assert all(c.get('type')!='event' for c in calls)
  if mode=='never_idle':assert result['status']=='ANSWER_STILL_ACTIVE_CLEANUP_PENDING'
  cases.append(dict(case=mode,passed=True,reads=reads.n,pause_commands=len(calls),cancel_commands=0))
 old="""one_complete=bool(live_ns.get('completed'))
# Main chat requested a pause immediately after each target's full ACK.
try:
 v=get_json(8783,'/api/state')
 if v.get('handsfree_dialogue',{}).get('enabled') is True:ui_command(dict(type='conversation_toggle'))
 if not one_complete and (v.get('playing') is True or v.get('phase')!='IDLE'):ui_command(dict(type='event',event='cancel'))
except Exception as exc:
 print(json.dumps(dict(kind='cleanup_error',error_class=type(exc).__name__)),flush=True)
"""
 start=source.index('one_complete=bool');end=source.index('end=time.monotonic()+8',start);new=source[start:end]
 patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='previous_cleanup_excerpt',tofile='graceful_cleanup_excerpt'))
 diff_path=HERE/'evidence/graceful_cleanup_minimal.patch'
 with diff_path.open('x',encoding='utf-8') as f:f.write(patch)
 proof=dict(schema='aura-public-graceful-observer-cleanup-1',passed=True,tests=cases,device_access=False,
            wrapper_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),observer_caption_sha256=hashlib.sha256((HERE/'remote/live_observer_caption.py').read_bytes()).hexdigest(),
            diff_scope='Cleanup excerpt only; original full executable source remains bound by the prior trial source hash.',
            diff_sha256=hashlib.sha256(diff_path.read_bytes()).hexdigest(),sample_window_seconds=180,cleanup_grace_seconds=120,
            pending_never_claimed_paused=True,production_modified=False)
 output=HERE/'evidence'/('graceful_live_cleanup_exact_ast_'+str(time.time_ns())+'.json')
 with output.open('x',encoding='utf-8') as f:json.dump(proof,f,indent=2);f.write('\n')
 print(json.dumps(dict(evidence=str(output),**proof)))

if __name__=='__main__':main()
