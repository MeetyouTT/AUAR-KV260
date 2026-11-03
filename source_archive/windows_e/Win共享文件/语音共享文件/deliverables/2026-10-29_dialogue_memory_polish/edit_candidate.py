"""Apply r4 improvements only in the frozen candidate."""
import hashlib,json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';C=H/'candidate_source'
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'));assert plan['status']=='BUILDING'
name='tools/board_model_host.py'
for base in ('before','candidate_source'):shutil.copy2(A/name,H/base/name)
plan['files'][name]={'before':hashlib.sha256((A/name).read_bytes()).hexdigest()}
def edit(name,old,new):
    p=C/name;t=p.read_text(encoding='utf-8');assert t.count(old)==1,(name,old);p.write_text(t.replace(old,new,1),encoding='utf-8')
edit('common/memory_controls.py',"    if value in ('确认删除这些对话记录','确认删除对话记录'):",
     "    from common.fact_answers import question\n    natural=question(value)\n    if natural is not None:return natural\n    if value in ('确认删除这些对话记录','确认删除对话记录'):")
edit('common/memory_controls.py',"        return {'op':'help'}\n    match=re.fullmatch(r'(?:删除|清除)",
     "        return {'op':'history_help'}\n    match=re.fullmatch(r'(?:删除|清除)")
edit('common/memory_controls.py',"        CREATE INDEX IF NOT EXISTS memory_dependency_source ON memory_source_dependencies(source_seq);",
     "        CREATE INDEX IF NOT EXISTS memory_dependency_source ON memory_source_dependencies(source_seq);\n        CREATE TABLE IF NOT EXISTS memory_source_coverage(\n          seq INTEGER PRIMARY KEY REFERENCES turns(seq) ON DELETE CASCADE,version INTEGER NOT NULL);")
edit('common/memory_controls.py','    def attach_sources(self,meta,sources,*,profile=None):','    def attach_sources(self,meta,sources,*,profile=None,mark_complete=False):')
edit('common/memory_controls.py','        if not sources:return','        if not sources and not mark_complete:return')
edit('common/memory_controls.py',"            self._scope(db,turn['conversation_id'],profile)\n            for source in sources:",
     "            self._scope(db,turn['conversation_id'],profile)\n            if mark_complete:db.execute('INSERT OR REPLACE INTO memory_source_coverage VALUES(?,1)',(turn['seq'],))\n            for source in sources:")
old="""        cutoff=db.execute("SELECT value FROM memory_control_meta WHERE key='legacy_cutoff'").fetchone()[0]
        if selected and min(selected)<=cutoff:
            # Pre-upgrade replies have no complete lineage. Conservatively withhold
            # later legacy turns in this authorized scope, retaining their archive.
            affected.update(r[0] for r in db.execute('SELECT t.seq FROM turns t WHERE '+scope[0]+" AND t.seq>? AND t.seq<=? AND t.assistant IS NOT NULL AND t.seq NOT IN (SELECT seq FROM recall_exclusions WHERE reason IN ('memory_command','personal_memory_command'))",
                scope[1]+[min(selected),cutoff]))
            frontier=set(affected)
"""
new="""        if selected:
            # Unknown old/imported/rollback writers remain unknown regardless of seq.
            legacy_scope=('t.conversation_id=?',[cid]) if profile is None else (
                't.conversation_id IN (SELECT conversation_id FROM conversation_profiles WHERE profile_id=?)',[profile])
            unknown=db.execute('SELECT t.seq FROM turns t WHERE '+legacy_scope[0]+
                " AND t.seq>? AND t.assistant IS NOT NULL "
                "AND NOT EXISTS(SELECT 1 FROM memory_source_coverage c WHERE c.seq=t.seq) "
                "AND NOT EXISTS(SELECT 1 FROM memory_source_dependencies d WHERE d.seq=t.seq) "
                "AND t.seq NOT IN (SELECT seq FROM recall_exclusions WHERE reason IN "
                "('memory_command','personal_memory_command','memory_controls_command')) ORDER BY t.seq LIMIT 2001",
                legacy_scope[1]+[min(selected)]).fetchall()
            affected.update(r[0] for r in unknown)
            if len(affected)>2000:raise ValueError('关联范围较大，请缩小日期或主题。')
            frontier=set(affected)
"""
edit('common/memory_controls.py',old,new)
edit('common/memory_controls.py','    def memory_command(self,meta,text,*,profile=None):',
"""    @staticmethod
    def _fact_owner(db,cid,profile,scope,key):
        if scope in ('本次对话','当前对话'):return 'c:'+cid,False
        if scope in ('我的长期','个人','我的'):
            return (('p:'+profile,True) if profile is not None else (None,True))
        if db.execute('SELECT 1 FROM conversation_facts WHERE conversation_id=? AND key=?',(cid,key)).fetchone():
            return 'c:'+cid,False
        return (('p:'+profile,True) if profile is not None else ('c:'+cid,False))

    def memory_command(self,meta,text,*,profile=None):""")
