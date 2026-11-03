"""Stage documentary evidence and execute the existing public offline Skill only."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]
SHARED = Path('E:/Win共享文件')
OLD = SHARED/'协作任务/2026-11-02_dual_reports'
SKILL = SHARED/'协作任务/2026-11-02_pynq_skill/skill/pynq-contract-testgen'
STATE = SHARED/'语音共享文件/deliverables/2026-11-02_5090_deployment'
WIRING = SHARED/'output/hardware/wiring_review_20261102'
EVIDENCE = OUT/'attachments/evidence'
DATE = '2026-11-02'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    manifest = {'schema':'amd-report-v2-sources-1','client_date':DATE,
                'client_timezone':'America/Los_Angeles','board_accessed':False,
                'runtime_or_models_changed':False,'entries':[]}
    old_index = read_json(OLD/'source_index.json')
    for row in old_index['entries']:
        src = OLD/row['report_copy']
        data = src.read_bytes()
        assert sha(data)==row['sha256'], src
        dest = EVIDENCE/src.name
        dest.write_bytes(data)
        manifest['entries'].append({**row,'source_path':str(src),
                                   'original_engineering_path':row['source_path'],
                                   'report_copy':dest.relative_to(OUT).as_posix(),
                                   'scope':('历史快照，不能作为当前状态；' if row['id'] in ['V11','V17'] else '')+row['scope']})

    def capture(sid, path, dest, scope, transform=None):
        data = path.read_bytes()
        if transform:
            included = (json.dumps(transform(json.loads(data.decode('utf-8-sig'))),ensure_ascii=False,indent=2)+'\n').encode('utf8')
        else:
            included = data
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(included)
        manifest['entries'].append({'id':sid,'source_path':str(path),'source_sha256':sha(data),
                                   'report_copy':dest.relative_to(OUT).as_posix(),
                                   'sha256':sha(included),'bytes':len(included),'scope':scope,
                                   'transformation':'documented field extraction' if transform else 'byte-preserving copy'})
        return json.loads(data.decode('utf-8-sig')) if path.suffix=='.json' else None

    def progress_extract(d):
        keys=['schema','updated_utc','client_date','timezone','overall','full_five_component_human_acceptance_complete',
              'full_three_minute_integrated_demo_ready','voice_owner_match_human_accepted','voice_field_calibration_complete',
              'face_voice_association_required','face_voice_association_status']
        return {**{k:d[k] for k in keys if k in d},
                'modules':[{k:r[k] for k in ['module','status','facts','user_acceptance_complete'] if k in r} for r in d['modules']],
                'scope':'本文件为保存状态的字段摘录；没有新设备查询或验收动作'}

    progress = capture('V29', STATE/'project_progress_20261102/PROJECT_PROGRESS.json',
                       EVIDENCE/'v29_current_progress_extract.json','保存进度；独立人脸/声纹、转轴用户验收与未完成项',progress_extract)
    def axis_extract(d):
        keys=['schema','updated_utc','status','current_release','latest_user_feedback','next_action',
              'user_acceptance','functional_acceptance','human_acceptance']
        return {k:d[k] for k in keys if k in d}
    capture('V30',STATE/'AXIS_CURRENT_HANDOFF.json',EVIDENCE/'v30_axis_acceptance_extract.json',
            '转轴功能行为的用户验收；不扩大为机械精度或新遥测验收',axis_extract)
    voice = capture('V31',STATE/'dialogue_latency_20261101/TWO_TURN_LATENCY.json',
                    EVIDENCE/'v31_two_turn_latency.json','先前启动中两轮真人完整播放；软件事件时延')
    screenshot = Path('C:/Users/REVO1/AppData/Local/Temp/codex-clipboard-612df775-a410-4f2b-8c29-022ededc657e.jpg')
    capture('R7_SCREENSHOT',screenshot,OUT/'requirements/amd_3353.jpg','用户提供的AMD设计报告七项要求截图')
    (OUT/'figures').mkdir(exist_ok=True)
    for name in ['vision_pipeline.png','dialogue_memory.png','motion_protocol.png','hardware_connections.png']:
        shutil.copyfile(OLD/'figures'/name,OUT/'figures'/name)
    for name in ['kv260_servo_wiring_v1.svg','kv260_system_connections_v1.svg','kv260_servo_wiring_v1.png',
                 'kv260_system_connections_v1.png','kv260_wiring_review_v1.pdf','connections.json','sources.json','report_caption.txt']:
        p=OUT/'attachments/wiring'/name;p.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(WIRING/name,p)

    # The existing Skill contains synthetic HWH and independent mock/golden references.
    target=OUT/'skill/pynq-contract-testgen'
    shutil.copytree(SKILL,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'),dirs_exist_ok=False)
    before={p.relative_to(target).as_posix():sha(p.read_bytes()) for p in target.rglob('*') if p.is_file()}
    save_json(OUT/'attachments/validation/skill_source_manifest.json',before)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
    unit=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],cwd=target,
                        env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace')
    unit_log=OUT/'attachments/validation/unit_tests_windows.log'
    unit_log.write_text(unit.stdout,encoding='utf8')
    count=re.search(r'Ran (\d+) tests? in',unit.stdout)
    assert unit.returncode==0 and count,unit.stdout
    run_dir=OUT/'attachments/validation/windows_offline_01'
    process=subprocess.run([sys.executable,'-B','scripts/reproduce.py','--out',str(run_dir)],cwd=target,
                           env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace')
    (OUT/'attachments/validation/reproduce_windows.log').write_text(process.stdout,encoding='utf8')
    summary=read_json(run_dir/'summary.json')
    assert process.returncode==0 and summary['status']=='PASS',process.stdout
    assert not summary['board_verified'] and not summary['pynq_imported']
    assert {r['name']:r['cases'] for r in summary['examples']}=={'adder':36,'crc32':37}
    after={p.relative_to(target).as_posix():sha(p.read_bytes()) for p in target.rglob('*') if p.is_file()}
    assert before==after,'Skill source was modified by validation'
    new_validation={'schema':'amd-report-v2-fresh-offline-validation-1','client_date':DATE,
                    'python':platform.python_version(),'platform':platform.platform(),
                    'unit_tests_passed':int(count.group(1)),'unit_tests_exit_code':unit.returncode,
                    'examples':summary['examples'],'status':'PASS','board_verified':False,
                    'pynq_imported':False,'source_unchanged':True,
                    'scope':'同一套既有测试在Windows新目录复跑；不增加测试覆盖，也不声称PYNQ或跨板通过'}
    save_json(OUT/'attachments/validation/current_validation.json',new_validation)
    manifest['entries'].append({'id':'V32','report_copy':'attachments/validation/current_validation.json',
                               'sha256':sha((OUT/'attachments/validation/current_validation.json').read_bytes()),
                               'scope':'本次Windows Python3.12离线复现与单元测试；原始日志同目录'})

    # Exact excerpts from the visible conversation, rather than reconstructed historical prompts.
    case={'schema':'visible-ai-collaboration-excerpt-1','case_id':'ai06_wiring_documentation',
          'date':DATE,'source':'本对话可见用户消息、公开答复和工具反馈摘录',
          'record_type':'verbatim_excerpts_and_observed_tool_feedback','tool':'Codex','model_build_version':None,
          'user_prompt_excerpt':'这个怎么做，按照我这个盘里面的资料，你可以帮我做一下么',
          'assistant_visible_reply_excerpt':'我会按盘里的接线资料和 FPGA 引脚约束，先做一份可放进报告的接线图和逐线接线表。资料能确认的内容会直接标出，尚未核实的实物端子会标为“待核对”，重点处理旧图 H12 与宽版约束 E10 的差异。',
          'evidence_based_decision':'宽版约束确认servo_pwm在E10；J2.3仅按B03参考映射标注；不从资料推断实物已经核线。',
          'observed_tool_error_excerpt':"ValueError: invalid literal for int() with base 10: 'white'",
          'actual_correction':'c.setFillColor(colors.toColor(fill))',
          'layout_corrections':['将电源域标题移出导线区','分开W10与W11标签','将舵机端口文字移入框内','将PWM/E10标签移离连线'],
          'verification_source':'attachments/wiring/validation_original.json',
          'scope':'证明本次文档生成与工具纠错；不是FPGA算法开发历史的逐字导出；未记录的模型构建版本保持未知'}
    ai_path=OUT/'attachments/ai_collaboration/wiring_case_verbatim.json'
    save_json(ai_path,case)
    shutil.copyfile(WIRING/'validation.json',OUT/'attachments/wiring/validation_original.json')
    manifest['entries'].append({'id':'V33','report_copy':ai_path.relative_to(OUT).as_posix(),
                               'sha256':sha(ai_path.read_bytes()),'scope':case['scope']})
    historical=SHARED/'协作任务/2026-11-02_AI辅助学习记录'
    for name in ['ai_learning_record_review.md','conversation_excerpts.md','evidence_index.json']:
        dest=OUT/'attachments/ai_collaboration'/name
        shutil.copyfile(historical/name,dest)

    yunet=read_json(EVIDENCE/'v04_yunet_board.json')['core']['latencies']
    sface=read_json(EVIDENCE/'v05_sface_three_model_board.json')['core']['latencies']
    model_rows=[]
    for name,n,cpu,dpu,evid in [('YuNet',40,yunet['cpu_fp32'],yunet['dpu_int8_with_cpu_postprocess'],'V04'),
                               ('SFace',8,sface['arm_cpu_fp32'],sface['dpu_int8_with_input_output_conversion'],'V05')]:
        model_rows.append({'model':name,'samples':n,'cpu_median_ms':cpu['median_ms'],'cpu_p95_ms':cpu['p95_ms'],
                           'dpu_median_ms':dpu['median_ms'],'dpu_p95_ms':dpu['p95_ms'],
                           'median_ratio':cpu['median_ms']/dpu['median_ms'],'source':evid})
    def resource(name):
        text=(EVIDENCE/name).read_text(encoding='utf8')
        values={}
        for field,key in [('CLB LUTs','lut'),('CLB Registers','ff'),('Block RAM Tile','bram_tile'),('URAM','uram'),('DSPs','dsp')]:
            m=re.search(r'^\|\s*'+re.escape(field)+r'\s*\|\s*([\d.]+)',text,re.M)
            assert m,(name,field)
            val=float(m.group(1));values[key]=int(val) if val.is_integer() else val
        return values
    metrics={'schema':'amd-report-v2-metrics-1','model_paths':model_rows,
             'resource_before':resource('v01_narrow_utilization.rpt'),'resource_after':resource('v02_wide_utilization.rpt'),
             'sface_quality':read_json(EVIDENCE/'v06_sface_quality.json')['models'],
             'compact_fields':read_json(EVIDENCE/'v08_compact_fields_profile.json')['summary'],
             'voice_turns':voice['turns'],'voice_means_ms':voice['means_ms'],
             'fresh_offline_skill':new_validation}
    save_json(OUT/'data/metrics.json',metrics)
    save_json(OUT/'data/project_snapshot.json',progress_extract(progress))
    manifest['external_primary_sources']=[
        {'id':'R1','url':'https://arxiv.org/abs/2107.08430','title':'YOLOX','checked':DATE},
        {'id':'R2','url':'https://arxiv.org/abs/2110.06864','title':'ByteTrack','checked':DATE},
        {'id':'R3','url':'https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/README.md','title':'OpenCV Zoo YuNet','checked':DATE},
        {'id':'R4','url':'https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/README.md','title':'OpenCV Zoo SFace','checked':DATE},
        {'id':'R5','url':'https://xilinx.github.io/Vitis-AI/3.0/html/docs/reference/version_compatibility.html','title':'Vitis AI 3.0 compatibility','checked':DATE},
        {'id':'R6','url':'https://pynq.readthedocs.io/en/v3.1/pynq_package/pynq.overlay.html','title':'PYNQ Overlay API','checked':DATE},
    ]
    save_json(OUT/'source_index.json',manifest)
    print(json.dumps({'status':'MATERIALS_STAGED','skill_validation':new_validation,
                      'progress_snapshot_utc':progress['updated_utc'],'evidence_entries':len(manifest['entries'])},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
