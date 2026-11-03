import collections,json,subprocess
from pathlib import Path
p=subprocess.run(['journalctl','--since','4 seconds ago','-n','250','-o','json','--no-pager'],capture_output=True,text=True,timeout=6)
groups=collections.Counter()
for line in p.stdout.splitlines():
 try:d=json.loads(line)
 except ValueError:continue
 if d.get('SYSLOG_IDENTIFIER') in ('kernel','systemd-journald'):
  m=d.get('MESSAGE','');m=m if isinstance(m,str) else str(m)
  groups[(d.get('SYSLOG_IDENTIFIER'),m[:450])]+=1
print(json.dumps({'system_messages_only':[dict(source=k[0],message=k[1],count=v) for k,v in groups.most_common(9)],
 'disk':subprocess.check_output(['df','-h','/','/run','/var/log'],text=True),
 'journal_configuration_files':[str(p) for p in Path('/etc/systemd').glob('journald.conf*')],
 'cmdline':Path('/proc/cmdline').read_text().strip(),'observer_writes':0}))
