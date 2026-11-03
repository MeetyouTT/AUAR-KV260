import json,urllib.request
def get(url):
 with urllib.request.urlopen(url,timeout=4) as r:return json.load(r)
u=get('http://127.0.0.1:8783/api/state');rows=[]
for n,t in enumerate(u.get('turns',[])):
 m=t.get('server_metrics',{}).get('timing',{}).get('llm',{})
 rows.append({'index':n,'backend':m.get('backend'),'native_build':m.get('native_build'),'fallback':str(m.get('compact_grammar_fallback',''))[:180],'preparation_ms':m.get('request_preparation_ms')})
h=get('http://192.168.50.1:8792/health')
print(json.dumps({'routes':rows,'service_revision':h.get('service_revision'),'source_fingerprint':h.get('source_fingerprint'),'latency_options':h.get('latency_options'),'startup_warmup_complete':h.get('startup_warmup_complete')}))
