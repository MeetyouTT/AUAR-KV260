"""Atomic board-local anonymous conversation selection, no person identity."""
import json
import os
from pathlib import Path
import uuid

from common.conversation_store import conversation_id


class ConversationSelection:
    def __init__(self, path):
        self.path = Path(path)
        self.saved = None
        self.active = None  # Loading a file never grants automatic resumption.
        if self.path.exists():
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if set(value) != {'version', 'conversation_id'} or value['version'] != 1:
                raise ValueError('Invalid conversation selection file')
            self.saved = conversation_id(value['conversation_id'])

    def select(self, resume):
        if type(resume) is not bool:
            raise ValueError('Expected explicit conversation selection')
        if resume and self.saved is None:
            raise ValueError('No saved conversation to resume')
        cid = self.saved if resume else uuid.uuid4().hex
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + '.tmp-' + uuid.uuid4().hex)
        try:
            with os.fdopen(os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
                json.dump({'version': 1, 'conversation_id': cid}, out)
                out.flush(); os.fsync(out.fileno())
            os.replace(str(temporary), str(self.path))
        finally:
            temporary.unlink(missing_ok=True)
        self.saved = self.active = cid
        return cid
