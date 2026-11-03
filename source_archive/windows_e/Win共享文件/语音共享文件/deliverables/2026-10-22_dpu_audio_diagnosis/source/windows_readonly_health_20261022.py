import json,socket,time,urllib.request
out={'scope':'TCP and existing health GET only; no face/audio/text inference payloads','services':{}}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for port in (8791,8792,8795):
 row={};start=time.monotonic()
 try:
  with socket.create_connection(('192.168.50.1',port),timeout=.7):pass
  row['tcp']='connected'
  with op.open('http://192.168.50.1:%d/health'%port,timeout=1) as r:
   data=r.read(32769);assert len(data)<=32768
   value=json.loads(data)
  row['health']={k:value[k] for k in ('status','ready','backend','model','service','version') if k in value and isinstance(value[k],(str,int,float,bool,type(None)))}
 except Exception as exc:row['error_type']=type(exc).__name__
 row['elapsed_s']=time.monotonic()-start;out['services'][str(port)]=row
print(json.dumps(out))
