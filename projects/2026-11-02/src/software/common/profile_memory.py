"""Explicit profile facts atop the existing single SQLite conversation store.

Callers must authorize profile_id with ProfileAccess before entering this
trusted store API. Public HTTP accepts a scoped capability, never profile_id.
Anonymous history is never automatically assigned to a profile.
"""
import json
import re
import secrets
import time
from common.conversation_store import ConversationStore,conversation_id
from common.memory_commands import parse_command,key_terms
from common.profile_access import identifier


def scoped_command(text,personal):
    value=text.strip()
    personal_words={'查看我的长期记忆':'查看记忆','查看个人记忆':'查看记忆',
                    '清空我的长期记忆':'清空本次对话记忆','清空个人记忆':'清空本次对话记忆'}
    if value.rstrip('。！!？?') in personal_words:
        return parse_command(personal_words[value.rstrip('。！!？?')]),'personal'
    if value.startswith(('长期记住','更正长期记忆','忘记长期记忆')):
        value=re.sub(r'^长期记住','记住',value)
        value=re.sub(r'^更正长期记忆','更正记忆',value)
        value=re.sub(r'^忘记长期记忆[：:]?','忘记',value)
        return parse_command(value),'personal'
    if '本次对话' in value or '当前对话' in value:
        value=re.sub(r'^记住(?:本次|当前)对话[：:]','记住：',value)
        return parse_command(value),'conversation'
    return parse_command(value),'personal' if personal else 'conversation'


