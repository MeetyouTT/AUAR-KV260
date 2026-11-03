"""Scoped fact revisions and confirmed transcript deletion. No model/device I/O."""
import hashlib,json,re,time
from datetime import datetime
from zoneinfo import ZoneInfo
from common.memory_commands import key_name
from common.timeline import query,event_id

def parse(text):
    if not isinstance(text,str) or len(text)>200:return None
    value=re.sub(r'[。！!？?]+$','',text.strip())
    value=re.sub(r'^汐蓝[，,\s]*','',value)
    value=re.sub(r'^(?:请(?:你)?|麻烦你)?(?:帮我)?','',value).strip()
    if value in ('确认删除这些对话记录','确认删除对话记录'):return {'op':'confirm'}
    if value in ('取消删除对话记录','取消删除这些对话记录'):return {'op':'cancel'}
    match=re.fullmatch(r'(?:查看|查询|回顾)(本次对话|当前对话|我的长期|个人|我的)?(.{1,20}?)(?:的)?(?:记忆历史|记忆变更|更正历史)',value)
    if match:
        key=key_name(match[2].removesuffix('的'))
        if re.fullmatch(r'[\w\u4e00-\u9fff]{1,16}',key):return {'op':'history','scope':match[1],'key':key}
        return {'op':'help'}
    match=re.fullmatch(r'(?:删除|清除)(.*?)(?:对话|聊天)记录',value)
    if not match:return None
    body=match[1].strip();scope=None
    for prefix,target in (('本次对话中','conversation'),('当前对话中','conversation'),('本次','conversation'),('当前','conversation'),('我的','personal'),('个人','personal')):
        if body.startswith(prefix):scope=target;body=body[len(prefix):];break
    body=body.removesuffix('的').strip()
    if any(w in body for w in ('如果','假如','假设','他说','她说','不要','别','“','”','"','\n','\x00')):return {'op':'help'}
    parts=body.split('关于',1);date=parts[0].strip();topic=parts[1].removesuffix('的').strip() if len(parts)==2 else ''
    allowed=r'(?:今天|昨天|前天|昨晚|今早|上周|本周|这周|刚才|最近\d{1,3}天|\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)(?:凌晨|上午|下午|晚上)?'
    if (date and not re.fullmatch(allowed,date)) or not(date or topic):return {'op':'help'}
    if topic and not re.fullmatch(r'[\w\u4e00-\u9fff ]{1,16}',topic):return {'op':'help'}
    return {'op':'preview','scope':scope or 'conversation','date':date,'topic':topic}