old="""            if op=='history':
                personal=command['scope'] not in ('本次对话','当前对话') and (profile is not None or command['scope'] in ('我的长期','个人','我的'))
                if personal and profile is None:return '请先明确选择个人档案，才能查询个人记忆历史。'
                key=command['key'];fact_owner=('p:'+profile) if personal else ('c:'+cid)
                rows=db.execute('SELECT value,recorded,superseded FROM memory_fact_versions WHERE owner=? AND key=? ORDER BY source_seq DESC LIMIT 2',(fact_owner,key)).fetchall()
"""
new="""            if op=='history_help':
                return '请说明哪项记忆，例如“查看颜色记忆历史”或“查看颜色第3条记忆历史”，条目从新到旧编号。'
            if op in ('fact','history'):
                key=command['key'];fact_owner,personal=self._fact_owner(db,cid,profile,command.get('scope'),key)
                if fact_owner is None:return '请先明确选择个人档案，才能查询个人记忆。'
                if op=='fact':
                    from common.fact_answers import fact_reply
                    table,column=('profile_facts','profile_id') if personal else ('conversation_facts','conversation_id')
                    row=db.execute('SELECT value FROM '+table+' WHERE '+column+'=? AND key=?',(fact_owner[2:],key)).fetchone()
                    return fact_reply(key,row[0] if row else None,personal)
                index=command.get('index')
                rows=db.execute('SELECT value,recorded,superseded FROM memory_fact_versions WHERE owner=? AND key=? ORDER BY source_seq DESC LIMIT ? OFFSET ?',
                    (fact_owner,key,1 if index else 2,index-1 if index else 0)).fetchall()
"""
edit('common/memory_controls.py',old,new)
edit('common/memory_controls.py',"                pieces=[datetime.fromtimestamp",
"""                if index:
                    row=rows[0]
                    return key+'第'+str(index)+'条（从新到旧）：'+datetime.fromtimestamp(row['recorded'],zone).strftime('%Y-%m-%d')+'录入的'+('当前值' if row['superseded'] is None else '旧值')+'是'+row['value']+'。'
                pieces=[datetime.fromtimestamp""")
edit('tools/board_model_host.py','self.conversations.attach_sources(meta,sources,**profile_options(pid))',
     'self.conversations.attach_sources(meta,sources,mark_complete=True,**profile_options(pid))')
edit('tools/voice_channel_source.py',"reuse_history=bool(board_exchange is None and durable is None and latency.get('reuse_history')",
     "reuse_history=bool(board_exchange is None and conversation is None and memory_reply is None and latency.get('reuse_history')")
edit('tools/voice_channel_source.py',"if board_exchange is None and durable is None and hasattr(models,'history_with_preferences'):",
     "if board_exchange is None and conversation is None and memory_reply is None and hasattr(models,'history_with_preferences'):")
edit('common/voice_service_capabilities.py',"SERVICE_REVISION = 'voice-memory-controls-20261029-r3'","SERVICE_REVISION = 'voice-dialogue-memory-20261029-r4'")
edit('common/voice_service_capabilities.py',"'fact_revision_history':1}","'fact_revision_history':1,'natural_fact_answers':1,'memory_source_coverage':1}")
edit('common/voice_service_capabilities.py',"SOURCE_FILES = (\n","SOURCE_FILES = (\n    'common/fact_answers.py',\n")
for name,entry in plan['files'].items():entry['candidate']=hashlib.sha256((C/name).read_bytes()).hexdigest()
plan['status']='CANDIDATE_IMPLEMENTED';(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':plan['status'],'candidate_files':len(plan['files']),'production_unchanged':True}))

