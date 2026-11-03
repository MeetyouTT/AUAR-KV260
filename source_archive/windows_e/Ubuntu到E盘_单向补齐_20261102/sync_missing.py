"""Read-only Ubuntu inventory and create-only Windows receive, with audit logs."""
import base64
import concurrent.futures
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import tempfile

AUDIT = Path(__file__).resolve().parent
DEST = Path('E:/Win共享文件')
SOURCE = '/home/ghmd/Win共享文件'
HOST = 'aura-ubuntu'

SCAN_CODE = r'''
import os,sys,json,stat,time
root=sys.argv[1]
records=[]; errors=[]; excluded=[]; stack=[('',root)]
started=time.time()
while stack:
 rel,folder=stack.pop()
 try:
  with os.scandir(folder) as it:
   entries=list(it)
 except OSError as e:
  errors.append({'path':rel,'error':str(e)}); continue
 for e in entries:
  p=rel+'/'+e.name if rel else e.name
  if e.name=='.verysync':
   excluded.append({'path':p,'reason':'sync_internal_metadata'}); continue
  try:
   s=e.stat(follow_symlinks=False)
   link=stat.S_ISLNK(s.st_mode) or bool(getattr(s,'st_file_attributes',0)&0x400)
   typ='l' if link else 'd' if stat.S_ISDIR(s.st_mode) else 'f' if stat.S_ISREG(s.st_mode) else 'o'
   rec={'p':p,'t':typ,'s':s.st_size,'m':s.st_mtime_ns}
   if typ=='l':
    try: rec['target']=os.readlink(e.path)
    except OSError: pass
   records.append(rec)
   if typ=='d': stack.append((p,e.path))
  except OSError as ex: errors.append({'path':p,'error':str(ex)})
print(json.dumps({'root':root,'started':started,'finished':time.time(),'records':records,'errors':errors,'excluded':excluded},ensure_ascii=True,separators=(',',':')))
'''

def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)

def write_json(name, value):
    (AUDIT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def write_csv(name, rows, fields):
    with (AUDIT/name).open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def remote_cmd(code, *args):
    payload=base64.b64encode(code.encode('utf-8')).decode('ascii')
    # All remote arguments are fixed paths or JSON delivered through stdin.
    import shlex
    command='python3 -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(payload)+'))')
    if args: command+=' '+' '.join(shlex.quote(str(x)) for x in args)
    return ['ssh.exe','-o','BatchMode=yes','-o','ConnectTimeout=10',HOST,command]

def local_path(relative=''):
    return Path('\\\\?\\'+str(DEST).replace('/','\\')) / Path(*relative.split('/')) if relative else Path('\\\\?\\'+str(DEST).replace('/','\\'))

def scan_local():
    ns={'__name__':'__main__'}
    import contextlib,io
    capture=io.StringIO(); saved=sys.argv
    try:
        sys.argv=['scan',str(local_path())]
        with contextlib.redirect_stdout(capture): exec(SCAN_CODE,ns)
    finally: sys.argv=saved
    return json.loads(capture.getvalue())

