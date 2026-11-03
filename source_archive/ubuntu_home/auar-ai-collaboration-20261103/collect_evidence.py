from pathlib import Path
import csv
import datetime as dt
import hashlib
import io
import json
import re
import zipfile
from audit_history import redact

WORK = Path(__file__).parent
OUT = Path('/home/ghmd/Win共享文件/协作任务/2026-11-03_ai_collaboration')
SHARED = Path('/home/ghmd/Win共享文件')
DEL = SHARED / '语音共享文件/deliverables'
COOP = SHARED / '协作任务'
LOG = Path('/home/ghmd/AMD_Smart/logs/daily')

SOURCES = [
 ('E03', '平台修复与历史冷启动验收', Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/BOARD_REPAIR_REPORT.md')),
 ('E04', '宽范围FPGA历史构建与板端部署', LOG/'2026-10-28-SYSTEM-PAN-WIDE.md'),
 ('E05', '9a4f源码重新构建与验证摘要', Path('/home/ghmd/下载/AUAR_方案A源码交付_9a4f_20261103/验证摘要.md')),
 ('E06', '9a4f源码RAR解包核验', Path('/home/ghmd/下载/AUAR_方案A源码交付_9a4f_20261103/archive_verification.json')),
 ('E07', '时序余量尝试与保留已验基线', LOG/'2026-11-03-SOURCE-TIMING-MARGIN-01a1a08b.md'),
 ('E08', '双模型DPU适配历史交付', DEL/'2026-10-21_dpu_vision_start/README.md'),
 ('E09', 'SFace公开独立量化质量评测', DEL/'2026-10-21_dpu_vision_start/evidence/sface-evaluation-report.json'),
 ('E10', 'YuNet公开FP32与INT8一致性', DEL/'2026-10-21_dpu_vision_start/evidence/yunet-evaluation-report.json'),
 ('E11', '三模型固定输入板端对照', DEL/'2026-10-21_dpu_vision_start/evidence/board-three-fixed.json'),
 ('E12', '共享锁失败候选及Event修复', LOG/'2026-10-23-YUNET-EVENT-SLOT-WAIT.md'),
 ('E13', 'VART实际绑定、诊断反例与成本边界', LOG/'2026-10-23-NATIVE-WAIT-DIAGNOSIS.md'),
 ('E14', '实际交给独立AI审查的历史提示词', DEL/'2026-10-23_deepseek_yunet_review/给DeepSeek的完整提示词.md'),
 ('E15', 'V14连续快回中与实体反馈', COOP/'2026-10-27_越界回中与断线恢复/V14_FPGA连续快回中.md'),
 ('E16', '降低人脸频率的软件反例', COOP/'2026-10-27_越界回中与断线恢复/FACE_REFRESH_RATE_REVIEW.json'),
 ('E17', 'LLM短字段配对测量', DEL/'2026-10-18_compact_reply_fields/paired_profile.json'),
 ('E18', 'LLM/TTS资源协调历史说明', DEL/'2026-10-29_parallel_interaction/README.md'),
 ('E19', '资源协调合并回归JUnit结果', DEL/'2026-10-29_parallel_interaction/final_tests.xml'),
 ('E20', '资源协调非缓存GPU观察', DEL/'2026-10-29_parallel_interaction/public_gpu_final_adaptive.json'),
 ('E21', '语音延迟开关加载和两轮结果', COOP/'2026-10-29_语音延迟修复/README.md'),
 ('E22', '同OmniVoice后端迁移的事实纠正', COOP/'2026-10-29_语音延迟修复/同OmniVoice板端迁移_可行性核查.md'),
 ('E23', '自然到期正文回收与摘要存储验证', DEL/'2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/continued_validation_20261101/RETENTION_RESULT.json'),
 ('E24', '否定语义摘要策略采用依据', DEL/'2026-10-30_board_owner/integration/dialogue_repair/memory_negation_model_validation_v24/ROOT_ADOPTION_R2_DECISION.json'),
 ('E25', '较新字幕、跟随和记忆交接原件', SHARED/'语音共享文件/AGENTS.md'),
 ('E26', '玩偶自启动提速候选与待验边界', COOP/'2026-10-29_玩偶自启动提速/README.md'),
 ('E27', 'HDMI冷启动显示对照与失败保留', COOP/'2026-10-28_冷启动闪屏接续/README.md'),
 ('E28', '视觉边界切页同步修复', COOP/'2026-10-29_边界切页同步/README.md'),
 ('E29', '通用PYNQ Skill使用与验证范围', COOP/'2026-11-02_pynq_skill/readme.md'),
 ('E30', 'PYNQ Skill离线测试原始结果', COOP/'2026-11-02_pynq_skill/skill/pynq-contract-testgen/evidence/offline_validation.json'),
 ('E31', '方案A真实运行根及布局修正', COOP/'2026-11-02_project_structure/rar_source_layout.md'),
 ('E32', '较新技术报告与自然负载观察记录', LOG/'2026-11-03-TECHNICAL-REPORT-01a1a1a5.md'),
 ('E33', '历史板端证据与新候选的分开登记', Path('/home/ghmd/下载/AUAR_上板资料扩充_9a4f_20261103/实测与参考对照说明.md')),
]


def public_text(s):
    s=redact(s)
    s=re.sub(r'(?i)([a-z]:[\\/]Users[\\/])[^\\/\s]+', r'\1[用户名已脱敏]', s)
    s=re.sub(r'(?i)(hostname=[\"\'])[^\"\']+', r'\1[设备名已脱敏]', s)
    # These are memory/session identifiers, not test values; exclude them from public snapshots.
    s=re.sub(r'("(?:seed_request_token|seed_scope_token|scope_token|request_token)"\s*:\s*")[^"]+"', r'\1[标识已脱敏]"', s)
    return s


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    (OUT/'evidence').mkdir(parents=True,exist_ok=True)
    entries=[]
    guide=next((SHARED/'参赛资料').glob('*.pdf'))
    original=guide.read_bytes()
    pages=Path('/tmp/auar_ai_record_guide.txt').read_text().split('\f')
    excerpt='\n\n'.join('PDF物理页%d（正文页%d）\n%s'%(n,n-3,pages[n-1]) for n in [23,24,25])
    p=OUT/'evidence/e01_guide_requirements.txt';p.write_text(excerpt)
    entries.append({'evidence_id':'E01','description':'用户指定指南第3.3节AI/Skill/报告要求','source_path':str(guide),'source_sha256':sha(original),'source_bytes':len(original),'snapshot':str(p.relative_to(OUT)),'snapshot_sha256':sha(p.read_bytes()),'transform':'仅提取物理23–25页；完整PDF保留在原处','verification':'原PDF本地提取，不查询网络新版本'})
    zpath=Path('/home/ghmd/下载/项目.zip')
    with zipfile.ZipFile(zpath) as z:
        names=['项目/README.md','项目/方案/AURA_KV260_完整实施方案_无声源定位版_2026-09-30.md','项目/方案/AURA_当前现状三人分工_2026-10-02.md','项目/aura_fpga/readme.md']
        for i,name in enumerate(names):
            b=z.read(name);s=b.decode('utf-8')
            snapshot=OUT/('evidence/e02_%02d_project_history.txt'%i)
            snapshot.write_text(public_text(s if i!=1 else s[:4300]))
            entries.append({'evidence_id':'E02-%d'%i,'description':'ZIP原始范围/职责/历史框架','source_path':str(zpath),'archive_member':name,'source_sha256':sha(b),'source_bytes':len(b),'snapshot':str(snapshot.relative_to(OUT)),'snapshot_sha256':sha(snapshot.read_bytes()),'transform':'完整文本脱敏' if i!=1 else '前4300字符节录并脱敏；属历史方案','verification':'读取ZIP原件；目标不作为现状'})
    for eid,desc,path in SOURCES:
        if not path.is_file():raise FileNotFoundError(path)
        raw=path.read_bytes();s=raw.decode('utf-8')
        transformation='全文文本脱敏；保留原始数值与结论'
        if eid=='E25':
            s='\n'.join(s.splitlines()[:65])+'\n\n[后文历史归档省略；来源SHA针对完整原文件。]\n'
            transformation='只截取开头65行当前交接及相邻历史上下文；脱敏'
        if eid=='E27' and len(s)>20000:
            s=s[:20000]+'\n\n[后文省略；完整原件见source_path。]\n'
            transformation='只截取前20000字符；脱敏'
        suffix=path.suffix.lower()
        if suffix not in ['.md','.json','.xml','.txt']:suffix='.txt'
        snapshot=OUT/('evidence/'+eid.lower()+'_source'+suffix)
        pub=public_text(s);snapshot.write_text(pub)
        entries.append({'evidence_id':eid,'description':desc,'source_path':str(path),'source_sha256':sha(raw),'source_bytes':len(raw),'snapshot':str(snapshot.relative_to(OUT)),'snapshot_sha256':sha(snapshot.read_bytes()),'transform':transformation,'redacted_or_excerpted':pub!=raw.decode('utf-8'),'verification':'本次仅读取原件和校验；工程测试归属原记录'})
    # Independently verify the earlier five-case index, preserving its exact artifact identity.
    oldbase=COOP/'2026-11-02_AI辅助学习记录'
    old=json.loads((oldbase/'evidence_index.json').read_text())
    old_results=[]
    for i,x in enumerate(old['entries'],1):
        path=(oldbase/x['relative_path']).resolve()
        if x['kind']=='archive_member':
            with zipfile.ZipFile(path) as z:b=z.read(x['member'])
        else:b=path.read_bytes()
        result={'evidence_id':'H%02d'%i,'prior_evidence_id':x['evidence_id'],'description':x['project_file'],'source_path':str(path),'archive_member':x.get('member'),'source_sha256':sha(b),'source_bytes':len(b),'prior_sha256_matches':sha(b)==x['sha256'],'snapshot':None,'verification':'原历史工程输入或结果逐字节复核；不认定为当前生产文件'}
        if not result['prior_sha256_matches']:raise ValueError('Historical evidence changed: '+x['evidence_id'])
        entries.append(result);old_results.append(result)
    (OUT/'source_index.json').write_text(json.dumps({'schema':'auar-ai-collaboration-source-index-v1','prepared_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'entries':entries,'historical_index_verified':len(old_results),'historical_mismatches':0,'board_or_model_operations_this_task':False},ensure_ascii=False,indent=2))
    cols=['evidence_id','description','source_path','archive_member','source_bytes','source_sha256','snapshot','snapshot_sha256','verification']
    with (OUT/'source_index.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');writer.writeheader();writer.writerows(entries)
    print(json.dumps({'source_entries':len(entries),'standalone_text_snapshots':sum(bool(x.get('snapshot')) for x in entries),'prior_index_entries_verified':len(old_results),'output':str(OUT)},ensure_ascii=False))


if __name__=='__main__':main()
