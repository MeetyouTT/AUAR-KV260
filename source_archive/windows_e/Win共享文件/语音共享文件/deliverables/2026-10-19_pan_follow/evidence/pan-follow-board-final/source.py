"""Repair test-process namespace setup; reuse the SHA-verified staged payload."""
import hashlib
from pathlib import Path
p=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/539ec1f3d5e4f5b0/source.py')
raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='539ec1f3d5e4f5b0a0c533541c27f5d50c134e62990c305549c22bcee9865990'
source=raw.decode().replace("board.__path__.insert(0,str(stage/'board'));common.__path__.insert(0,str(stage/'common'))", "board.__path__=[str(stage/'board')]+list(board.__path__);common.__path__=[str(stage/'common')]+list(common.__path__)")
source=source.replace("board.motion.__path__.insert(0,str(stage/'board/motion'))", "board.motion.__path__=[str(stage/'board/motion')]+list(board.motion.__path__)")
source=source.replace('packet=module.packet(i+1,1000+i*100,x=x)', "packet=module.packet(i+1,1000+i*100,x=x,source_kind='fixture')")
exec(compile(source,str(p)+'-namespace-fix','exec'))
