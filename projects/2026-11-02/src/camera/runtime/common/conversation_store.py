"""Durable anonymous conversations. Transport epochs never select a person.

Only full playback acknowledgements make assistant output eligible for recall.
User input survives a failed reply. SQLite transactions make retries idempotent.
"""
import json
import re
import sqlite3
import threading
import time
from pathlib import Path


def conversation_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{32}', value):
        raise ValueError('Invalid conversation identifier')
    return value


class ConversationStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, created REAL NOT NULL, revision INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS turns (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT UNIQUE NOT NULL,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    context TEXT NOT NULL, user TEXT NOT NULL, raw_user TEXT NOT NULL,
                    assistant TEXT, samples INTEGER, digest TEXT,
                    status TEXT NOT NULL, created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS conversation_turns ON turns(conversation_id, seq);
            ''')

    def _connect(self):
        db = sqlite3.connect(str(self.path), timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    @staticmethod
    def _owner(meta):
        return json.dumps(meta, sort_keys=True, separators=(',', ':'))

    def begin(self, cid, meta, text, raw_text):
        cid = conversation_id(cid)
        for value in (text, raw_text):
            if not isinstance(value, str) or not value.strip() or len(value) > 4096 or '\x00' in value:
                raise ValueError('Invalid conversation input')
        with self.lock, self._connect() as db:
            db.execute('INSERT OR IGNORE INTO conversations(id,created) VALUES(?,?)', (cid, time.time()))
            old = db.execute('SELECT * FROM turns WHERE request_id=?', (meta['request_id'],)).fetchone()
            if old:
                if (old['conversation_id'], old['context'], old['user'], old['raw_user']) != (
                        cid, self._owner(meta), text, raw_text):
                    raise ValueError('Turn identifier reused with different input')
                raise ValueError('Duplicate conversation request; start a new turn')
            db.execute('INSERT INTO turns(request_id,conversation_id,context,user,raw_user,status,created) '
                       'VALUES(?,?,?,?,?,?,?)',
                       (meta['request_id'], cid, self._owner(meta), text, raw_text, 'submitted', time.time()))
            db.execute('UPDATE conversations SET revision=revision+1 WHERE id=?', (cid,))

    def generated(self, meta, text, samples, digest):
        with self.lock, self._connect() as db:
            changed = db.execute("UPDATE turns SET assistant=?,samples=?,digest=?,status='generated' "
                                 "WHERE request_id=? AND context=? AND status='submitted'",
                                 (text, samples, digest, meta['request_id'], self._owner(meta))).rowcount
            if changed != 1:
                raise ValueError('Missing or obsolete conversation turn')

    def played(self, meta, samples, digest):
        with self.lock, self._connect() as db:
            row = db.execute('SELECT * FROM turns WHERE request_id=?', (meta['request_id'],)).fetchone()
            if (not row or row['context'] != self._owner(meta) or row['samples'] != samples
                    or row['digest'] != digest or row['status'] not in ('generated', 'played')):
                raise ValueError('Invalid durable playback acknowledgement')
            if row['status'] == 'played':
                return False
            db.execute("UPDATE turns SET status='played' WHERE request_id=?", (meta['request_id'],))
            db.execute('UPDATE conversations SET revision=revision+1 WHERE id=?', (row['conversation_id'],))
            return True

    def failed(self, meta):
        with self.lock, self._connect() as db:
            db.execute("UPDATE turns SET status='interrupted' WHERE request_id=? AND context=? "
                       "AND status IN ('submitted','generated')", (meta['request_id'], self._owner(meta)))

    def records(self, cid, *, exclude=None, limit=2000):
        conversation_id(cid)
        if not 1 <= limit <= 2000:
            raise ValueError('Invalid history bound')
        with self.lock, self._connect() as db:
            rows = db.execute('SELECT seq,user,assistant,status,request_id FROM turns '
                              'WHERE conversation_id=? AND request_id!=? ORDER BY seq DESC LIMIT ?',
                              (cid, exclude or '', limit)).fetchall()
            return [dict(row) for row in reversed(rows)]

    def health(self):
        # No text, names, identifiers or filesystem paths in the public health API.
        with self.lock, self._connect() as db:
            return {'version': 1, 'persistent': True, 'scope': 'explicit_anonymous_conversation',
                    'conversations': db.execute('SELECT count(*) FROM conversations').fetchone()[0],
                    'turns': db.execute('SELECT count(*) FROM turns').fetchone()[0],
                    'assistant_commit': 'full_playback_ack', 'summary': 'source_excerpts_v1'}