class ProfileConversationStore(ConversationStore):
    def __init__(self,path):
        super().__init__(path)
        with self.lock,self._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS profiles(
                    id TEXT PRIMARY KEY,name TEXT NOT NULL,created REAL NOT NULL,
                    memory_revision INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS conversation_profiles(
                    conversation_id TEXT PRIMARY KEY REFERENCES conversations(id),
                    profile_id TEXT NOT NULL REFERENCES profiles(id));
                CREATE INDEX IF NOT EXISTS profile_conversations ON conversation_profiles(profile_id);
                CREATE TABLE IF NOT EXISTS profile_facts(
                    profile_id TEXT NOT NULL REFERENCES profiles(id),key TEXT NOT NULL,
                    value TEXT NOT NULL,source_seq INTEGER NOT NULL REFERENCES turns(seq),
                    PRIMARY KEY(profile_id,key));
                CREATE TABLE IF NOT EXISTS profile_changes(
                    profile_id TEXT NOT NULL REFERENCES profiles(id),revision INTEGER NOT NULL,
                    operation TEXT NOT NULL,PRIMARY KEY(profile_id,revision));
            ''')
            if 'profile_revision' not in {r['name'] for r in db.execute('PRAGMA table_info(turns)')}:
                db.execute('ALTER TABLE turns ADD COLUMN profile_revision INTEGER NOT NULL DEFAULT 0')

    def create_profile(self,name,*,consent=False):
        if consent is not True:raise ValueError('Explicit profile consent required')
        if not isinstance(name,str) or not 1<=len(name.strip())<=40 or any(ord(c)<32 for c in name):
            raise ValueError('Invalid profile display name')
        pid=secrets.token_hex(16)
        with self.lock,self._connect() as db:
            db.execute('INSERT INTO profiles(id,name,created) VALUES(?,?,?)',(pid,name.strip(),time.time()))
        return pid

    def profiles(self):
        with self.lock,self._connect() as db:
            return [dict(r) for r in db.execute('SELECT id,name FROM profiles ORDER BY created,id')]

    def require_profile(self,pid):
        identifier(pid)
        with self.lock,self._connect() as db:
            if not db.execute('SELECT 1 FROM profiles WHERE id=?',(pid,)).fetchone():raise ValueError('Unknown profile')

    @staticmethod
    def _scope(db,cid,profile):
        conversation_id(cid)
        if profile is not None:identifier(profile)
        row=db.execute('SELECT profile_id FROM conversation_profiles WHERE conversation_id=?',(cid,)).fetchone()
        expected=row[0] if row else None
        if expected!=profile:raise PermissionError('Conversation belongs to another scope')

    def check_scope(self,cid,*,profile=None):
        conversation_id(cid)
        with self.lock,self._connect() as db:
            if db.execute('SELECT 1 FROM conversations WHERE id=?',(cid,)).fetchone():self._scope(db,cid,profile)
            elif profile is not None:
                identifier(profile)
                if not db.execute('SELECT 1 FROM profiles WHERE id=?',(profile,)).fetchone():raise ValueError('Unknown profile')

    def begin(self,cid,meta,text,raw_text,*,profile=None):
        conversation_id(cid)
        for value in (text,raw_text):
            if not isinstance(value,str) or not value.strip() or len(value)>4096 or '\x00' in value:
                raise ValueError('Invalid conversation input')
        with self.lock,self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            exists=db.execute('SELECT 1 FROM conversations WHERE id=?',(cid,)).fetchone()
            profile_revision=0
            if profile is not None:
                identifier(profile)
                row=db.execute('SELECT memory_revision FROM profiles WHERE id=?',(profile,)).fetchone()
                if row is None:raise ValueError('Unknown profile')
                profile_revision=row[0]
            if exists:self._scope(db,cid,profile)
            else:
                db.execute('INSERT INTO conversations(id,created) VALUES(?,?)',(cid,time.time()))
                if profile is not None:db.execute('INSERT INTO conversation_profiles VALUES(?,?)',(cid,profile))
            old=db.execute('SELECT 1 FROM turns WHERE request_id=?',(meta['request_id'],)).fetchone()
            if old:raise ValueError('Duplicate conversation request; start a new turn')
            revision=db.execute('SELECT memory_revision FROM conversations WHERE id=?',(cid,)).fetchone()[0]
            db.execute('INSERT INTO turns(request_id,conversation_id,context,user,raw_user,status,created,memory_revision,profile_revision) '
                       "VALUES(?,?,?,?,?,'submitted',?,?,?)",(meta['request_id'],cid,self._owner(meta),text,raw_text,time.time(),revision,profile_revision))
            db.execute('UPDATE conversations SET revision=revision+1 WHERE id=?',(cid,))

    def _current_revision(self,db,meta):
        super()._current_revision(db,meta)
        row=db.execute('SELECT t.profile_revision,p.memory_revision FROM turns t '
            'JOIN conversation_profiles cp ON cp.conversation_id=t.conversation_id '
            'JOIN profiles p ON p.id=cp.profile_id WHERE t.request_id=? AND t.context=?',
            (meta['request_id'],self._owner(meta))).fetchone()
        if row is not None and row[0]!=row[1]:raise ValueError('Personal memory changed; obsolete conversation output')

    def records(self,cid,*,exclude=None,limit=2000,profile=None):
        with self.lock,self._connect() as db:
            self._scope(db,cid,profile)
            return super().records(cid,exclude=exclude,limit=limit)

    def facts(self,cid,*,profile=None):
        return self.context_snapshot(cid,profile=profile)[1]

    def context_snapshot(self,cid,*,exclude=None,profile=None):
        with self.lock,self._connect() as db:
            db.execute('BEGIN');self._scope(db,cid,profile)
            rows=db.execute('SELECT seq,user,assistant,status,request_id FROM turns WHERE conversation_id=? '
                'AND request_id!=? AND seq NOT IN (SELECT seq FROM recall_exclusions) ORDER BY seq DESC LIMIT 2000',
                (cid,exclude or '')).fetchall()
            facts={r['key']:dict(r,scope='personal') for r in db.execute(
                'SELECT key,value,source_seq FROM profile_facts WHERE profile_id=? ORDER BY source_seq,key',(profile,))}
            for r in db.execute('SELECT key,value,source_seq FROM conversation_facts WHERE conversation_id=? ORDER BY source_seq,key',(cid,)):
                facts[r['key']]=dict(r,scope='conversation')
            return [dict(r) for r in reversed(rows)],list(facts.values())

    def memory_command(self,meta,text,*,profile=None):
        command,scope=scoped_command(text,profile is not None)
        if command is None:return None
        with self.lock,self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            turn=db.execute('SELECT * FROM turns WHERE request_id=? AND context=?',(meta['request_id'],self._owner(meta))).fetchone()
            if not turn or turn['status']!='submitted':raise ValueError('Missing memory command turn')
            self._scope(db,turn['conversation_id'],profile);self._current_revision(db,meta)
            if scope=='conversation':
                # The base implementation owns its transaction; release this
                # read transaction first while retaining the Python RLock.
                db.rollback()
                rewritten=re.sub(r'^记住(?:本次|当前)对话[：:]','记住：',text)
                return super().memory_command(meta,rewritten)
            seq=turn['seq']
            db.execute('INSERT OR IGNORE INTO recall_exclusions VALUES(?,?)',(seq,'personal_memory_command'))
            if profile is None:return '请先在本机明确选择个人档案，才能使用个人长期记忆。'
            facts=[dict(r) for r in db.execute('SELECT key,value,source_seq FROM profile_facts WHERE profile_id=? ORDER BY source_seq,key',(profile,))]
            op=command['operation']
            if op=='list':
                return ('个人长期记忆还没有明确事实。' if not facts else '个人长期记忆有：'+
                        '、'.join('%d%s'%(i+1,r['key']) for i,r in enumerate(facts))+'。可说“查看第1条记忆”。')
            if op=='help':return '请明确说“记住：项目是海风”，将保存到当前授权档案的长期记忆。'
            if op=='scope_help':return '请明确说“清空本次对话记忆”或“清空我的长期记忆”。'
            if 'index' in command:
                index=command['index']-1
                if index>=len(facts):return '个人长期记忆没有这条内容。'
                command['key']=facts[index]['key']
                if op=='view':return facts[index]['key']+'：'+facts[index]['value']+'。'
            key=command.get('key');previous=next((r for r in facts if r['key']==key),None)
            if op=='set' and len(facts)>=12 and previous is None:return '个人长期记忆已有12项，请先删除一项再添加。'
            if op=='set' and previous and previous['value']==command['value']:return '个人长期记忆已经记住这项内容了。'
            if op=='clear':
                db.execute('INSERT OR IGNORE INTO recall_exclusions SELECT t.seq,? FROM turns t '
                    'JOIN conversation_profiles cp ON cp.conversation_id=t.conversation_id WHERE cp.profile_id=?',('personal_memory_clear',profile))
                db.execute('DELETE FROM profile_facts WHERE profile_id=?',(profile,))
                db.execute('DELETE FROM conversation_facts WHERE conversation_id IN (SELECT conversation_id FROM conversation_profiles WHERE profile_id=?)',(profile,))
                reply='已清空当前档案的可召回长期记忆和相关历史召回。'
            else:
                needles=key_terms(key)
                if previous:needles.add(previous['value'])
                rows=db.execute('SELECT t.seq,t.user,t.raw_user,t.assistant FROM turns t JOIN conversation_profiles cp '
                    'ON cp.conversation_id=t.conversation_id WHERE cp.profile_id=? AND t.seq!=?',(profile,seq)).fetchall()
                for r in rows:
                    for candidate in [r['user']]+['记住：'+p for p in re.split('[，,。！？；;]',r['user']) if p]:
                        old,_=scoped_command(candidate,True)
                        if old and old.get('key')==key and old.get('operation')=='set':needles.add(old['value'])
                matches=[]
                for r in rows:
                    content='\n'.join(r[f] or '' for f in ('user','raw_user','assistant')).casefold()
                    if any(needle.casefold() in content for needle in needles):matches.append((r['seq'],'personal_memory_update'))
                db.executemany('INSERT OR IGNORE INTO recall_exclusions VALUES(?,?)',matches)
                db.execute('DELETE FROM conversation_facts WHERE key=? AND conversation_id IN '
                    '(SELECT conversation_id FROM conversation_profiles WHERE profile_id=?)',(key,profile))
                if op=='forget':
                    db.execute('DELETE FROM profile_facts WHERE profile_id=? AND key=?',(profile,key))
                    reply='已从当前档案的长期记忆和相关历史召回中移除这项内容。'
                else:
                    db.execute('INSERT OR REPLACE INTO profile_facts VALUES(?,?,?,?)',(profile,key,command['value'],seq))
                    reply='已'+('更正' if previous else '记住')+'当前档案的长期记忆：'+key+'。'
            db.execute('UPDATE profiles SET memory_revision=memory_revision+1 WHERE id=?',(profile,))
            revision=db.execute('SELECT memory_revision FROM profiles WHERE id=?',(profile,)).fetchone()[0]
            db.execute('INSERT INTO profile_changes VALUES(?,?,?)',(profile,revision,op))
            db.execute('UPDATE turns SET profile_revision=? WHERE seq=?',(revision,seq))
            return reply

    def health(self):
        value=super().health()
        return dict(value,version=3,scope='explicit_anonymous_or_authorized_profile',
                    personal_identity_memory=True,profile_selection='explicit_local_capability',
                    automatic_speaker_unlock=False,personal_fact_limit=12)
