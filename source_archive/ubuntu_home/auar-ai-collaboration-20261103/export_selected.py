from pathlib import Path
import datetime as dt
import hashlib
import json
import sqlite3
from audit_history import redact, user_text, iso

WORK = Path(__file__).parent
SELECTION = [
    ('q01', '平台工件来源纠错', '01a0e0b2-f56b-7072-b26c-52b56fe40294'),
    ('q02', 'DFX共享状态修复', '01a1058b-a43c-76a3-b8d6-52e6eb072f7b'),
    ('q03', 'DFX断电冷启动验证', '01a105bc-3298-73c1-bfb3-7f4c904e9c4f'),
    ('q04', 'YuNet和SFace能否迁到DPU', '01a161a7-ce28-7eb2-8ef8-bea34fa0fb91'),
    ('q05', '双模型适配与固定输入验证', '01a161e7-0b65-7b13-af5d-a2dd7fc626b1'),
    ('q06', '人脸准入共享锁缺陷定位', '01a16777-0d6c-7693-a061-ed0bfec84f23'),
    ('q07', '自动恢复是否属于可接受抖动', '01a167e6-e44e-7db2-84d3-41d980350324'),
    ('q08', '第三次长尾推翻早期判断', '01a16820-0ab6-7d62-aa30-3814d6f808b1'),
    ('q09', '独立AI补丁及测试公式再核验', '01a1682f-963e-7152-8ea2-e2adead83bf3'),
    ('q10', '降低人脸刷新率的反例', '01a17d0d-141c-7ca1-8d55-c688992a2595'),
    ('q11', 'v14连续快回中与用户反馈', '01a17d48-7165-7a10-b07e-2a00d49a4994'),
    ('q12', '舵机范围和语音延迟的需求', '01a182d0-a5fa-71c0-a76d-3a00745a9181'),
    ('q13', '语音延迟阶段定位', '01a18682-7855-7022-9121-02d6809ebd8d'),
    ('q14', '语音延迟开关加载后的结果', '01a187b1-fb97-7e20-8ee9-7c0eee3384e7'),
    ('q15', '同一TTS模型更换后端的纠错', '01a187fc-ba4f-7932-a54e-bbbb2d2b5e8d'),
    ('q16', '板端记忆与关键词检索问题', '01a18c33-cd14-7dfe-8582-bf0ab64d234c'),
    ('q17', '通用PYNQ Skill离线实现', '01a19bf2-46a7-7e81-804d-27fc36c29bc3'),
    ('q18', '工程布局从示意目录改为真实运行根', '01a1a055-c662-7d10-8f5f-d945a19595d4'),
    ('q19', '板端玩偶自启动与提速边界', '01a18a7a-2a0b-7ce2-af64-a715d005ef1b'),
    ('q20', '显示故障观察和动态画面核对', '01a18562-893c-7c42-8392-80b6bfcc7071'),
    ('q21', 'Ubuntu与Windows共享任务及回执', '01a14e12-8375-7430-8de3-6d95bcc4bebc'),
    ('q22', '历史DCP与新构建的来源核查', '01a19feb-308d-7580-bc2b-542488ca577e'),
]


def main():
    hist = sqlite3.connect('file:/home/ghmd/.codex/thread_history_1.sqlite?mode=ro', uri=True)
    hist.row_factory=sqlite3.Row
    meta = sqlite3.connect('file:/home/ghmd/.codex/state_5.sqlite?mode=ro', uri=True)
    selected=[]
    for qid,topic,turn in SELECTION:
        rows=hist.execute("select thread_id,turn_id,item_id,rollout_ordinal,created_at_ms,item_type,item_json from thread_items where turn_id=? and item_type in ('userMessage','agentMessage') order by rollout_ordinal",(turn,)).fetchall()
        if not rows:
            if qid=='q16':
                rows=hist.execute("select thread_id,turn_id,item_id,rollout_ordinal,created_at_ms,item_type,item_json from thread_items where thread_id like '01a18c33%' and item_type in ('userMessage','agentMessage') order by rollout_ordinal").fetchall()
            else:
                raise RuntimeError('Missing selection '+qid)
        for row in rows:
            ob=json.loads(row['item_json'])
            role='user' if row['item_type']=='userMessage' else ob.get('phase')
            if role not in ('user','final_answer'):
                continue
            original=user_text(ob) if role=='user' else ob.get('text','')
            public=redact(original)
            model,cli=meta.execute('select model,cli_version from threads where id=?',(row['thread_id'],)).fetchone()
            record={k:row[k] for k in ['thread_id','turn_id','item_id','rollout_ordinal','created_at_ms']}
            record.update({'selection_id':qid,'topic':topic,'role':'user' if role=='user' else 'assistant','phase':role,'created_utc':iso(row['created_at_ms']/1000),'created_bjt':dt.datetime.fromtimestamp(row['created_at_ms']/1000,dt.timezone(dt.timedelta(hours=8))).isoformat(),'source_db':'thread_history_1.sqlite','source_table':'thread_items','source_item_json_sha256':hashlib.sha256(row['item_json'].encode()).hexdigest(),'source_text_sha256':hashlib.sha256(original.encode()).hexdigest(),'export_text_sha256':hashlib.sha256(public.encode()).hexdigest(),'redacted':public!=original,'model_last_recorded':model,'cli_version_last_recorded':cli,'text':public})
            selected.append(record)
    (WORK/'selected_conversations.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected))
    for qid,topic,turn in SELECTION:
        rs=[r for r in selected if r['selection_id']==qid]
        print(qid,topic,len(rs),'messages',sum(len(r['text']) for r in rs),'chars',[(r['role'],r['text'][:80].replace('\n',' ')) for r in rs])
    print('TOTAL',len(selected),'messages',sum(len(r['text']) for r in selected),'chars')


if __name__=='__main__':
    main()
