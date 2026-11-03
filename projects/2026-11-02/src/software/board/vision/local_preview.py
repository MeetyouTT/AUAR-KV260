"""Atomic RAM-backed latest BGR frame; explicit owner, size and source deadline.

Optional fast path for this board's camera adapter. No device is opened here.
JPEG/HTTP remains available for other clients and explicit frame requests.
"""
import json
import os
from pathlib import Path
import re
import stat
import struct

MAGIC = b'AURABGR1'
PREFIX = struct.Struct('!8sH')
PIXELS = 640*480*3
MAX_HEADER = 1024
TRANSPORT = 'aura-local-bgr-1'


def frame_path(owner, directory='/run'):
    epoch = owner['camera_epoch']
    if not isinstance(epoch,str) or not re.fullmatch('[0-9a-f]{32}',epoch):
        raise ValueError('Invalid local camera epoch')
    return Path(directory)/('aura-camera-ui-'+epoch+'.frame')


def unpack(data, owner, now_ms):
    if len(data)<PREFIX.size:raise ValueError('Truncated frame prefix')
    magic,size = PREFIX.unpack_from(data)
    if magic!=MAGIC or not 0<size<=MAX_HEADER or len(data)!=PREFIX.size+size+PIXELS:
        raise ValueError('Invalid raw frame size/format')
    header=json.loads(data[PREFIX.size:PREFIX.size+size])
    if (not isinstance(header,dict) or set(header)!=set(owner)|{'frame_id','captured_mono_ms'}
            or any(header.get(k)!=v for k,v in owner.items())
            or type(header['frame_id']) is not int or not 0<header['frame_id']<2**53
            or type(header['captured_mono_ms']) is not int
            or not -100<=now_ms-header['captured_mono_ms']<250):
        raise ValueError('Raw frame owner, sequence or deadline mismatch')
    return header,data[PREFIX.size+size:]


class RawFrameStore:
    def __init__(self, owner, directory='/run'):
        self.owner=dict(owner)
        self.path=frame_path(owner,directory)
        if self.path.exists() or self.path.is_symlink():raise FileExistsError(str(self.path))
        self.inode=None

    def publish(self, fid, stamp, pixels):
        if len(pixels)!=PIXELS:raise ValueError('Expected contiguous 640x480 BGR')
        header=json.dumps(dict(self.owner,frame_id=fid,captured_mono_ms=stamp),separators=(',',':')).encode()
        if len(header)>MAX_HEADER:raise ValueError('Raw frame header too large')
        temp=self.path.with_suffix('.part')
        descriptor=os.open(str(temp),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(descriptor,'wb') as stream:
                stream.write(PREFIX.pack(MAGIC,len(header)));stream.write(header);stream.write(pixels)
            os.replace(str(temp),str(self.path))
            self.inode=self.path.stat().st_ino
        finally:
            if temp.exists():temp.unlink()  # This call created this private temporary file.

    def close(self):
        if self.inode is not None:
            try:
                if self.path.lstat().st_ino==self.inode:self.path.unlink()
            except FileNotFoundError:pass


class RawFrameReader:
    def __init__(self, owner, directory='/run'):
        self.owner=dict(owner)
        self.path=frame_path(owner,directory)
        self.inode=None
        self.previous=0

    def read(self, now_ms):
        fd=os.open(str(self.path),os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode&0o077
                    or not PREFIX.size<info.st_size<=PREFIX.size+MAX_HEADER+PIXELS):
                raise ValueError('Invalid local frame file')
            version=(info.st_dev,info.st_ino,info.st_mtime_ns,info.st_size)
            if version==self.inode:return None
            data=stream.read(PREFIX.size+MAX_HEADER+PIXELS+1)
        header,pixels=unpack(data,self.owner,now_ms)
        if header['frame_id']<=self.previous:raise ValueError('Raw frame sequence rolled back')
        self.inode,self.previous=version,header['frame_id']
        return header,pixels
