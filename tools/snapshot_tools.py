"""Verify the prepared engineering files, or reconstruct a recorded source layout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]

def long_path(path):
    p=Path(path).absolute()
    return Path('\\\\?\\'+str(p)) if os.name=='nt' and not str(p).startswith('\\\\?\\') else p

def joined(root,rel):
    if rel.startswith(('/','\\')) or '..' in rel.replace('\\','/').split('/'):
        raise ValueError('Unsafe relative path: '+rel)
    p=Path(root).joinpath(*rel.split('/'))
    try:p.resolve().relative_to(Path(root).resolve())
    except ValueError:raise ValueError('Path outside destination')
    return long_path(p)

def records(name):
    p=ROOT/'inventory'/name
    if not p.exists():return
    with p.open(encoding='utf-8') as f:
        for line in f:
            if line.startswith('version https://git-lfs.github.com/spec/'):
                raise ValueError('Inventory contains a Git LFS pointer. Run git lfs pull to retrieve the entity files.')
            if line.strip():yield json.loads(line)

def digest(path):
    h=hashlib.sha256()
    with long_path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()

def verify(assets,repo_only=False):
    staged={r['path']:r for r in records('staged_files.jsonl')}
    failures=[];checked=0
    for rel,row in staged.items():
        p=joined(ROOT,rel)
        try:
            if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:failures.append({'path':rel,'error':'SHA or size mismatch'})
        except OSError as e:failures.append({'path':rel,'error':str(e)})
        checked+=1
        if checked%10000==0:print(json.dumps({'verified_repo_files':checked}),flush=True)
    releases={r['sha256']:r for r in records('release_payloads.jsonl')}
    parts=0
    if not repo_only:
        for sha,row in releases.items():
            h=hashlib.sha256();total=0
            for part in row['parts']:
                p=joined(assets,part['path'])
                try:
                    ph=hashlib.sha256();size=0
                    with p.open('rb') as f:
                        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b);ph.update(b);size+=len(b)
                    if ph.hexdigest()!=part['sha256'] or size!=part['bytes']:failures.append({'path':part['path'],'error':'release part mismatch'})
                    total+=size;parts+=1
                except OSError as e:failures.append({'path':part['path'],'error':str(e)})
            if h.hexdigest()!=sha or total!=row['bytes']:failures.append({'sha256':sha,'error':'assembled release mismatch'})
    covered=0
    for row in records('source_coverage.jsonl'):
        target=row['repo_path']
        if target.startswith('@release:'):
            found=releases.get(target.split(':',1)[1])
        else:found=staged.get(target)
        if not found or found['sha256']!=row['sha256'] or found['bytes']!=row['bytes']:
            failures.append({'source_id':row['source_id'],'path':row['rel'],'error':'source mapping mismatch'})
        covered+=1
    reference_counts={}
    for project in ('projects/current','projects/2026-11-02'):
        manifest=joined(ROOT,project+'/checksums.sha256')
        total=0
        if manifest.exists():
            for line in manifest.read_text(encoding='utf-8-sig').splitlines():
                if not line.strip():continue
                sha,name=line.split('  ',1);rel=project+'/'+name.lstrip('*');entry=staged.get(rel)
                if entry is None or entry['sha256']!=sha:failures.append({'path':rel,'error':'original delivery checksum manifest mismatch'})
                total+=1
        reference_counts[project]=total
    board=joined(ROOT,'projects/board_current/startup/config.json');board_pins=0
    if board.exists():
        config=json.loads(board.read_text(encoding='utf-8-sig'))
        for rel,sha in config['component_sha256'].items():
            path='projects/board_current/runtime/aura/'+rel;entry=staged.get(path)
            if entry is None or entry['sha256']!=sha:failures.append({'path':path,'error':'board declared component mismatch'})
            board_pins+=1
    result={'status':'PASS' if not failures else 'FAIL','repo_files':checked,'source_file_mappings':covered,'release_payloads':len(releases),'release_parts_verified':parts,'original_delivery_manifest_entries':reference_counts,'board_declared_components_verified':board_pins,'repo_only':repo_only,'failures':failures}
    print(json.dumps(result,ensure_ascii=False,indent=2));return result

def restore(source_id,out,assets,plan=False):
    rows=[r for r in records('source_coverage.jsonl') if r['source_id']==source_id]
    if not rows:raise ValueError('No covered files for source_id '+source_id)
    if plan:
        print(json.dumps({'source_id':source_id,'files':len(rows),'bytes':sum(r['bytes'] for r in rows),'output':str(out),'writes_performed':False},ensure_ascii=False,indent=2));return
    out=Path(out).absolute()
    if out.exists():raise ValueError('Choose a new output directory; existing directories are never overwritten')
    out.mkdir(parents=True)
    releases={r['sha256']:r for r in records('release_payloads.jsonl')}
    for row in rows:
        dest=joined(out,row['rel']);dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():raise ValueError('Distinct source names collide on this filesystem; restore the Linux source layout on a case-sensitive filesystem')
        if row['repo_path'].startswith('@release:'):
            release=releases[row['sha256']]
            with dest.open('xb') as dst:
                for part in release['parts']:
                    src=joined(assets,part['path'])
                    if digest(src)!=part['sha256']:raise RuntimeError('Release part verification failed')
                    with src.open('rb') as f:shutil.copyfileobj(f,dst,4*1024**2)
        else:shutil.copy2(joined(ROOT,row['repo_path']),dest)
        if dest.stat().st_size!=row['bytes'] or digest(dest)!=row['sha256']:raise RuntimeError('Restored file verification failed: '+row['rel'])
    link_count=0
    for link in records('source_links.jsonl'):
        if link['source_id']!=source_id or link['disposition']!='restorable_contained_target':continue
        dest=joined(out,link['rel']);target=joined(out,link['target_rel'])
        if dest.exists() or dest.is_symlink():continue
        if not target.exists():continue
        dest.parent.mkdir(parents=True,exist_ok=True)
        portable=os.path.relpath(str(target),str(dest.parent))
        os.symlink(portable,dest,target_is_directory=target.is_dir());link_count+=1
    print(json.dumps({'status':'PASS','source_id':source_id,'restored_files':len(rows),'restored_contained_links':link_count,'output':str(out)},ensure_ascii=False,indent=2))

def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    v=sub.add_parser('verify');v.add_argument('--assets',type=Path,default=ROOT.parent/'release_assets');v.add_argument('--repo-only',action='store_true');v.add_argument('--result',type=Path)
    r=sub.add_parser('restore');r.add_argument('--source-id',required=True);r.add_argument('--out',type=Path,required=True);r.add_argument('--assets',type=Path,default=ROOT.parent/'release_assets');r.add_argument('--plan',action='store_true')
    args=parser.parse_args()
    if args.command=='verify':
        result=verify(args.assets,args.repo_only)
        if args.result:args.result.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return 0 if result['status']=='PASS' else 1
    restore(args.source_id,args.out,args.assets,args.plan);return 0

if __name__=='__main__':sys.exit(main())
