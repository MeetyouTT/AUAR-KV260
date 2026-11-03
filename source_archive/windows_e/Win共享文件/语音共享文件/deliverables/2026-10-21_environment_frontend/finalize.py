"""Archive this isolated evaluation without copying models or private data."""
import hashlib,json,shutil,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
WORKSPACE=PROJECT.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
pc=read(HERE/'pc_benchmark.json')
sdk=read(HERE/'board_sdk_benchmark.json')
stream=read(HERE/'stream_transport_probe.json')
before=read(HERE/'board_inventory_before.json');after=read(HERE/'board_inventory.json')
assert before['runtime']==after['runtime'] and before['files']==after['files']
assert after['ui']['monitor_enabled'] is True and after['ui']['audio_output_state']=='IDLE_READY'
names=['aura/board/runtime/audio/silero_gate.py','aura/board/runtime/audio/vad.py',
       'aura/board/runtime/audio/automatic_capture.py','aura/tests/framework/test_silero_gate.py']
hashes={}
for name in names:
    data=(PROJECT/name).read_bytes();hashes[name]=hashlib.sha256(data).hexdigest()
    target=HERE/'candidate_sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
for name in ('SILERO_LICENSE','SHERPA_LICENSE','GTCRN_LICENSE'):
    target=HERE/'licenses'/name;target.parent.mkdir(exist_ok=True)
    shutil.copyfile(Path('D:/AIModels/audio-frontend-eval-20261021')/name,target)
summary={
 'date':'2026-10-21','status':'ISOLATED_COMPONENTS_AND_PC_STREAM_PATH_VERIFIED_PRODUCTION_UNCHANGED',
 'active_runtime':after['runtime'],'monitor_enabled':True,'production_source_hashes_unchanged':True,
 'candidate_default_enabled':False,'production_integration_ready':False,
 'pc_tests_passed':117,'pc_tests_skipped':1,'new_boundary_tests':10,
 'public_or_generated_cases':len(pc['cases']),
 'non_speech_generated_cases_including_silence':5,
 'non_speech_starts':{name:sum(len(c['results'][name]['speech_starts']) for c in pc['cases'] if c['expected']=='non_speech') for name in pc['cases'][0]['results']},
 'gtcrn_chinese_variants':12,'gtcrn_v5_all_twelve_single_completed_segment':all(len(c['silero_v5_after']['segments'])==1 and not c['silero_v5_after']['still_active_at_end'] for c in pc['gtcrn'] if c['name'].startswith('public_')),
 'board_stock_sdk_realtime_qualified':False,
 'board_stock_sdk_wall_rtf_range':[min(x['wall_rtf'] for x in sdk['rows']),max(x['wall_rtf'] for x in sdk['rows'])],
 'selected_next_architecture':'Board capture/AEC and ownership; stock CPU SDK on PC with bounded streaming integration.',
 'temporary_stream_probe':stream,
 'existing_ecapa_reused':True,'speaker_field_calibrated':False,'speaker_database_changed':False,
 'microphone_opened_by_operator':False,'private_recordings_read':False,'production_restarted':False,
 'human_environment_verified':False,'llm_weights_copied':False,
 'remaining':['Capture/request/generation ownership and cancellation integration','Live delay/preroll alignment','Actual microphone UI/CPU load','Room noise and competing speech acceptance','Separate speaker threshold calibration'],
 'evidence':['asset_manifest.json','pc_benchmark.json','asr_public_comparison.json','board_benchmark_v4.json','board_benchmark_v5.json','board_sdk_benchmark.json','stream_transport_probe.json','speaker_public_baseline.json','tests_pc.log','board_inventory.json'],
}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(HERE/'source_manifest.json').write_text(json.dumps({'files':hashes,'deployment':False,'baseline_runtime':after['runtime']},indent=2)+'\n',encoding='utf-8')
with zipfile.ZipFile(HERE/'verified_candidate_sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in names:archive.write(HERE/'candidate_sources'/name,name)
    for folder in ('before','licenses'):
        for file in (HERE/folder).rglob('*'):
            if file.is_file():archive.write(file,str(file.relative_to(HERE)))
    for name in ('README.md','source_manifest.json','verification_summary.json'):
        archive.write(HERE/name,name)


def note(path,text,after_title=False):
    marker='<!-- environment-front-end-evaluation-20261021 -->'
    old=path.read_text(encoding='utf-8-sig')
    if marker in old:return
    value=marker+'\n'+text+'\n\n'
    if after_title:
        title,rest=old.split('\n',1);old=title+'\n\n'+value+rest.lstrip('\n')
    else:old=value+old
    path.write_text(old,encoding='utf-8')


note(PROJECT/'AGENTS.md','- 用户“继续”后已完成成熟前端隔离验证，尚未部署：GTCRN+Silero v5，35公开/生成场景/19降噪对照；4类生成噪声起点从原能量4→0，12中文变体组合均单段收尾，但强噪声仍词差，不能写真实环境/电视拒绝通过。板端官方SDK组合RTF约1.26–1.51不实时，选择电脑CPU方向；337个20ms公开帧板端→PC→板端往返P95 3.71ms/最大6.29ms/0包超20ms，仅处理与传输非算法/说完判断/回答延迟。117相关回归通过/1跳过，10新边界；共享silero_gate及vad/automatic_capture分类器注入默认未启用。实际922dab入口与6文件哈希保持、监听true/IDLE_READY，PC/板端生产无重启/无新常驻服务。板端原ORT Python包独立导入abort；官方ORT1.17.3/sherpa1.13.8只解包到/home/root/aura-environment-eval-20261021隔离目录，勿误称系统包已替换。模型/包在D:/AIModels/audio-frontend-eval-20261021；现有ECAPA禁网公开双人复测，未读个人库或调阈值。下一步先做流式归属/取消/有界队列及延迟前导对齐，再真实负载，不把临时TCP实验直接常驻。用户问三路线区别，尚未选择商业授权/购买硬件。证据deliverables/2026-10-21_environment_frontend/README.md、verification_summary.json。')
text='[环境声成熟前端隔离验证（2026-10-21）](../语音共享文件/deliverables/2026-10-21_environment_frontend/README.md)：GTCRN＋Silero v5及现有ECAPA复用验证完成。板端组合不实时，电脑CPU流式路径337帧往返P95约3.71ms（不含算法/回答延迟）。117相关回归/1跳过；真实环境和说话者过滤尚未验收，正式922dab入口、监听及回声保护保持。未新增个人录音/模型服务，未部署候选。'
note(WORKSPACE/'语言模型分析/README.md',text)
note(WORKSPACE/'语言模型分析/环境干扰与声纹_成熟方案调研_20261021.md',text,True)
print(json.dumps({'status':summary['status'],'runtime':after['runtime'],'production_changed':False,'candidate_files':len(names)},ensure_ascii=False))
