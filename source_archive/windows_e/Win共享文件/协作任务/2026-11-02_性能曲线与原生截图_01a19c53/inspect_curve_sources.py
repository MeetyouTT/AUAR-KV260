from pathlib import Path
import json

base=Path('E:/Win共享文件/语音共享文件/deliverables')
roots=[base/'2026-10-21_dpu_vision_start'/'evidence',base/'2026-10-21_dpu_live_baseline'/'evidence']

def describe(v,p='',out=None):
    if out is None:out=[]
    if isinstance(v,dict):
        for k,x in v.items():describe(x,p+'/'+k,out)
    elif isinstance(v,list) and len(v)>3:
        first=next((x for x in v if x is not None),None)
        if isinstance(first,dict):
            out.append({'path':p,'length':len(v),'item_keys':list(first),'numeric_fields':{k:x for k,x in first.items() if isinstance(x,(float,int)) and not isinstance(x,bool)}})
        elif isinstance(first,(int,float)):out.append({'path':p,'length':len(v),'type':'numeric'})
    return out

for root in roots:
    for path in root.glob('*.json'):
        try: d=json.loads(path.read_text(encoding='utf-8'))
        except Exception:continue
        arrays=describe(d)
        if arrays:print(json.dumps({'file':str(path),'top_keys':list(d)[:15] if isinstance(d,dict) else [],'arrays':arrays},ensure_ascii=False))
