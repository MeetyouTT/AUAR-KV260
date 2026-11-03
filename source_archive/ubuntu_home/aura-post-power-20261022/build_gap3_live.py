"""Pin gap recorder payloads into the reviewed restored short-trial helper."""
import ast,base64,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CANDIDATE=Path('/home/ghmd/aura-yunet-retry-gap-audit-20261023')
old=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_combined_live_v4_20261022.py')
source=old.read_text();assert hashlib.sha256(source.encode()).hexdigest()=='ad0e90471ce14261486402968c69504d6f750c51ac9521cc075453467953b3bb'
tree=ast.parse(source)
constants={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body
           if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)
           and n.targets[0].id in ('RETRY_PAYLOAD','RETRY_HASHES')}
files={name:(CANDIDATE/name).read_bytes() for name in constants['RETRY_PAYLOAD']}
hashes={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
payload={name:base64.b64encode(gzip.compress(data,mtime=0)).decode() for name,data in files.items()}
lines=source.splitlines(keepends=True)
for node in sorted((n for n in tree.body if isinstance(n,ast.Assign)
                    and isinstance(n.targets[0],ast.Name) and n.targets[0].id in constants),
                   key=lambda n:n.lineno,reverse=True):
    name=node.targets[0].id
    lines[node.lineno-1:node.end_lineno]=[name+'='+repr(payload if name=='RETRY_PAYLOAD' else hashes)+'\n']
source=''.join(lines)
def replace(old,new):
    global source
    assert source.count(old)==1,(old[:90],source.count(old))
    source=source.replace(old,new)
replace("assert checked_result['run']==82","assert checked_result['run']==85")
replace("/home/root/aura-post-power-20261022/light2-preflight/9b7373edd1316069/report.json",
        "/home/root/aura-post-power-20261022/gap3-preflight/99e52c483594cd2f/report.json")
replace("light['schema_version']=='aura-face-freshness-light-2'", "light['schema_version']=='aura-face-freshness-light-3'")
replace('YUNET_RETRY_LIGHT_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED','YUNET_RETRY_GAP3_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED')
replace("('cbee206f503bab01-'+str(os.getpid()))", "('gap3-'+str(os.getpid()))")
replace('postpower-combined-launches','postpower-gap3-launches')
source=source.replace('aura-postpower-combined-live-','aura-postpower-gap3-live-')
replace("        report['freshness_final']=light", """        report['freshness_final']=light
        records=light['gap_records']
        assert light['gap_record_capacity']==32 and len(records)<=32
        assert len(records)+light['gap_records_dropped']==light['counters']['observed_gap_intervals']
        assert all(type(value) is int and value>=0 for row in records for value in row.values())
        report['gap_record_retention_passed']=True""")
newtree=ast.parse(source)
def final(t):
    main=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    guarded=next(n for n in main.body if isinstance(n,ast.Try) and n.finalbody)
    return ast.dump(ast.Module(body=guarded.finalbody,type_ignores=[]))
assert final(tree)==final(newtree),'Rollback must stay identical'
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_gap3_live_20261023.py')
assert not target.exists();target.write_text(source)
result={'helper':str(target),'sha256':hashlib.sha256(source.encode()).hexdigest(),
        'sources':hashes,'tests':85,'seconds':120,'rollback_finalizer_ast_unchanged':True,
        'cost_helper_sha256':'99e52c483594cd2fcb9921b2d8aeda6f955bafbc429aa43070e1955ca55af89f'}
(ROOT/'gap3-live-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='sources'}))
