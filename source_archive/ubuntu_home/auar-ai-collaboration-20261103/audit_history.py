from pathlib import Path
import collections
import datetime as dt
import hashlib
import json
import re
import sqlite3

ROOT = Path('/home/ghmd')
WORK = ROOT / 'auar-ai-collaboration-20261103'
CURRENT = '01a1a27e-86fe-78b2-8dff-053f28053090'


def redact(s):
    s = re.sub(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{12,}', '[密钥已脱敏]', s)
    s = re.sub(r'(?i)(authorization\s*[:=]\s*bearer\s+)\S+', r'\1[已脱敏]', s)
    s = re.sub(r'(?i)((?:api[_-]?key|access[_-]?token|password|passwd|密码)\s*[:=]\s*)[\"\']?[^\s\"\',;]{4,}', r'\1[已脱敏]', s)
    s = re.sub(r'\b(?:192\.168\.|10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)\d{1,3}(?:\.\d{1,3}){1,2}\b', '[局域网地址已脱敏]', s)
    return s


def user_text(item):
    return '\n'.join(p.get('text', '') for p in item.get('content', []) if p.get('type') in ('text', 'inputText'))


def iso(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat() if ts else None


def main():
    state = sqlite3.connect('file:/home/ghmd/.codex/state_5.sqlite?mode=ro', uri=True)
    state.row_factory = sqlite3.Row
    hist = sqlite3.connect('file:/home/ghmd/.codex/thread_history_1.sqlite?mode=ro', uri=True)
    hist.row_factory = sqlite3.Row
    threads = [dict(r) for r in state.execute('select id,title,created_at,updated_at,model,cli_version,cwd from threads order by created_at')]
    topic_pattern = re.compile(r'AURA|AUAR|KV260|FPGA|PYNQ|DPU|Vivado|Vitis|PetaLinux|雪妃|雾镜|舵机|转轴|声纹|SFace|YuNet|MCP01|音色|语音模型|人脸|跟随|YOLO|嵌入式|AMD|声源|OmniVoice|海报|参赛|赛题|竞赛|项目|大语言模型|大模型|LLM|GPU|量化|技术报告|语音|图像', re.I)
    all_records = []
    stats = collections.Counter()
    for row in hist.execute("select thread_id,turn_id,item_id,rollout_ordinal,created_at_ms,item_type,item_json from thread_items where item_type in ('userMessage','agentMessage') order by created_at_ms,rollout_ordinal"):
        item = json.loads(row['item_json'])
        text = user_text(item) if row['item_type'] == 'userMessage' else item.get('text', '')
        phase = 'user' if row['item_type'] == 'userMessage' else item.get('phase', '')
        if phase == 'final_answer':
            phase = 'final'
        if phase not in ('user', 'final'):
            continue
        stats[phase] += 1
        record = {k: row[k] for k in ['thread_id','turn_id','item_id','rollout_ordinal','created_at_ms']}
        record.update({'role':phase,'text':text})
        all_records.append(record)
    by_thread = collections.defaultdict(list)
    for r in all_records:
        by_thread[r['thread_id']].append(r)
    summaries = []
    for t in threads:
        rs = by_thread[t['id']]
        hits = sum(bool(topic_pattern.search(r['text'])) for r in rs)
        relevant = bool(topic_pattern.search(t['title'])) or hits >= 2
        title = t['title'].replace('\n', ' ')
        summary = {'thread_id': t['id'], 'created_utc': iso(t['created_at']), 'title': redact(title[:180]), 'model_last_recorded': t['model'], 'cli_version_last_recorded': t['cli_version'], 'project_relevant_heuristic': relevant, 'current_compilation_thread':t['id'] == CURRENT, 'user_items':sum(r['role']=='user' for r in rs), 'final_items':sum(r['role']=='final' for r in rs), 'keyword_items': hits}
        summaries.append(summary)
    history_lines = 0
    history_sessions = set()
    for line in (ROOT/'.codex/history.jsonl').open():
        try:
            ob=json.loads(line)
            history_lines += 1
            history_sessions.add(ob.get('session_id'))
        except json.JSONDecodeError:
            pass
    stats_dict = {'snapshot_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'thread_count':len(threads),'history_jsonl_items':history_lines,'history_jsonl_sessions':len(history_sessions),'selected_message_types':dict(stats),'project_threads_heuristic_including_current':sum(t['project_relevant_heuristic'] for t in summaries),'rollout_jsonl_files':len(list((ROOT/'.codex/sessions').rglob('*.jsonl'))),'earliest_thread_utc':iso(min(t['created_at'] for t in threads)),'latest_thread_utc':iso(max(t['created_at'] for t in threads)),'reasoning_read_or_exported':False}
    (WORK/'history_stats.json').write_text(json.dumps(stats_dict,ensure_ascii=False,indent=2))
    (WORK/'thread_index.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2))
    # Only sanitized task summaries are persisted. Complete source texts remain in memory.
    with (WORK/'message_catalog.jsonl').open('w') as out:
        for r in all_records:
            text = r['text']
            entry = {k:v for k,v in r.items() if k!='text'}
            entry.update({'created_utc':iso(r['created_at_ms']/1000),'source_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'chars':len(text),'text_excerpt':redact(text[:6500] if r['role']=='final' else text[:2200])})
            out.write(json.dumps(entry,ensure_ascii=False)+'\n')
    print(json.dumps(stats_dict,ensure_ascii=False,indent=2))
    for t in summaries:
        print(t['created_utc'][:10],t['thread_id'][:8],t['user_items'],t['final_items'],'PROJECT' if t['project_relevant_heuristic'] else 'OTHER',t['title'][:110])


if __name__=='__main__':
    main()
