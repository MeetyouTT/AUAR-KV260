"""Retain the prior verified mute/watchdog/restore procedure; add audio diagnostics."""
import ast,json
from board_guard import H,capture,ssh
c=json.loads((H/'candidate.json').read_text(encoding='utf-8'));before=capture()
assert before['safe'] and before['actual_runtime']==c['runtime'] and not before['mismatches']
tree=ast.parse((H.parent/'2026-10-27_windows_portrait/muted_speech_probe.py').read_text(encoding='utf-8'))
assignment=next(node for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in node.targets))
script=ast.literal_eval(assignment.value.func.value)
old="'max_audio_lag_ms':s['portrait_offload']['max_accepted_audio_lag_ms']})"
new="'max_audio_lag_ms':s['portrait_offload']['max_accepted_audio_lag_ms'],'audio_output':s.get('audio_output',{})})"
assert old in script;script=script.replace(old,new)
old="report.update(status='PASS',speaking=summary,pan_readback_preserved=position,rows=rows)"
new="""report['audio_diagnostics']={'max_poll_gap_ms':max(r['audio_output'].get('max_poll_gap_ms',0) for r in speaking),
      'max_turn_underrun_packets':max(r['audio_output'].get('turn_underrun_packets',0) for r in speaking),
      'max_turn_late_rebases':max(r['audio_output'].get('turn_late_rebases',0) for r in speaking),
      'last_ipc':speaking[-1]['audio_output'].get('ipc',{})}
    assert report['audio_diagnostics']['max_turn_underrun_packets']==0,report['audio_diagnostics']
    assert report['audio_diagnostics']['max_poll_gap_ms']<80,report['audio_diagnostics']
    assert report['audio_diagnostics']['last_ipc'].get('nonblocking') is True
    assert not report['audio_diagnostics']['last_ipc'].get('broken_pipe',True)
    report.update(status='PASS',speaking=summary,pan_readback_preserved=position,rows=rows)"""
assert old in script;script=script.replace(old,new).replace('CANDIDATE',repr(c))
compile(script,'<muted-existing-ui>','exec')
v=json.loads(ssh('python3 -B -',script,timeout=95))
(H/'muted_live_probe.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in v.items() if key!='rows'}))
raise SystemExit(0 if v['status']=='PASS' else 1)
