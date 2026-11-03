"""Protected board-local grant delivery; loading never activates a profile."""
import json
import os
from pathlib import Path
import re
import stat
from common.conversation_store import conversation_id
from common.profile_access import actor,identifier


def selection(value,boot_id):
    if not isinstance(value,dict) or value.get('mode')!='profile':raise ValueError('No authorized profile selection')
    if value.get('board_boot_id')!=boot_id:raise ValueError('Profile authorization belongs to another boot')
    actor(value);conversation_id(value.get('conversation_id'));identifier(value.get('profile_id'))
    if not isinstance(value.get('access_token'),str) or not re.fullmatch('[0-9a-f]{64}',value['access_token']):raise ValueError('Invalid profile credential')
    return dict(value)


def read_selection(path,boot_id):
    path=Path(path)
    if path.is_symlink():raise ValueError('Profile selection cannot be a symbolic link')
    info=path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size>8192:raise ValueError('Invalid profile selection file')
    if os.name!='nt' and (info.st_uid!=os.getuid() or info.st_mode&0o077):raise PermissionError('Profile selection file must be private')
    return selection(json.loads(path.read_text(encoding='utf-8')),boot_id)
