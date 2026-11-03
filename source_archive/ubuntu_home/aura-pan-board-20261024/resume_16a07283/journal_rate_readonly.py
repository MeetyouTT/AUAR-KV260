import collections,hashlib,json,subprocess,time
start=time.monotonic()
p=subprocess.run(['journalctl','--since','8 seconds ago','-n','600','-o','json','--no-pager'],capture_output=True,text=True,timeout=8)
counts=collections.Counter();templates=collections.Counter();examples={};timestamps=[]
keywords=('gst','gstreamer','xv','gtk','broken pipe','assertion','failed','error','warning','traceback','console','repeated')
for line in p.stdout.splitlines():
 try:d=json.loads(line)
 except ValueError:continue
 unit=d.get('_SYSTEMD_UNIT','');identifier=d.get('SYSLOG_IDENTIFIER',d.get('_COMM',''))
 message=d.get('MESSAGE','');message=message if isinstance(message,str) else str(message)
 key=(unit,identifier);counts[key]+=1
 normalized=message[:200];h=hashlib.sha256(normalized.encode()).hexdigest()[:12]
 templates[(unit,identifier,h)]+=1
 if any(k in message.lower() for k in keywords):examples[h]=message[:350]
 ts=d.get('__REALTIME_TIMESTAMP')
 if ts and str(ts).isdigit():timestamps.append(int(ts))
print(json.dumps({'returncode':p.returncode,'elapsed_s':round(time.monotonic()-start,3),'entries':sum(counts.values()),
 'observed_span_s':round((max(timestamps)-min(timestamps))/1e6,3) if timestamps else None,
 'producers':[dict(unit=k[0],identifier=k[1],count=v) for k,v in counts.most_common(12)],
 'repeated_templates':[dict(unit=k[0],identifier=k[1],message_hash=k[2],count=v,diagnostic_example=examples.get(k[2])) for k,v in templates.most_common(12)],
 'journal_unit':subprocess.check_output(['systemctl','show','systemd-journald.service','-p','MainPID','-p','NRestarts','-p','Result'],text=True),
 'scope':'bounded last8s/600entries; only error-related excerpts; no config changes or actuator writes'}))
