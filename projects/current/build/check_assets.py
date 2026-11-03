#!/usr/bin/env python3
"""Exercise the original frame selector on a two-frame, 16x16 RGBA software fixture."""
import json
from pathlib import Path
import struct
import sys
import zlib
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from board.interaction import avatar_assets as assets
pool=root/'src/assets/test_fixture'
folder=assets.frames_dir('IDLE',root=pool)
frames=assets.list_frames(folder)
if [p.name for p in frames]!=['000000.png','000001.png'] or assets.frames_fps(folder)!=12 or assets.is_burst_asset(folder.name):
    raise ValueError('Unexpected frame order, FPS or loop selection')
for p in frames:
    raw=p.read_bytes()
    if raw[:8]!=bytes.fromhex('89504e470d0a1a0a'):
        raise ValueError('Not a PNG')
    pos=8
    decoded=b''
    while pos<len(raw):
        size=struct.unpack_from('>I',raw,pos)[0]
        kind=raw[pos+4:pos+8]
        part=raw[pos+8:pos+8+size]
        if zlib.crc32(kind+part)!=struct.unpack_from('>I',raw,pos+8+size)[0]:
            raise ValueError('PNG CRC mismatch')
        if kind==b'IHDR' and struct.unpack('>IIBBBBB',part)!=(16,16,8,6,0,0,0):
            raise ValueError('Unexpected PNG format')
        if kind==b'IDAT':
            decoded+=part
        pos+=12+size
    if len(zlib.decompress(decoded))!=16*(1+16*4):
        raise ValueError('Truncated fixture pixels')
print(json.dumps({'status':'PASS','selection':folder.name,'frames':len(frames),'fps':12,'size':[16,16],'board_rendered':False}))
