"""Check whether existing read-only APIs already expose source-bound tracks."""
import json
import urllib.error
import urllib.request

terms=('track','target','observ','frame','capture','stamp','box','person')
def scan(port,path):
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:
            raw=r.read(262145);status=r.status
    except urllib.error.HTTPError as e:return {'http':e.code}
    if len(raw)>262144:return {'http':status,'oversize':True}
    try:value=json.loads(raw)
    except Exception:return {'http':status,'json':False,'bytes':len(raw)}
    found=[]
    def visit(obj,prefix='',depth=0):
        if depth>9:return
        if isinstance(obj,dict):
            for k,v in obj.items():
                key=str(k);name=prefix+'.'+key if prefix else key
                if any(t in key.lower() for t in terms):found.append(name)
                visit(v,name,depth+1)
        elif isinstance(obj,list) and obj:visit(obj[0],prefix+'[]',depth+1)
    visit(value)
    return {'http':status,'json':True,'bytes':len(raw),'candidate_field_paths':sorted(set(found))[:50]}
print(json.dumps({'camera_health':scan(8790,'/health'),'gui_state':scan(8783,'/api/state')},sort_keys=True))
