"""Record tested code, with activation and genuine-photo acceptance kept explicit."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
read=lambda name:json.loads((HERE/name).read_text(encoding='utf-8'))
c=read('candidate.json');p=read('preflight.json');gallery=read('review_export_test.json')
assert c['tests_passed'] and c['preflight_passed']
assert all(p[key] for key in ('real_models_passed','bootstrap_passed','widget_passed'))
assert '152 passed' in (HERE/'tests_pc.log').read_text(encoding='utf-8')
assert 'Ran 215 tests' in (HERE/'tests_board.log').read_text(encoding='utf-8')
deployment=read('deployment.json') if (HERE/'deployment.json').is_file() else None
verification=read('source_verification.json') if (HERE/'source_verification.json').is_file() else None
active=bool(deployment and deployment.get('status')=='ENROLLMENT_PHOTO_ARCHIVE_ENABLED_EXISTING_IDENTITY_PRESERVED' and verification)
c['activated']=active
(HERE/'candidate.json').write_text(json.dumps(c,indent=2),encoding='utf-8')
manifest={}
with zipfile.ZipFile(HERE/'tested_candidate_source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,expected in c['files'].items():
        raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected,name
        archive.writestr(name,raw);manifest[name]={'sha256':expected,'bytes':len(raw)}
    archive.writestr('candidate_source_manifest.json',json.dumps(manifest,indent=2))
    archive.writestr('local_config/board_identity.json',(ROOT/'aura/config/board_identity.json').read_bytes())
(HERE/'candidate_source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
status='ENROLLMENT_PHOTOS_ACTIVE_AWAITING_FRESH_USER_CAPTURE' if active else 'TESTED_ENROLLMENT_PHOTOS_NOT_ACTIVE_BOARD_CONNECTION_UNAVAILABLE'
board_path='/home/root/.local/share/aura/enrollment_photos'
pc_path=ROOT/'身份登记照片'
summary={'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':status,'user_explicitly_authorized_future_enrollment_photo_retention':True,
    'code_tests_passed':{'windows':152,'linux':215},'original_real_models_temporary_archive_passed':True,
    'temporary_public_test_pngs':27,'public_images_are_not_user_enrollment_photos':True,
    'offline_export_and_final_validation_labels_passed':gallery['status']=='PASS_SYNTHETIC_GALLERY_EXPORT',
    'candidate_runtime':c['runtime'],'activated':active,'board_photo_directory':board_path,
    'pc_review_directory_on_export':str(pc_path),'image_size':[112,112],
    'maximum_sample_photos_per_session':192,'separate_selected_copy':True,
    'outcomes_retained':['committed','failed','cancelled','interrupted'],
    'ordinary_recognition_photos_saved':False,'full_camera_frames_saved':False,
    'names_or_embeddings_exported':False,'threshold':.8,'ambiguity_margin':.1,
    'matcher_or_voice_pipeline_changed':False,'actual_new_user_photos_captured':False,
    'actual_user_photo_review_passed':None,'historical_missing_photos_recoverable':False,
    'activation_guard':'idle conversation; no active enrollment; preserve original UI/voice/DB and DPU config',
    'database_verified_at_activation':verification['database'] if active else None,
    'database_last_confirmed_before_connection_failure':{'identities':1,'templates':1,'revision':14},
    'camera_pid':verification['camera_pid'] if active else None,
    'llm_data_stays_external_to_shared_directory':True}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
state=('**已加载存图功能；等待一次新的真实登记来查看照片。**' if active else
       '**开发和预检已通过，但尚未加载到正式相机服务。** 当前板卡SSH握手、相机8790和界面8783均超时；电脑8792仍ready。此前的预检确实在板端通过，本次连接失败发生在正式切换之前。未执行相机停止或服务切换，待连接恢复后继续。')
text=f'''# 身份登记人脸照片保存与查看

{state}

用户2026-10-19明确要求将后续身份登记照片保存在本地或板卡供查看。这项明确授权覆盖本项目此前“未来不默认留照片”的约定，仅对登记时的人脸小图启用；普通识别不持续存图。

## 保存内容和位置

- 板卡持久目录：`{board_path}/<32位登记会话ID>/`，目录0700、文件0600。每轮独立文件夹，不自动删除失败或取消轮次，重启后可读取上一轮。
- 采样图：`frame_*.png`，原样保存实际送入SFace的112×112对齐人脸。最多192张，达到上限时清单标明截断；不保存全幅相机画面、上半身、视频、姓名或特征向量。
- 最终模板：`selected.png`，实际选中帧的原始PNG副本。仍只将一份实际特征存入身份库，存图不增加模板数或修改识别逻辑。
- `manifest.json`标明每张图的帧ID、原始SHA256、几何姿态、清晰度、采集/姿态拒绝/质量拒绝/验证通过或失败，以及真正最终连续5张验证图的ID和分数。失败过的旧验证帧不会被标成最终5张。
- `latest.json`指向最近轮次。只有真实身份库提交成功才标`committed`；失败、取消和重启中断分开标注。存图I/O异常通过健康接口计数和报错，不改变身份识别门槛或冒报已保存身份。

电脑导出目录：`{pc_path}/<会话ID>/`。本目录`export_latest.py`将板卡已存小图校验后复制到电脑，生成`照片总览.html`和`照片预览.md`，标注最终模板、采集图和最终独立验证图。HTML离线查看，点击图片看原始112像素图；不是生成、修复或放大后的替代图。

## 验证范围

Windows152项、Linux215项通过。原YuNet→112对齐→Windows CPU SFace→临时SQLite登记/识别/失脸预检通过，临时目录实际保存27张公开测试图，逐张核对112×112，最终模板与后5张独立验证来源分开。原GTK组件预检通过。离线总览合成小图测试通过，核对字节保真、5张验证标注及拒绝路径越界。公开测试图和合成图不是用户登记照片，未复制到正式用户照片目录。

本次不修改0.80相似度、0.1图库分差、正脸模板选择、连续5张独立验证、固定锚点/来源/库修订检查、明确更新确认。保留原YOLOX-Nano/ByteTrack/DPU/FPGA和Paraformer→原27B IQ4_XS/2048→OmniVoice16及五项语音延迟参数，LLM数据仍D盘。

## 接续步骤

1. 连接恢复后运行`stop_for_reload.py`，只在对话空闲且没有登记时正常停止监听。
2. 运行`activate_camera.py`切换已测试候选，再运行`verify.py`核对实际源码、配置、私有目录和未变的身份库；`record.py`更新本页状态。只重载相机，不重启UI或电脑模型服务，失败自动恢复上一相机版本。
3. 加载完成后，用户点“开始对话”，说“帮我登记身份，我叫……”（原称呼），复述后说“确认更新登记”。按原语音提示自然看镜头，验证时正对稍停。照片从原确认后的真实采样开始保存；无需末尾确认。
4. 运行`export_latest.py`导出真实采样，即使本轮验证失败也可以查看，并向用户展示实际照片及结果。此前未保存的历史照片无法补回，不能把当前截图或公开测试素材称为历史登记照片。

候选：`{c['runtime']}`。最后确认用户库1身份/1模板/修订14；当前实时值以激活后`source_verification.json`为准，连接失败期间未重新核对。

证据：`candidate.json`、`tests_pc.log`、`tests_board.log`、`preflight.json`、`real_models.log`、`review_export_test.json`、`connection_check.json`和`verification_summary.json`。`tested_candidate_source.zip`是已预检候选源码；只有正式加载核对后生成的`verified_source.zip`才代表活动相机源码。两者均不含模型权重、身份数据库、姓名、特征或现场照片。

加载后的回退用`rollback.py`恢复上一相机unit，保留身份库、照片档案和UI；不恢复已经删除的身份。当前若尚未激活，无需执行回退。
'''
(HERE/'README.md').write_text(text,encoding='utf-8')
marker='enrollment-photo-archive-20261019'
def note(path,content):
    raw=path.read_text(encoding='utf-8')
    pattern=r'<!-- '+marker+r' -->.*?<!-- /'+marker+r' -->\s*'
    raw=re.sub(pattern,'',raw,flags=re.S)
    path.write_text('<!-- '+marker+' -->\n'+content+'\n<!-- /'+marker+' -->\n\n'+raw,encoding='utf-8')
status_cn='已加载、真实新登记照片待采集' if active else '已开发预检、尚未激活，板卡SSH及8790/8783连接超时'
note(ROOT/'AGENTS.md',f'- 2026-10-19用户明确授权后续身份登记时保留人脸照片供查看；覆盖旧“不默认保存登记照片”约定。状态：{status_cn}。板卡目录`{board_path}`，每会话最多192张实际112×112对齐脸+selected原图副本/manifest，最终5张独立验证单独标注；失败/取消/中断留档，普通识别不持续存图。电脑按请求由export_latest.py校验复制到`身份登记照片/<sid>/`，生成离线总览。Windows152/Linux215、原公开模型临时27图及GUI/合成导出预检通过，不能当真人照片或真人识别已通过。候选`{c["runtime"]}`；未激活时正式仍front-template旧相机，不误写活动路径。保存特性不改0.80/0.1、单模板/5独立验证/明确更新及DPU/语音。最后库1/1/rev14，连接失败期间实时值未知；不补造历史照片。详见`deliverables/2026-10-19_enrollment_photo_archive/README.md`和verification_summary.json。LLM权重仍D盘，源码包不含私有照片/向量/库。')
note(ROOT/'README.md',f'> **2026-10-19 登记照片留档：{status_cn}。** 按用户要求仅保存112×112人脸，保留采集图、最终模板、最终5张验证图及失败轮次，导出后可看离线总览。Windows152/板端215项和真实模型预检通过；真实新照片尚未采集。[本轮状态和接续步骤](deliverables/2026-10-19_enrollment_photo_archive/README.md)。')
analysis=ROOT.parent/'语言模型分析';name='身份登记人脸照片保存与查看_20261019.md'
(analysis/name).write_text(text,encoding='utf-8')
note(analysis/'README.md',f'[身份登记照片保存与查看]({name})：{status_cn}，真实用户照片待采集；保留原语音与视觉配置。')
print(json.dumps({'status':status,'activated':active,'source_files':len(manifest),
    'board_photo_directory':board_path,'actual_new_user_photos_captured':False},ensure_ascii=False))