def scan_remote():
    p=subprocess.run(remote_cmd(SCAN_CODE,SOURCE),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if p.returncode: raise RuntimeError(p.stderr.decode('utf-8',errors='replace'))
    return json.loads(p.stdout)

def win_invalid(p):
    for part in p.split('/'):
        if part in ('','.','..'): return 'unsafe_path_component'
        if re.search(r'[<>:"\\|?*\x00-\x1f]',part): return 'invalid_windows_name'
        if part.endswith((' ','.')): return 'windows_trailing_space_or_dot'
        if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',part): return 'windows_reserved_name'
        if len(part.encode('utf-16-le',errors='surrogatepass'))//2>255: return 'windows_component_too_long'
    return None

def ancestors(p):
    parts=p.split('/')
    return ['/'.join(parts[:n]) for n in range(1,len(parts))]

def inventory():
    AUDIT.mkdir(exist_ok=True)
    emit({'stage':'inventory_started','source':HOST+':'+SOURCE,'destination':str(DEST)})
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(scan_remote); b=pool.submit(scan_local)
        source=a.result(); destination=b.result()
    write_json('ubuntu_inventory.json',source); write_json('windows_before_inventory.json',destination)
    sr=source['records']; dr=destination['records']
    sm={}; dm={r['p'].casefold():r for r in dr}; collisions=set()
    for r in sr:
        k=r['p'].casefold()
        if k in sm: collisions.add(k)
        sm[k]=r
    error_paths={x['path'].casefold() for x in destination['errors']}
    venv_roots={r['p'].rsplit('/',1)[0] for r in sr if r['t']=='f' and r['p'].endswith('/pyvenv.cfg')}
    missing=[]; dirs=[]; common=[]; differing=[]; blocked=[]; special=[]
    for r in sr:
        p=r['p']; k=p.casefold(); existing=dm.get(k)
        reason=win_invalid(p)
        keys=[x.casefold() for x in ancestors(p)]+[k]
        if any(x in collisions for x in keys): reason='case_insensitive_collision'
        if any(x in error_paths for x in keys): reason='windows_unreadable_path'
        for parent in ancestors(p):
            d=dm.get(parent.casefold())
            if d and d['t']!='d': reason='windows_parent_is_not_directory'
        if r['t'] in ('l','o'):
            special.append({**r,'reason':'symbolic_link' if r['t']=='l' else 'special_file'}); continue
        if reason:
            blocked.append({**r,'reason':reason}); continue
        if existing:
            if existing['t']!=r['t']:
                blocked.append({**r,'reason':'type_conflict','windows_type':existing['t']})
            elif r['t']=='f':
                row={'p':p,'ubuntu_size':r['s'],'windows_size':existing['s'],'ubuntu_mtime_ns':r['m'],'windows_mtime_ns':existing['m'],'windows_path':existing['p']}
                common.append(row)
                if r['s']!=existing['s']: differing.append(row)
        elif r['t']=='d': dirs.append(r)
        else: missing.append(r)
    windows_only=[r for r in dr if r['t']=='f' and r['p'].casefold() not in sm]
    plan={'source':SOURCE,'host':HOST,'destination':str(DEST),'missing_files':missing,'missing_directories':dirs,'common_files':common,'blocked':blocked,'special':special,'venv_roots':sorted(venv_roots),'case_collisions':sorted(collisions)}
    write_json('copy_plan.json',plan)
    write_csv('E盘缺少的文件_待补齐.csv',missing,['p','s','m'])
    write_csv('同名但大小不同_保留E盘.csv',differing,['p','ubuntu_size','windows_size','ubuntu_mtime_ns','windows_mtime_ns'])
    write_csv('仅E盘存在_保留.csv',windows_only,['p','s','m'])
    write_csv('特殊路径和无法读取.csv',[*blocked,*special,*[{'p':x['path'],'reason':'ubuntu_scan_error','error':x['error']} for x in source['errors']],*[{'p':x['path'],'reason':'windows_scan_error','error':x['error']} for x in destination['errors']]],['p','t','s','reason','target','error'])
    totals=lambda records:{'files':sum(r['t']=='f' for r in records),'directories':sum(r['t']=='d' for r in records),'bytes':sum(r['s'] for r in records if r['t']=='f')}
    summary={'ubuntu':totals(sr),'windows_before':totals(dr),'missing_files':len(missing),'missing_bytes':sum(r['s'] for r in missing),'missing_directories':len(dirs),'common_files':len(common),'common_size_different':len(differing),'common_size_equal':len(common)-len(differing),'windows_only_files':len(windows_only),'blocked_paths':len(blocked),'special_paths':len(special),'ubuntu_scan_errors':len(source['errors']),'windows_scan_errors':len(destination['errors']),'case_collisions':len(collisions),'venv_roots':sorted(venv_roots),'free_bytes':shutil.disk_usage(DEST).free}
    write_json('inventory_summary.json',summary); emit(summary)
    emit({'largest_missing_files':sorted(missing,key=lambda r:r['s'],reverse=True)[:20]})
    emit({'blocked_examples':blocked[:8],'special_examples':special[:8],'source_errors':source['errors'][:8],'venv_roots':sorted(venv_roots)})

TRANSFER_CODE = r'''
import sys,os,json,stat,hashlib
request=json.load(sys.stdin); root=request['root']; output=sys.stdout.buffer
def say(value): output.write(json.dumps(value,ensure_ascii=True,separators=(',',':')).encode()+b'\n'); output.flush()
for r in request['files']:
 p=r['p']; full=os.path.join(root,p)
 fd=None
 try:
  if p.startswith('/') or '..' in p.split('/') or os.path.realpath(full)!=full: raise ValueError('unsafe_or_symlink_source')
  fd=os.open(full,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)); before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode): raise ValueError('not_regular_file')
  if before.st_size!=r['s'] or before.st_mtime_ns!=r['m']: raise ValueError('source_changed_since_inventory')
 except Exception as e:
  if fd is not None: os.close(fd)
  say({'kind':'skip','p':p,'reason':str(e)}); continue
 with os.fdopen(fd,'rb') as f:
  say({'kind':'file','p':p,'s':before.st_size,'m':before.st_mtime_ns})
  h=hashlib.sha256(); remain=before.st_size
  while remain:
   chunk=f.read(min(1024*1024,remain))
   if not chunk: raise RuntimeError('source_truncated:'+p)
   h.update(chunk); output.write(chunk); remain-=len(chunk)
  after=os.fstat(f.fileno())
  say({'kind':'digest','p':p,'sha256':h.hexdigest(),'stable':(before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)})
say({'kind':'done'})
'''

def safe_parent(relative):
    if win_invalid(relative): raise ValueError('invalid destination path')
    here=local_path()
    s=os.lstat(here)
    if not stat.S_ISDIR(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400: raise ValueError('unsafe_destination_root')
    for part in relative.split('/')[:-1]:
        here/=part
        try: s=os.lstat(here)
        except FileNotFoundError:
            os.mkdir(here); s=os.lstat(here)
        if not stat.S_ISDIR(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400: raise ValueError('unsafe_destination_parent')
    return local_path(relative)

def digest_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def copy_missing():
    if os.name!='nt': raise RuntimeError('This receiver requires Windows no-overwrite rename semantics.')
    plan=json.loads((AUDIT/'copy_plan.json').read_text(encoding='utf-8'))
    selected=[]; policy_skips=[]
    for r in plan['missing_files']:
        p=r['p']; parts=p.split('/')
        virtual=any(p==v or p.startswith(v+'/') for v in plan['venv_roots'])
        private=any(x.casefold()=='.ssh' for x in parts) or parts[-1] in ('id_rsa','id_ed25519','id_ecdsa','id_dsa')
        weight=bool(re.search(r'(?i)\.(?:gguf|safetensors)(?:\..*)?$',p)) or any(x.casefold() in ('ollama','blobs') for x in parts)
        if virtual or private or weight:
            policy_skips.append({**r,'reason':'virtual_environment' if virtual else 'ssh_private_material' if private else 'model_weight_requires_external_storage'})
        else: selected.append(r)
    needed=sum(r['s'] for r in selected)
    if shutil.disk_usage(DEST).free < needed+100*1024*1024: raise RuntimeError('Insufficient free space')
    write_json('policy_skips.json',policy_skips)
    # The selected list is saved before starting the read-only SSH stream.
    write_json('selected_files.json',selected)
    staging=AUDIT/'staging'; staging.mkdir(exist_ok=True)
    results=[]; made_dirs=[]; started=time.time()
    for r in sorted(plan['missing_directories'],key=lambda r:r['p'].count('/')):
        if any(r['p']==v or r['p'].startswith(v+'/') for v in plan['venv_roots']): continue
        try:
            d=safe_parent(r['p'])
            if not os.path.lexists(d): os.mkdir(d); made_dirs.append(r)
            elif not d.is_dir(): raise ValueError('directory_path_already_exists_as_file')
        except OSError as e: results.append({'p':r['p'],'status':'directory_error','error':str(e)})
    stderr_file=(AUDIT/'transfer_ssh_stderr.log').open('wb')
    process=subprocess.Popen(remote_cmd(TRANSFER_CODE),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr_file)
    request={'root':SOURCE,'files':selected}
    # Input is small and the remote consumes all JSON before emitting output.
    process.stdin.write(json.dumps(request,ensure_ascii=True).encode()); process.stdin.close()
    allowed={r['p']:r for r in selected}; count=0; transferred=0
    try:
        with (AUDIT/'transfer_events.jsonl').open('a',encoding='utf-8') as events:
            while True:
                raw=process.stdout.readline()
                if not raw: raise RuntimeError('SSH stream ended before completion')
                header=json.loads(raw)
                if header['kind']=='done': break
                p=header['p']
                if p not in allowed: raise RuntimeError('Unexpected path in transfer')
                if header['kind']=='skip':
                    result={'p':p,'status':'source_skipped','reason':header['reason']}
                else:
                    expected=allowed[p]
                    if header['kind']!='file' or header['s']!=expected['s']: raise RuntimeError('Unexpected transfer metadata')
                    fd,tmp=tempfile.mkstemp(prefix='receive_',suffix='.part',dir=staging)
                    try:
                        h=hashlib.sha256(); remain=header['s']
                        with os.fdopen(fd,'wb') as out:
                            while remain:
                                chunk=process.stdout.read(min(1024*1024,remain))
                                if not chunk: raise RuntimeError('Incomplete file stream')
                                out.write(chunk); h.update(chunk); remain-=len(chunk)
                        end=json.loads(process.stdout.readline())
                        if end['kind']!='digest' or end['p']!=p or end['sha256']!=h.hexdigest(): raise RuntimeError('Transfer hash mismatch')
                        if not end['stable']:
                            result={'p':p,'status':'source_unstable'}
                        else:
                            d=safe_parent(p)
                            os.utime(tmp,ns=(header['m'],header['m']))
                            if os.path.lexists(d):
                                result={'p':p,'status':'already_exists_preserved'}
                            else:
                                try:
                                    # On Windows, rename fails when the destination exists. Never use replace.
                                    os.rename(tmp,d)
                                    actual=digest_file(d)
                                    if actual!=end['sha256']: raise RuntimeError('Destination reread hash mismatch')
                                    result={'p':p,'status':'copied_verified','bytes':header['s'],'sha256':actual,'source_mtime_ns':header['m']}
                                    count+=1; transferred+=header['s']
                                except FileExistsError: result={'p':p,'status':'already_exists_preserved'}
                    finally:
                        if os.path.isfile(tmp): os.remove(tmp)
                results.append(result); events.write(json.dumps(result,ensure_ascii=False)+'\n'); events.flush()
                if len(results)%50==0: emit({'stage':'copy_progress','processed':len(results),'copied':count,'bytes':transferred})
        rc=process.wait(timeout=30)
        if rc: raise RuntimeError('SSH transfer process failed: '+str(rc))
    finally:
        if process.poll() is None: process.terminate(); process.wait(timeout=10)
        stderr_file.close(); write_json('transfer_results.json',results)
    for r in sorted(made_dirs,key=lambda r:r['p'].count('/'),reverse=True):
        try: os.utime(local_path(r['p']),ns=(r['m'],r['m']))
        except OSError: pass
    write_csv('本次已补齐并校验.csv',[r for r in results if r['status']=='copied_verified'],['p','bytes','sha256','source_mtime_ns'])
    summary={'copied_files':count,'copied_bytes':transferred,'created_directories':len(made_dirs),'policy_skips':len(policy_skips),'statuses':{},'elapsed_seconds':time.time()-started,'source_writes':0,'existing_files_overwritten':0,'existing_files_deleted':0}
    for r in results: summary['statuses'][r['status']]=summary['statuses'].get(r['status'],0)+1
    write_json('transfer_summary.json',summary); emit(summary)

HASH_CODE = r'''
import os,sys,json,hashlib,concurrent.futures,time
req=json.load(sys.stdin); root=req['root']; rows=req['files']
def one(r):
 p=r['p']
 try:
  full=os.path.join(root,p); before=os.stat(full,follow_symlinks=False)
  h=hashlib.sha256()
  with open(full,'rb') as f:
   for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
  after=os.stat(full,follow_symlinks=False)
  return {'p':p,'sha256':h.hexdigest(),'size':after.st_size,'mtime_ns':after.st_mtime_ns,'stable':(before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)}
 except Exception as e: return {'p':p,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for i,r in enumerate(pool.map(one,rows),1):
  print(json.dumps(r,ensure_ascii=True,separators=(',',':')),flush=True)
  if i%10000==0: print('hashed '+str(i)+'/'+str(len(rows)),file=sys.stderr,flush=True)
'''

def compare_hashes():
    plan=json.loads((AUDIT/'copy_plan.json').read_text(encoding='utf-8'))
    rows=plan['common_files']; started=time.time()
    emit({'stage':'full_content_comparison_started','files':len(rows)})
    stderr_file=(AUDIT/'hash_ssh_stderr.log').open('wb')
    process=subprocess.Popen(remote_cmd(HASH_CODE),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr_file)
    # Send a short ASCII request from a worker so stdout can always be drained.
    def feed():
        process.stdin.write(json.dumps({'root':SOURCE,'files':[{'p':r['p']} for r in rows]},ensure_ascii=True).encode()); process.stdin.close()
    def collect():
        result=[]
        with (AUDIT/'ubuntu_common_sha256.jsonl').open('wb') as out:
            for line in process.stdout:
                out.write(line); result.append(json.loads(line))
        return result
    def local_one(r):
        p=r['p']; full=local_path(r['windows_path'])
        try:
            before=os.stat(full,follow_symlinks=False); digest=digest_file(full); after=os.stat(full,follow_symlinks=False)
            return {'p':p,'sha256':digest,'size':after.st_size,'mtime_ns':after.st_mtime_ns,'stable':(before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)}
        except Exception as e: return {'p':p,'error':str(e)}
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as io_pool:
            sender=io_pool.submit(feed); receiver=io_pool.submit(collect)
            local=[]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool, (AUDIT/'windows_common_sha256.jsonl').open('w',encoding='utf-8') as out:
                for i,r in enumerate(pool.map(local_one,rows),1):
                    local.append(r); out.write(json.dumps(r,ensure_ascii=False)+'\n')
                    if i%10000==0: emit({'stage':'windows_hash_progress','files':i,'total':len(rows)})
            sender.result(); remote=receiver.result()
        rc=process.wait(timeout=30)
        if rc: raise RuntimeError('Remote hash failed: '+str(rc))
        if len(remote)!=len(rows): raise RuntimeError('Incomplete remote hash inventory')
    finally:
        if process.poll() is None: process.terminate(); process.wait(timeout=10)
        stderr_file.close()
    rm={r['p']:r for r in remote}; differences=[]; errors=[]; equal=0
    for r in local:
        other=rm[r['p']]
        if r.get('error') or other.get('error') or not r.get('stable') or not other.get('stable'):
            errors.append({'p':r['p'],'windows':r,'ubuntu':other})
        elif r['sha256']==other['sha256']: equal+=1
        else: differences.append({'p':r['p'],'ubuntu_size':other['size'],'windows_size':r['size'],'ubuntu_sha256':other['sha256'],'windows_sha256':r['sha256']})
    write_json('common_content_differences.json',differences); write_json('hash_errors_or_unstable.json',errors)
    write_csv('同名但内容不同_保留E盘.csv',differences,['p','ubuntu_size','windows_size','ubuntu_sha256','windows_sha256'])
    summary={'compared_common_files':len(rows),'content_identical':equal,'content_different':len(differences),'errors_or_unstable':len(errors),'elapsed_seconds':time.time()-started}
    write_json('content_comparison_summary.json',summary); emit(summary)

def verify_after():
    after_source=scan_remote(); after_dest=scan_local()
    write_json('ubuntu_after_inventory.json',after_source); write_json('windows_after_inventory.json',after_dest)
    before_source=json.loads((AUDIT/'ubuntu_inventory.json').read_text(encoding='utf-8'))
    before_dest=json.loads((AUDIT/'windows_before_inventory.json').read_text(encoding='utf-8'))
    results=json.loads((AUDIT/'transfer_results.json').read_text(encoding='utf-8'))
    dm={r['p'].casefold():r for r in after_dest['records']}
    sm={r['p']:r for r in after_source['records']}
    pre_sm={r['p']:r for r in before_source['records']}
    source_changed=[p for p,r in pre_sm.items() if p not in sm or (r['t'],r['s'],r['m'])!=(sm[p]['t'],sm[p]['s'],sm[p]['m'])]
    source_added=[p for p in sm if p not in pre_sm]
    preexisting_changed=[]; preexisting_deleted=[]
    for r in before_dest['records']:
        if r['t']!='f': continue
        now=dm.get(r['p'].casefold())
        if now is None: preexisting_deleted.append(r['p'])
        elif (r['s'],r['m'])!=(now['s'],now['m']): preexisting_changed.append(r['p'])
    verification=[]
    for r in results:
        if r['status']!='copied_verified': continue
        full=local_path(r['p'])
        verification.append({'p':r['p'],'ok':full.is_file() and full.stat().st_size==r['bytes'] and digest_file(full)==r['sha256'],'sha256':r['sha256']})
    missing=[r['p'] for r in json.loads((AUDIT/'selected_files.json').read_text(encoding='utf-8')) if r['p'].casefold() not in dm]
    summary={'verified_new_files':len(verification),'new_file_hash_failures':sum(not r['ok'] for r in verification),'planned_files_still_missing':len(missing),'source_entries_changed_or_removed_since_scan':len(source_changed),'source_entries_added_since_scan':len(source_added),'preexisting_windows_files_changed_size_or_mtime':len(preexisting_changed),'preexisting_windows_files_missing':len(preexisting_deleted),'windows_after_files':sum(r['t']=='f' for r in after_dest['records']),'windows_after_bytes':sum(r['s'] for r in after_dest['records'] if r['t']=='f'),'windows_scan_errors':len(after_dest['errors'])}
    write_json('new_file_verification.json',verification)
    write_json('after_verification_details.json',{'planned_files_still_missing':missing,'source_entries_changed':source_changed,'source_entries_added':source_added,'preexisting_windows_files_changed':preexisting_changed,'preexisting_windows_files_missing':preexisting_deleted})
    write_json('after_verification_summary.json',summary); emit(summary)

if __name__=='__main__':
    actions={'inventory':inventory,'copy':copy_missing,'hash':compare_hashes,'verify':verify_after}
    if len(sys.argv)==2 and sys.argv[1] in actions: actions[sys.argv[1]]()
    else: raise SystemExit('Usage: python sync_missing.py inventory|copy|hash|verify')
