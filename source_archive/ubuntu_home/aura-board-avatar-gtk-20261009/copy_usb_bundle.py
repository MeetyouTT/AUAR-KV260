#!/usr/bin/env python3
"""Copy four prepared files into a new directory on the identified USB drive.

No overwrite, formatting, remounting, filesystem repair, or board operations.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'USB_READY_AURA_AVATAR'
MOUNT = Path('/media/ghmd/64 GB')
DEVICE = '/dev/sda1'
DESTINATION = 'AURA_AVATAR_20261009_1a8677ce'
ZIP_NAME = 'aura-board-avatar-gtk-runtime-20261009T112752Z-57fc8c.zip'
ZIP_SHA = '1a8677ce385516b406344f5e22acfed72e1fd9ab1ffe79aa745760e1137917de'
FILES = (ZIP_NAME,'SHA256SUMS','package_verification.json','U盘部署步骤.txt')


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            result.update(chunk)
    return result.hexdigest()


def mount_identity():
    result = subprocess.run(['findmnt','-J','-T',str(MOUNT),'-o','SOURCE,TARGET,FSTYPE,OPTIONS'],
                            check=True,stdout=subprocess.PIPE,text=True)
    mounts = json.loads(result.stdout)['filesystems']
    if len(mounts)!=1:
        raise RuntimeError('Cannot confirm exactly one USB mount')
    item = mounts[0]
    if item['source']!=DEVICE or item['target']!=str(MOUNT) or item['fstype']!='vfat':
        raise RuntimeError('USB mount identity changed')
    if 'rw' not in item['options'].split(','):
        raise RuntimeError('USB mount is not writable in this execution environment')
    result = subprocess.run(['lsblk','-J','-o','NAME,PATH,TRAN,RM,TYPE,MOUNTPOINT','/dev/sda'],
                            check=True,stdout=subprocess.PIPE,text=True)
    blocks = json.loads(result.stdout)['blockdevices']
    if len(blocks)!=1 or blocks[0]['tran']!='usb' or not blocks[0]['rm']:
        raise RuntimeError('Source device is not the identified removable USB disk')
    children = blocks[0].get('children',[])
    if not any(row['path']==DEVICE and row['mountpoint']==str(MOUNT) for row in children):
        raise RuntimeError('USB partition no longer matches its mount point')
    return item


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate',action='store_true',help='Validate local sources only; no USB writes')
    parser.add_argument('--inspect',action='store_true',help='Confirm USB identity and free space; no USB writes')
    args=parser.parse_args()
    rows=[]
    for name in FILES:
        path=SOURCE/name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('Prepared regular source file is missing: '+name)
        rows.append({'file':name,'bytes':path.stat().st_size,'sha256':digest(path)})
    if rows[0]['sha256']!=ZIP_SHA or rows[0]['bytes']!=217023529:
        raise RuntimeError('Prepared runtime archive changed')
    if args.validate:
        print(json.dumps({'source_files_verified':len(rows),'archive_sha256':ZIP_SHA,
                          'destination':str(MOUNT/DESTINATION),'usb_written':False},ensure_ascii=False))
        return 0
    if args.inspect:
        print(json.dumps({'mount_identity':mount_identity(),'free_bytes':shutil.disk_usage(MOUNT).free,
                          'destination_exists':(MOUNT/DESTINATION).exists(),'usb_written':False},ensure_ascii=False))
        return 0
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    evidence=ROOT/'evidence'/(stamp+'-usb-copy')
    evidence.mkdir(parents=True)
    status={'started_utc':utc(),'device':DEVICE,'mount_point':str(MOUNT),
            'destination':str(MOUNT/DESTINATION),'source_files':rows,'copied_files':[],
            'complete':False,'overwritten_files':False,'evidence':str(evidence)}
    root_fd=dest_fd=None
    try:
        status['mount_identity']=mount_identity()
        free=shutil.disk_usage(MOUNT).free
        if free<sum(row['bytes'] for row in rows)+16*1024*1024:
            raise RuntimeError('Insufficient USB free space')
        status['free_bytes_before']=free
        root_fd=os.open(str(MOUNT),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        os.mkdir(DESTINATION,dir_fd=root_fd)
        dest_fd=os.open(DESTINATION,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root_fd)
        for row in rows:
            mount_identity()
            fd=os.open(row['file'],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=dest_fd)
            with (SOURCE/row['file']).open('rb') as src,os.fdopen(fd,'wb') as dest:
                shutil.copyfileobj(src,dest,1024*1024)
                dest.flush()
                os.fsync(dest.fileno())
            copied=MOUNT/DESTINATION/row['file']
            if copied.stat().st_size!=row['bytes'] or digest(copied)!=row['sha256']:
                raise RuntimeError('USB copied file integrity mismatch: '+row['file'])
            status['copied_files'].append(dict(row,sha256_readback_verified=True,fsync_completed=True))
            print(json.dumps({'copied':row['file'],'bytes':row['bytes'],'sha256_verified':True},ensure_ascii=False),flush=True)
        os.fsync(dest_fd)
        os.fsync(root_fd)
        status['complete']=True
    except Exception as exc:
        status['error']=type(exc).__name__+': '+str(exc)
        print(json.dumps({'error':status['error']},ensure_ascii=False),flush=True)
    finally:
        if dest_fd is not None:
            os.close(dest_fd)
        if root_fd is not None:
            os.close(root_fd)
        status['finished_utc']=utc()
        (evidence/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'complete':status['complete'],'destination':status['destination'],
                      'evidence':str(evidence),'usb_unmounted':False},ensure_ascii=False),flush=True)
    return 0 if status['complete'] else 1


if __name__=='__main__':
    sys.exit(main())
