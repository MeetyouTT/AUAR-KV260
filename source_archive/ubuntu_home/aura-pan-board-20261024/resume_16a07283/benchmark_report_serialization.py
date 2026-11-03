import io,json,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:m=json.load(f)['manual_pan']
p=Path(m['face_follow']['report']);raw=p.read_bytes();report=json.loads(raw)
measurements=[]
for name,encode in [('current_json_dump_indent2',lambda:json.dump(report,io.StringIO(),indent=2)),
                    ('compact_json_dumps',lambda:json.dumps(report,separators=(',',':'))),
                    ('c_encoder_indent2',lambda:json.dumps(report,indent=2))]:
 values=[]
 for _ in range(3):
  start=time.monotonic();encode();values.append(round((time.monotonic()-start)*1000,3))
 measurements.append({'method':name,'elapsed_ms':values})
print(json.dumps({'report_bytes':len(raw),'trace_entries':len(report.get('observation_trace',[])),
 'measurements':measurements,'scope':'serialization only, separate observer process, no MMIO or motor writes'}))
