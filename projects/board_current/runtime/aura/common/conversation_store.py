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
                CREATE TABLE IF NOT EXISTS conversation_facts (
                    conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    key TEXT NOT NULL, value TEXT NOT NULL, source_seq INTEGER NOT NULL,
                    PRIMARY KEY(conversation_id,key));
                CREATE TABLE IF NOT EXISTS recall_exclusions (
                    seq INTEGER PRIMARY KEY REFERENCES turns(seq), reason TEXT NOT NULL);
            ''')
            for table in ('conversations', 'turns'):
                if 'memory_revision' not in {r['name'] for r in db.execute('PRAGMA table_info('+table+')')}:
                    db.execute('ALTER TABLE '+table+' ADD COLUMN memory_revision INTEGER NOT NULL DEFAULT 0')

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
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO conversations(id,created) VALUES(?,?)', (cid, time.time()))
            old = db.execute('SELECT * FROM turns WHERE request_id=?', (meta['request_id'],)).fetchone()
            if old:
                if (old['conversation_id'], old['context'], old['user'], old['raw_user']) != (
                        cid, self._owner(meta), text, raw_text):
                    raise ValueError('Turn identifier reused with different input')
                raise ValueError('Duplicate conversation request; start a new turn')
            revision = db.execute('SELECT memory_revision FROM conversations WHERE id=?', (cid,)).fetchone()[0]
            db.execute('INSERT INTO turns(request_id,conversation_id,context,user,raw_user,status,created,memory_revision) '
                       'VALUES(?,?,?,?,?,?,?,?)',
                       (meta['request_id'], cid, self._owner(meta), text, raw_text, 'submitted', time.time(), revision))
            db.execute('UPDATE conversations SET revision=revision+1 WHERE id=?', (cid,))

    def generated(self, meta, text, samples, digest):
        with self.lock, self._connect() as db:
            changed = db.execute("UPDATE turns SET assistant=?,samples=?,digest=?,status='generated' "
                                 "WHERE request_id=? AND context=? AND status='submitted'",
                                 (text, samples, digest, meta['request_id'], self._owner(meta))).rowcount
            if changed != 1:
                raise ValueError('Missing or obsolete conversation turn')
            self._current_revision(db, meta)

    def played(self, meta, samples, digest):
        with self.lock, self._connect() as db:
            row = db.execute('SELECT * FROM turns WHERE request_id=?', (meta['request_id'],)).fetchone()
            if (not row or row['context'] != self._owner(meta) or row['samples'] != samples
                    or row['digest'] != digest or row['status'] not in ('generated', 'played')):
                raise ValueError('Invalid durable playback acknowledgement')
            self._current_revision(db, meta)
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
                              'WHERE conversation_id=? AND request_id!=? '
                              'AND seq NOT IN (SELECT seq FROM recall_exclusions) ORDER BY seq DESC LIMIT ?',
                              (cid, exclude or '', limit)).fetchall()
            return [dict(row) for row in reversed(rows)]

    def _current_revision(self, db, meta):
        row = db.execute('SELECT t.memory_revision,c.memory_revision AS current_revision FROM turns t '
                         'JOIN conversations c ON c.id=t.conversation_id '
                         'WHERE t.request_id=? AND t.context=?', (meta['request_id'], self._owner(meta))).fetchone()
        if not row or row['memory_revision'] != row['current_revision']:
            raise ValueError('Memory changed; obsolete conversation output')

    def assert_current(self, meta):
        with self.lock, self._connect() as db:
            self._current_revision(db, meta)

    def facts(self, cid):
        conversation_id(cid)
        with self.lock, self._connect() as db:
            return [dict(row) for row in db.execute('SELECT key,value,source_seq FROM conversation_facts '
                    'WHERE conversation_id=? ORDER BY source_seq,key', (cid,))]

    def context_snapshot(self, cid, *, exclude=None):
        # Keep facts/history coherent even if another connection changes memory.
        with self.lock, self._connect() as db:
            db.execute('BEGIN')
            conversation_id(cid)
            records = db.execute('SELECT seq,user,assistant,status,request_id FROM turns WHERE conversation_id=? '
                        'AND request_id!=? AND seq NOT IN (SELECT seq FROM recall_exclusions) '
                        'ORDER BY seq DESC LIMIT 2000', (cid, exclude or '')).fetchall()
            facts = db.execute('SELECT key,value,source_seq FROM conversation_facts WHERE conversation_id=? '
                               'ORDER BY source_seq,key', (cid,)).fetchall()
            return [dict(r) for r in reversed(records)], [dict(r) for r in facts]

    def memory_command(self, meta, text):
        from common.memory_commands import parse_command, key_terms
        command = parse_command(text)
        if command is None:
            return None
        with self.lock, self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            turn = db.execute('SELECT * FROM turns WHERE request_id=? AND context=?',
                              (meta['request_id'], self._owner(meta))).fetchone()
            if not turn or turn['status'] != 'submitted':
                raise ValueError('Missing memory command turn')
            self._current_revision(db, meta)
            cid, seq = turn['conversation_id'], turn['seq']
            facts = [dict(r) for r in db.execute('SELECT key,value,source_seq FROM conversation_facts '
                     'WHERE conversation_id=? ORDER BY source_seq,key', (cid,))]
            # Commands/results are archive-only, never future factual evidence.
            db.execute('INSERT OR IGNORE INTO recall_exclusions VALUES(?,?)', (seq, 'memory_command'))
            operation = command['operation']
            if operation == 'list':
                if not facts: return '本次对话还没有明确记忆。'
                names = '、'.join('%d%s' % (i+1, r['key']) for i, r in enumerate(facts))
                return '本次对话记有：'+names+'。可说“查看第1条记忆”。'
            if operation == 'help':
                return '请明确说“记住：项目是海风”或“记住：项目等于海风”。'
            if operation == 'scope_help':
                return '若要重新开始，请说“清空本次对话记忆”，只影响这次对话。'
            if 'index' in command:
                index = command['index'] - 1
                if index >= len(facts): return '本次对话没有这条记忆。'
                command['key'] = facts[index]['key']
                if operation == 'view': return facts[index]['key']+'：'+facts[index]['value']+'。'
            key = command.get('key')
            if operation == 'set' and len(facts) >= 12 and key not in {r['key'] for r in facts}:
                return '本次对话已记住12项，请先删除一项再添加。'
            previous = next((r for r in facts if r['key'] == key), None)
            if operation == 'set' and previous and previous['value'] == command['value']:
                return '本次对话已经记住这项内容了。'
            if operation == 'clear':
                db.execute('INSERT OR IGNORE INTO recall_exclusions SELECT seq,? FROM turns '
                           'WHERE conversation_id=?', ('memory_clear', cid))
                db.execute('DELETE FROM conversation_facts WHERE conversation_id=?', (cid,))
                reply = '已清空本次对话的可召回记忆，接下来重新聊。'
            else:
                needles = key_terms(key)
                if previous: needles.add(previous['value'])
                # Include prior explicit values for this key, without retaining
                # deleted values in tombstones. Full turns are suppressed so
                # paraphrases in assistant responses cannot resurrect the fact.
                for row in db.execute('SELECT user FROM turns WHERE conversation_id=? AND seq!=?', (cid, seq)):
                    candidates = [row['user']] + ['记住：'+part for part in re.split(r'[，,。！？；;]',row['user']) if part]
                    for candidate in candidates:
                        old = parse_command(candidate)
                        if old and old.get('key') == key and old.get('operation') == 'set':
                            needles.add(old['value'])
                matches = []
                for row in db.execute('SELECT seq,user,raw_user,assistant FROM turns WHERE conversation_id=? '
                                      'AND seq!=?', (cid, seq)):
                    content = '\n'.join(row[f] or '' for f in ('user','raw_user','assistant')).casefold()
                    if any(needle.casefold() in content for needle in needles): matches.append((row['seq'], 'memory_update'))
                db.executemany('INSERT OR IGNORE INTO recall_exclusions VALUES(?,?)', matches)
                if operation == 'forget':
                    db.execute('DELETE FROM conversation_facts WHERE conversation_id=? AND key=?', (cid,key))
                    reply = ('已从本次对话的记忆和相关历史召回中移除这项内容。' if previous or matches
                             else '本次对话没有找到这项记忆。')
                else:
                    db.execute('INSERT OR REPLACE INTO conversation_facts VALUES(?,?,?,?)',
                               (cid,key,command['value'],seq))
                    reply = '已'+('更正' if previous else '记住')+'本次对话的'+key+'。'
            db.execute('UPDATE conversations SET revision=revision+1,memory_revision=memory_revision+1 WHERE id=?', (cid,))
            db.execute('UPDATE turns SET memory_revision=(SELECT memory_revision FROM conversations WHERE id=?) '
                       'WHERE seq=?', (cid,seq))
            return reply

    def health(self):
        # No text, names, identifiers or filesystem paths in the public health API.
        with self.lock, self._connect() as db:
            return {'version': 2, 'persistent': True, 'scope': 'explicit_anonymous_conversation',
                    'conversations': db.execute('SELECT count(*) FROM conversations').fetchone()[0],
                    'turns': db.execute('SELECT count(*) FROM turns').fetchone()[0],
                    'assistant_commit': 'full_playback_ack', 'summary': 'source_excerpts_v1',
                    'memory_controls': 'explicit_conversation_facts_v1', 'personal_identity_memory': False,
                    'memory_mutation_commit': 'input_submission', 'forgotten_history_recall': False}