def install(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS memory_fact_versions(
          owner TEXT NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL,
          source_seq INTEGER NOT NULL REFERENCES turns(seq) ON DELETE CASCADE,
          recorded REAL NOT NULL,superseded REAL,PRIMARY KEY(owner,key,source_seq));
        CREATE TABLE IF NOT EXISTS memory_source_dependencies(
          seq INTEGER NOT NULL REFERENCES turns(seq) ON DELETE CASCADE,
          source_seq INTEGER NOT NULL REFERENCES turns(seq) ON DELETE CASCADE,
          PRIMARY KEY(seq,source_seq),CHECK(seq>source_seq));
        CREATE INDEX IF NOT EXISTS memory_dependency_source ON memory_source_dependencies(source_seq);
        CREATE TABLE IF NOT EXISTS memory_control_meta(key TEXT PRIMARY KEY,value INTEGER NOT NULL);
        INSERT OR IGNORE INTO memory_control_meta SELECT 'legacy_cutoff',coalesce(max(seq),0) FROM turns;
        CREATE TABLE IF NOT EXISTS memory_delete_previews(
          owner TEXT PRIMARY KEY,query TEXT NOT NULL,fingerprint TEXT NOT NULL,
          expires REAL NOT NULL,created REAL NOT NULL);
    ''')
    for table,id_column,prefix in (('conversation_facts','conversation_id','c:'),('profile_facts','profile_id','p:')):
        owner="'"+prefix+"'||NEW."+id_column
        old_owner="'"+prefix+"'||OLD."+id_column
        at='(SELECT created FROM turns WHERE seq=NEW.source_seq)'
        body=('UPDATE memory_fact_versions SET superseded=max(recorded,'+at+') WHERE owner='+owner+' AND key=NEW.key AND superseded IS NULL;'
              'INSERT OR IGNORE INTO memory_fact_versions VALUES('+owner+',NEW.key,NEW.value,NEW.source_seq,'+at+',NULL);'
              'DELETE FROM memory_fact_versions WHERE owner='+owner+' AND key=NEW.key AND source_seq NOT IN '
              '(SELECT source_seq FROM memory_fact_versions WHERE owner='+owner+' AND key=NEW.key ORDER BY source_seq DESC LIMIT 32);')
        for action in ('INSERT','UPDATE'):
            db.executescript('CREATE TRIGGER IF NOT EXISTS mc_'+table+'_'+action.lower()+' AFTER '+action+' ON '+table+' BEGIN '+body+' END;')
        db.executescript('CREATE TRIGGER IF NOT EXISTS mc_'+table+'_delete AFTER DELETE ON '+table+' BEGIN '
                         'DELETE FROM memory_fact_versions WHERE owner='+old_owner+' AND key=OLD.key; END;')
        # Seed current facts only. Older exclusions may represent explicit forgetting.
        db.execute('INSERT OR IGNORE INTO memory_fact_versions SELECT ?||f.'+id_column+',f.key,f.value,f.source_seq,t.created,NULL '
                   'FROM '+table+' f JOIN turns t ON t.seq=f.source_seq',(prefix,))

def resolve_digest_sources(db,rows):
    out=[]
    for row in rows:
        sources=set(row.get('source_events',[]))
        records=db.execute('SELECT seq,request_id FROM turns WHERE conversation_id=? AND created>=? AND created<=? ORDER BY seq DESC LIMIT 10001',
            (row['conversation_id'],row['start_utc']-86400,row['end_utc'])).fetchall()
        if len(records)>10000:continue
        matched={event_id(kind,r['request_id']):r['seq'] for r in records for kind in ('user','assistant') if event_id(kind,r['request_id']) in sources}
        if sources and set(matched)==sources:
            row['source_seqs']=sorted(set(matched.values()));out.append(row)
    return out

class MemoryControlsMixin:
    def attach_sources(self,meta,sources,*,profile=None):
        sources=sorted(set(sources))
        if not sources:return
        if len(sources)>128 or any(type(x) is not int or x<=0 for x in sources):raise ValueError('Invalid source bound')
        with self.lock,self._connect() as db:
            db.execute('BEGIN IMMEDIATE');self._current_revision(db,meta)
            turn=db.execute('SELECT seq,conversation_id FROM turns WHERE request_id=? AND context=?',(meta['request_id'],self._owner(meta))).fetchone()
            self._scope(db,turn['conversation_id'],profile)
            for source in sources:
                row=db.execute('SELECT conversation_id FROM turns WHERE seq=? AND seq<?',(source,turn['seq'])).fetchone()
                if row is None:raise ValueError('Historical source no longer exists')
                self._scope(db,row['conversation_id'],profile)
                if profile is None and row['conversation_id']!=turn['conversation_id']:raise PermissionError('Source belongs to another conversation')
                db.execute('INSERT OR IGNORE INTO memory_source_dependencies VALUES(?,?)',(turn['seq'],source))

    @staticmethod
    def _delete_owner(meta,cid,profile):
        raw=[meta['board_boot_id'],meta['session_id'],cid,profile]
        return hashlib.sha256(json.dumps(raw,separators=(',',':')).encode()).hexdigest()

    def _selection(self,db,cid,profile,q):
        scope=('t.conversation_id=?',[cid]) if q['scope']=='conversation' else (
            't.conversation_id IN (SELECT conversation_id FROM conversation_profiles WHERE profile_id=?)',[profile])
        where=scope[0]+' AND t.seq<? AND t.created<?';args=scope[1]+[q['before_seq'],q['end']]
        if q['start'] is not None:
            where+=' AND (t.created>=? OR (p.received>=? AND p.received<?))';args += [q['start'],q['start'],q['end']]
        if q['topic']:
            where+=" AND instr(lower(t.user||char(10)||t.raw_user||char(10)||coalesce(t.assistant,'')),?)>0"
            args.append(q['topic'].lower())
        rows=db.execute('SELECT t.*,p.received AS played_at FROM turns t LEFT JOIN timeline_played p ON p.seq=t.seq WHERE '+where+' ORDER BY t.seq LIMIT 1001',args).fetchall()
        if len(rows)>1000:raise ValueError('范围超过1000轮，请缩小日期或主题。')
        selected={r['seq'] for r in rows};affected=set(selected);frontier=set(selected)
        cutoff=db.execute("SELECT value FROM memory_control_meta WHERE key='legacy_cutoff'").fetchone()[0]
        if selected and min(selected)<=cutoff:
            # Pre-upgrade replies have no complete lineage. Conservatively withhold
            # later legacy turns in this authorized scope, retaining their archive.
            affected.update(r[0] for r in db.execute('SELECT t.seq FROM turns t WHERE '+scope[0]+" AND t.seq>? AND t.seq<=? AND t.assistant IS NOT NULL AND t.seq NOT IN (SELECT seq FROM recall_exclusions WHERE reason IN ('memory_command','personal_memory_command'))",
                scope[1]+[min(selected),cutoff]))
            frontier=set(affected)
        while frontier:
            following=set()
            ordered=sorted(frontier)
            for start in range(0,len(ordered),300):
                part=ordered[start:start+300]
                following.update(r[0] for r in db.execute('SELECT seq FROM memory_source_dependencies WHERE source_seq IN ('+','.join('?' for _ in part)+')',part))
            frontier=following-affected;affected.update(frontier)
            if len(affected)>2000:raise ValueError('关联范围较大，请缩小日期或主题。')
        revisions=[r[0] for r in db.execute('SELECT memory_revision FROM profiles WHERE id=?',(profile,))] if profile else [
            db.execute('SELECT memory_revision FROM conversations WHERE id=?',(cid,)).fetchone()[0]]
        payload=[[[r[k] for k in r.keys()] for r in rows],sorted(affected),revisions]
        fingerprint=hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        return rows,affected-selected,fingerprint

    def memory_command(self,meta,text,*,profile=None):
        command=parse(text)
        if command is None:return super().memory_command(meta,text,profile=profile)
        with self.lock,self._connect() as db:
            db.execute('BEGIN IMMEDIATE');self._current_revision(db,meta)
            turn=db.execute("SELECT * FROM turns WHERE request_id=? AND context=? AND status='submitted'",(meta['request_id'],self._owner(meta))).fetchone()
            if turn is None:raise ValueError('Missing memory control turn')
            cid=turn['conversation_id'];self._scope(db,cid,profile)
            db.execute('INSERT OR IGNORE INTO recall_exclusions VALUES(?,?)',(turn['seq'],'memory_controls_command'))
            owner=self._delete_owner(meta,cid,profile);now=time.time();op=command['op']
            if op=='help':
                db.execute('DELETE FROM memory_delete_previews WHERE owner=?',(owner,))
                return '请明确日期或简短主题，例如“删除昨天关于比赛的对话记录”。已撤销旧预览，确认后才会删除。'
            if op=='history':
                personal=command['scope'] not in ('本次对话','当前对话') and (profile is not None or command['scope'] in ('我的长期','个人','我的'))
                if personal and profile is None:return '请先明确选择个人档案，才能查询个人记忆历史。'
                key=command['key'];fact_owner=('p:'+profile) if personal else ('c:'+cid)
                rows=db.execute('SELECT value,recorded,superseded FROM memory_fact_versions WHERE owner=? AND key=? ORDER BY source_seq DESC LIMIT 2',(fact_owner,key)).fetchall()
                if not rows:return '没有找到这项记忆的有效更正记录；不会恢复已遗忘的值。'
                zone=ZoneInfo(getattr(self,'memory_zone','America/Los_Angeles'))
                pieces=[datetime.fromtimestamp(r['recorded'],zone).strftime('%Y-%m-%d')+('当前值' if r['superseded'] is None else '旧值')+'：'+r['value'][:12]+('…' if len(r['value'])>12 else '') for r in reversed(rows)]
                return key+'最近两条记录：'+'；'.join(pieces)+'。日期为录入时间，长值为摘录。'
            if op=='cancel':
                db.execute('DELETE FROM memory_delete_previews WHERE owner=?',(owner,));return '已取消待确认的对话删除。'
            if op=='preview':
                db.execute('DELETE FROM memory_delete_previews WHERE owner=?',(owner,))
                if command['scope']=='personal' and profile is None:return '请先明确选择个人档案，才能删除个人档案范围的对话。'
                q=query(command['date'],now=now,zone=getattr(self,'memory_zone','America/Los_Angeles'))
                if q['error']:return q['error']
                q.update(topic=command['topic'],scope=command['scope'],before_seq=turn['seq'])
                try:rows,derived,fingerprint=self._selection(db,cid,profile,q)
                except ValueError as exc:return str(exc)
                if not rows:
                    db.execute('DELETE FROM memory_delete_previews WHERE owner=?',(owner,));return '该范围没有找到对话记录，没有删除任何内容。'
                db.execute('DELETE FROM memory_delete_previews WHERE expires<?',(now,))
                db.execute('INSERT OR REPLACE INTO memory_delete_previews VALUES(?,?,?,?,?)',(owner,json.dumps(q),fingerprint,now+60,now))
                db.execute('DELETE FROM memory_delete_previews WHERE owner NOT IN (SELECT owner FROM memory_delete_previews ORDER BY created DESC LIMIT 256)')
                label=(command['date'] or '不限日期')+('关于'+command['topic'] if command['topic'] else '')
                return (label+'找到'+str(len(rows))+'轮'+('个人档案' if q['scope']=='personal' else '本次对话')+'。确认会删除原文及来源事实，'+str(len(derived))+
                    '轮关联历史停止召回；不删视觉或备份。60秒内说“确认删除这些对话记录”，或“取消删除对话记录”。')
            pending=db.execute('SELECT * FROM memory_delete_previews WHERE owner=?',(owner,)).fetchone()
            if pending is None or not pending['created']<=now<=pending['expires']:
                db.execute('DELETE FROM memory_delete_previews WHERE owner=?',(owner,));return '没有有效的待确认删除，请重新说明日期和主题。'
            q=json.loads(pending['query'])
            try:rows,derived,fingerprint=self._selection(db,cid,profile,q)
            except ValueError as exc:return str(exc)
            db.execute('DELETE FROM memory_delete_previews WHERE owner=?',(owner,))
            if fingerprint!=pending['fingerprint']:return '相关记录已变化，这次没有删除。请重新发起删除并核对范围。'
            selected={r['seq'] for r in rows};affected=selected|derived
            conversations={r['conversation_id'] for r in rows}
            for seq in sorted(derived):
                row=db.execute('SELECT conversation_id FROM turns WHERE seq=?',(seq,)).fetchone()
                if row:conversations.add(row[0]);db.execute('INSERT OR IGNORE INTO recall_exclusions VALUES(?,?)',(seq,'deleted_source_dependency'))
            for seq in sorted(selected):
                db.execute('DELETE FROM conversation_facts WHERE source_seq=?',(seq,))
                db.execute('DELETE FROM profile_facts WHERE source_seq=?',(seq,))
                db.execute('DELETE FROM recall_exclusions WHERE seq=?',(seq,))
                db.execute('DELETE FROM turns WHERE seq=?',(seq,))
            for changed in conversations:
                db.execute('UPDATE conversations SET revision=revision+1,memory_revision=memory_revision+1 WHERE id=?',(changed,))
            if profile is not None:
                db.execute('UPDATE profiles SET memory_revision=memory_revision+1 WHERE id=?',(profile,))
                revision=db.execute('SELECT memory_revision FROM profiles WHERE id=?',(profile,)).fetchone()[0]
                db.execute('INSERT INTO profile_changes VALUES(?,?,?)',(profile,revision,'conversation_delete'))
                db.execute('UPDATE turns SET profile_revision=? WHERE seq=?',(revision,turn['seq']))
            db.execute('UPDATE turns SET memory_revision=(SELECT memory_revision FROM conversations WHERE id=?) WHERE seq=?',(cid,turn['seq']))
            return '已删除'+str(len(selected))+'轮对话原文，并停止召回'+str(len(derived))+'轮关联历史。视觉记录和备份未删除。'
