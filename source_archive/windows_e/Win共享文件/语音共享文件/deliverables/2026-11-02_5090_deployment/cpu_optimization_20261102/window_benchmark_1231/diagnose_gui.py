import hashlib,json,re,subprocess
from pathlib import Path
r=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,SubState,Result,ExecMainStatus,InvocationID,Job'],capture_output=True,text=True,timeout=5);assert r.returncode==0
u=dict(v.split('=',1) for v in r.stdout.splitlines() if '=' in v)
assert re.fullmatch('[0-9a-f]{32}',u['InvocationID'])
j=subprocess.run(['journalctl','_SYSTEMD_INVOCATION_ID='+u['InvocationID'],'-n','180','--no-pager','-o','cat'],capture_output=True,text=True,timeout=5);assert j.returncode==0
t=j.stdout
markers={k:k in t for k in ('ClockUnavailable','sample_rtt_exceeded','sample_too_old','invalid_sample_monotonic_order','Traceback','SyntaxError','AttributeError','NameError','ImportError','RuntimeError','ValueError','source changed','component','pinned','read_preview')}
frames=[]
for line in t.splitlines():
 m=re.search(r'File "([^"]+)", line ([0-9]+), in ([a-zA-Z0-9_<>]+)',line)
 if m:frames.append({'file':Path(m.group(1)).name,'line':int(m.group(2)),'function':m.group(3)})
print(json.dumps({'status':'GUI_FAILURE_CLASSIFIED_READONLY','unit':u,'markers':markers,'frames':frames,'journal_lines':len(t.splitlines()),'private_log_text_exported':False,'startup_sha256':hashlib.sha256(Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json').read_bytes()).hexdigest()}))
