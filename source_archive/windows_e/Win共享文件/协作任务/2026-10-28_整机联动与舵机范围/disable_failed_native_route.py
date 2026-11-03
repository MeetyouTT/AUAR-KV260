"""Preview/apply one reversible voice option; does not stop or start services."""
import argparse,datetime,hashlib,json,os
from pathlib import Path

def update(path,apply=False):
    path=Path(path).resolve(strict=True)
    if path.name!='voice_latency.json':raise ValueError('Expected voice_latency.json')
    before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
    if not isinstance(data,dict) or any(type(v) is not bool for v in data.values()):raise ValueError('Expected boolean voice option object')
    if 'compact_grammar' not in data:raise ValueError('No current compact_grammar option')
    digest=hashlib.sha256(before).hexdigest();result={'path':str(path),'before_sha256':digest,'before_compact_grammar':data['compact_grammar'],'after_compact_grammar':False,'applied':False,'service_restarted':False}
    if not apply or data['compact_grammar'] is False:return result
    data['compact_grammar']=False
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=path.with_name('voice_latency.before-native-disable-'+stamp+'.json')
    with backup.open('xb') as f:f.write(before)
    temporary=path.with_name(path.name+'.native-disable-'+stamp+'.tmp')
    with temporary.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    if path.read_bytes()!=before:
        temporary.unlink();raise RuntimeError('Configuration changed concurrently; original retained')
    os.replace(temporary,path)
    actual=json.loads(path.read_text(encoding='utf-8-sig'));assert actual==data
    result.update(applied=True,backup=str(backup),after_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path(__file__).resolve().parents[2]/'语音共享文件/aura/config/voice_latency.json')
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    print(json.dumps(update(args.config,args.apply),ensure_ascii=False,indent=2))
