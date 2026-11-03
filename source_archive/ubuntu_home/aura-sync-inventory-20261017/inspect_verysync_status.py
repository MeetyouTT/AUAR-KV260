"""Read selected Verysync state through CLI/API; redact configuration secrets."""
import hashlib
import ipaddress
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BINARY='/home/ghmd/.local/opt/verysync/verysync'
WORK=Path(__file__).resolve().parent/'verysync-status'

def cli(*args):
    p=subprocess.run([BINARY,'cli',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=12)
    if p.returncode:raise RuntimeError('Verysync CLI failed: '+str(args[:2])+' exit='+str(p.returncode))
    return json.loads(p.stdout)

def rows(value):
    if isinstance(value,list):return value
    if isinstance(value,dict):return list(value.values())
    return []

def alias(value):return hashlib.sha256(str(value).encode()).hexdigest()[:10]

def redact_address(value):
    if not isinstance(value,str):return value
    try:
        host,port=value.rsplit(':',1)
        if not ipaddress.ip_address(host.strip('[]')).is_private:return '[public address]:'+port
    except ValueError:pass
    return value

config=cli('config','dump-json')
gui=config.get('gui',{})
address=gui.get('address','127.0.0.1:8886')
if isinstance(address,str) and address.startswith(':'):address='127.0.0.1'+address
if not isinstance(address,str) or '://' in address or '/' in address:raise ValueError('Unexpected local GUI address')
host,port=address.rsplit(':',1)
if host in ('0.0.0.0','[::]','::'):host='127.0.0.1'
if not ipaddress.ip_address(host.strip('[]')).is_loopback:raise ValueError('Only the local sync API is permitted')
BASE=('https' if gui.get('useTLS') else 'http')+'://'+host+':'+port
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
key=gui.get('apiKey',gui.get('apikey',''))

def api(path,query=None):
    if query:path+='?'+urllib.parse.urlencode(query)
    request=urllib.request.Request(BASE+path,headers={'X-API-Key':key} if key else {})
    try:
        with opener.open(request,timeout=8) as reply:return json.load(reply)
    except urllib.error.HTTPError as exc:return {'api_error':'HTTP '+str(exc.code)}
    except Exception as exc:return {'api_error':type(exc).__name__}

devices=rows(config.get('devices',[]))
device_names={row.get('deviceID',row.get('deviceId')):row.get('name','') for row in devices if isinstance(row,dict)}
report={'observed_unix':time.time(),'local_api':BASE,'folders':[],
        'system':{},'connections':[],'pending_errors':[],
        'config_top_keys':sorted(config),'gui_fields':sorted(gui)}
system=cli('show','system')
report['system']={name:system.get(name) for name in ('uptime','startTime','myName','alloc','sys','goroutines') if name in system}
report['version']=cli('show','version')
connections=cli('show','connections')
report['connection_top_keys']=sorted(connections) if isinstance(connections,dict) else []
if isinstance(connections,dict):
    for identity,row in connections.get('connections',{}).items():
        if not isinstance(row,dict):continue
        report['connections'].append(dict({name:(redact_address(row.get(name)) if name=='address' else row.get(name)) for name in
            ('connected','paused','type','address','isLocal','inBytesTotal','outBytesTotal','clientVersion','startedAt') if name in row},
            peer=alias(identity),name=device_names.get(identity,'')))
    report['traffic_total']=connections.get('total',{})
try:
    errors=cli('errors','show')
    error_rows=(errors.get('errors') or []) if isinstance(errors,dict) else []
    report['pending_errors']=[{'when':row.get('when'),'message':row.get('message','')[:500]} for row in error_rows if isinstance(row,dict)]
except Exception as exc:report['error_query']=type(exc).__name__

for folder in rows(config.get('folders',[])):
    if not isinstance(folder,dict):continue
    identity=folder.get('id',folder.get('ID'))
    if not identity:continue
    summary={name:folder.get(name) for name in ('label','path','type','paused','ignorePerms','rescanIntervalS') if name in folder}
    summary['folder']=alias(identity)
    for name,path in (('status','/rest/db/status'),('ignores','/rest/db/ignores'),
                      ('errors','/rest/folder/errors'),('need','/rest/db/need')):
        value=api(path,{'folder':identity,**({'page':1,'perpage':20} if name=='need' else {})})
        if name=='status':
            summary[name]={key:val for key,val in value.items() if key not in ('deviceID','deviceId','id')}
            if isinstance(summary[name].get('remoteSequence'),dict):
                summary[name]['remoteSequence']={alias(k):v for k,v in summary[name]['remoteSequence'].items()}
        elif name=='ignores':
            ignore=value.get('ignore') or []
            summary['ignore_rules_count']=len(ignore)
            summary['pytest_cache_ignore_loaded']='.pytest_cache' in ignore
            summary['ignore_query_error']=value.get('api_error')
        elif name=='errors':
            summary['error_query_keys']=sorted(value)
            summary['errors']=[{key:row.get(key) for key in ('path','error')} for row in (value.get('errors') or [])[:20] if isinstance(row,dict)]
            if 'api_error' in value:summary['errors_api_error']=value['api_error']
        elif name=='need':
            summary['need_query_keys']=sorted(value)
            summary['needed']={group:[{key:row.get(key) for key in ('name','type','size','deleted')} for row in (value.get(group) or [])[:20] if isinstance(row,dict)]
                               for group in ('progress','queued','rest')}
            if 'api_error' in value:summary['need_api_error']=value['api_error']
    summary['remote_completion']=[]
    for peer,connection in connections.get('connections',{}).items():
        if not isinstance(connection,dict) or not connection.get('connected'):continue
        value=api('/rest/db/completion',{'folder':identity,'device':peer})
        summary['remote_completion'].append(dict({name:value.get(name) for name in
            ('completion','globalBytes','globalItems','needBytes','needItems','needDeletes','remoteState','api_error') if name in value},
            peer=alias(peer),name=device_names.get(peer,'')))
        needed=api('/rest/db/remoteneed',{'folder':identity,'device':peer,'page':1,'perpage':20})
        if isinstance(needed,dict):
            summary['remote_completion'][-1]['need_query_keys']=sorted(needed)
            summary['remote_completion'][-1]['needed_files']=[{name:row.get(name) for name in ('name','size','type') if name in row}
                for row in (needed.get('files') or [])[:20] if isinstance(row,dict)]
            if 'api_error' in needed:summary['remote_completion'][-1]['need_api_error']=needed['api_error']
    summary['important_files']=[]
    important=['共享文件夹/aura/.pytest_cache',
                     '共享文件夹/aura/scripts/start_board_asr.ps1',
                     '共享文件夹/deliverables/2026-10-17_board_asr_host_files/asr-host-complete-code-b9ac9d83fe24f179.zip']
    manifest_path=Path('/home/ghmd/Win共享文件/共享文件夹/deliverables/2026-10-17_board_asr_host_files/ASR_REQUIRED_FILES.json')
    if manifest_path.exists():
        important.extend('共享文件夹/aura/'+name for name in json.loads(manifest_path.read_text())['files'])
    for relative in dict.fromkeys(important):
        value=api('/rest/db/file',{'folder':identity,'file':relative})
        entry={'path':relative,'api_error':value.get('api_error')}
        for name in ('global','local'):
            row=value.get(name) or {}
            entry[name]={key:row.get(key) for key in ('type','size','deleted','invalid','ignored','localFlags','sequence') if key in row}
        availability=[]
        for row in value.get('availability') or []:
            peer=row.get('id',row.get('deviceID')) if isinstance(row,dict) else row
            availability.append({'peer':alias(peer),'name':device_names.get(peer,''),
                                 'from_temporary':row.get('fromTemporary') if isinstance(row,dict) else None})
        entry['availability']=availability
        summary['important_files'].append(entry)
    report['folders'].append(summary)

WORK.mkdir(parents=True,exist_ok=True)
stamp=str(int(time.time()))
target=WORK/('status-'+stamp+'.json')
target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if '--summary' in sys.argv:
    print(json.dumps({'observed_unix':report['observed_unix'],'connections':report['connections'],
        'folders':[{'path':row['path'],'state':row['status'].get('state'),
                    'errors':row['errors'],'need_total_items':row['status'].get('needTotalItems'),
                    'cache_ignore_loaded':row['pytest_cache_ignore_loaded'],'remote_completion':row['remote_completion'],
                    'important_files':[{'path':item['path'],'global_bytes':item['global'].get('size'),
                                        'available_on':[p['name'] for p in item['availability']],'error':item['api_error']}
                                       for item in row['important_files']]}
                   for row in report['folders']]},ensure_ascii=False,indent=2))
else:print(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'saved_redacted_report':str(target)},ensure_ascii=False))
