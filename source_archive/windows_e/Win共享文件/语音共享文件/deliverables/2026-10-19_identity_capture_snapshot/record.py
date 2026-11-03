"""Record the confirmed UI cancellation/source bug and guarded active fix."""
import datetime
import json
from pathlib import Path
import re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read=lambda name:json.loads((HERE/name).read_text(encoding='utf-8'))
c=read('candidate.json');d=read('deployment.json');v=read('source_verification.json');p=read('preflight.json')
assert c['activated'] and d['status']=='IDENTITY_CAPTURE_SOURCE_FIXED_PHOTO_CAMERA_PRESERVED'
assert p['capture_source_passed'] and d['database_hash_unchanged'] and d['camera_pid_preserved']
assert '182 passed' in (HERE/'tests_pc.log').read_text(encoding='utf-8')
assert 'Ran 222 tests' in (HERE/'tests_board.log').read_text(encoding='utf-8')
diagnosis=read('entry_diagnosis_before.json');samples=diagnosis['samples'];latest=samples[-1]
assert latest['ui_cache']['has_display_cancel_flag'] and latest['ui_cache']['validation_error']
summary={'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'CAPTURE_SOURCE_FIXED_PHOTO_CAMERA_ACTIVE_AWAITING_FRESH_USER_ENROLLMENT',
 'actual_user_failed_to_start_enrollment_before_fix':True,
 'before_failure_code':'face_unavailable','before_capture_snapshot_valid':False,
 'confirmed_root_cause':'SnapshotGate.read adds UI-only interaction_suppressed; strict capture-start validation rejects the decorated snapshot',
 'before_cache_link':latest['ui_cache']['link'],'before_cache_validation_error':latest['ui_cache']['validation_error'],
 'before_camera_start_available_samples':sum(bool(row['entry_capabilities']['identity_sample_start']) for row in samples),
 'before_camera_samples':len(samples),'fix':'capture provider uses freshly validated canonical source snapshot in memory',
 'display_cancel_mask_retained':True,'source_boot_ttl_epoch_target_and_explicit_consent_checks_retained':True,
 'pc_tests':182,'linux_tests':222,'windows_posix_mode_test_ran_on_linux':True,
 'actual_camera_source_preflight_passed':True,'live_user_new_enrollment_passed':None,
 'actual_user_photos_available':False,'user_photo_review_passed':None,
 'ui_runtime':c['runtime'],'camera_config':c['old_camera_config'],'camera_pid':v['camera_pid'],
 'camera_photo_service_preserved':True,'database_at_deployment':v['database'],
 'threshold':.8,'ambiguity_margin':.1,'photo_size':[112,112],
 'board_photo_directory':v['enrollment_photos']['directory'],
 'pc_review_directory':str(ROOT/'身份登记照片'),'matching_accuracy_not_yet_accepted':True,
 'voice_models_and_five_latency_flags_unchanged':True,'llm_data_stays_on_D_drive':True}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''# 语音登记入口：取消字幕标记导致人脸状态被拒

**修复已加载，照片保存服务保持启用；等待新的真实登记照片。** UI运行`{c['runtime']}`，相机仍`{c['old_camera_config']}`、PID {v['camera_pid']}（后续动态读取）。本次仅重载UI，未重载相机或电脑模型，身份库1身份/1模板/修订14及哈希保持。

## 已确认原因

用户反馈登记失败或无法开始。正式语音第18代返回`face_unavailable`，`capture_snapshot_valid=false`，照片0张、采样idle。随后8秒18次相机观测中17次允许开始采样，排除了“当时模型一直未就绪”的解释。界面缓存链接READY、快照约230ms，包含`interaction_suppressed=true`，严格协议校验报“服务状态字段不完整或未知”。

结束/取消交互后，`SnapshotGate.read()`在展示副本上加该标记并隐藏旧字幕；旧GUI把这个展示副本交给`ChannelConversationJobs.capture_started`。相机协议不允许该未知字段，录音起点身份因此变成None。后续即使当前人脸清晰，语音登记仍因缺录音起点来源拒绝进入采样。这轮失败没有进入保存照片的环节。

## 修复及验证

新增`UiServiceClient.identity_snapshot()`，在内存锁内读取原始协议缓存，检查连接READY、原启动ID、原时钟/TTL、原结构后返回独立副本；GUI把这个方法直接交给录音绑定。界面继续使用原展示副本，旧字幕仍隐藏。无新HTTP、文件、图片处理或模型调用进入UI/音频线程，不过滤任意未知字段来强行通过，不延长TTL、不使用旧授权。原同服务/相机/目标/库修订、单人、显式更新确认、0.80/0.1及独立5帧验证保持。

Windows182项和24个子用例通过，4个Linux专属用例在板端运行；Linux222项通过。新增7项复现取消后捕获失败、修复后可准备称呼且不写库，以及断线、过期、错启动、未知字段、换目标、返回副本独立和取消授权不复活。Windows首轮POSIX权限断言失败已保留在`tests_pc_linux_mode_initial.log`，生产权限未放宽。真实相机协议快照预检确认原展示消息仍校验失败、新来源可捕获、字幕仍屏蔽、断线仍拒绝；该预检只读，无登记命令。

活动29份源码、原相机unit/PID和原模型/音频配置已核对。电脑保持Paraformer→原27B IQ4_XS/2048→OmniVoice16及5项延迟选项；原YOLOX-Nano/ByteTrack/DPU/FPGA保持，LLM权重仍D盘。

## 下一轮照片

按原称呼说“帮我登记身份，我叫……”，复述后说“确认更新登记”；确认后才开始采样。脸部照片保存在`{v['enrollment_photos']['directory']}/<session>/`，实际112×112人脸裁剪；成功、失败或取消均留档。最终模板和最终5张独立验证图有清单标记。

`../2026-10-19_enrollment_photo_archive/export_latest.py`将实际照片校验复制到`{ROOT/'身份登记照片'}/<session>/`并生成离线总览。此前未保存的照片无法补回，公开模型预检图片不可当用户登记照片。当前尚未取得这次修复后真人照片，不把入口修复称为真人采样/重返准确度通过。

证据：`entry_diagnosis_before.json`、`tests_pc.log`、`tests_board.log`、`preflight.json`、`deployment.json`、`source_verification.json`、`verification_summary.json`、`verified_source.zip`。源码包不含权重、身份库、现场照片、特征或姓名。回退`rollback.py`仅恢复上一UI，保留存图相机和当前身份库；备份`{d['backup']}`。
'''
(HERE/'README.md').write_text(text,encoding='utf-8')
marker='identity-capture-snapshot-20261019'
def note(path,body):
 raw=path.read_text(encoding='utf-8')
 raw=re.sub(r'<!-- '+marker+r' -->.*?<!-- /'+marker+r' -->\s*','',raw,flags=re.S)
 path.write_text('<!-- '+marker+' -->\n'+body+'\n<!-- /'+marker+' -->\n\n'+raw,encoding='utf-8')
note(ROOT/'AGENTS.md',f'- 2026-10-19用户存图版登记仍无法开始：实际generation18/face_unavailable、capture_snapshot_valid=false，0照片。已确认UI缓存READY/新鲜却含取消字幕展示字段interaction_suppressed，严格相机协议拒绝。新增UiServiceClient.identity_snapshot读取原始新鲜缓存并严格校验，GUI录音改绑定该方法，显示遮罩/取消授权/同人来源和原阈值保持。Windows182+24子用例、Linux222及当前相机只读预检通过；UI已加载`{c["runtime"]}`，存图相机仍6f1候选/PID动态，库1/1/rev14哈希保持，电脑8792未重启。后续明确登记后保存实际112×112脸，失败也留；新真人采样和图片展示待完成，不当人脸准确度验收。最新证据`deliverables/2026-10-19_identity_capture_snapshot/README.md`及verification_summary.json；照片功能已启用，旧连接阻塞已恢复。LLM数据D盘。')
note(ROOT/'README.md','> **2026-10-19 登记入口修复已加载：** 已确认并修复取消字幕的显示标记导致录音起点人脸状态校验失败；原确认和身份门槛保持。Windows182/板端222项及真实快照预检通过，照片保存服务正常；新真人采样照片待取得。[本轮原因和证据](deliverables/2026-10-19_identity_capture_snapshot/README.md)。')
prior=HERE.parent/'2026-10-19_enrollment_photo_archive'
note(prior/'README.md','> 后续已确认“登记无法开始”的UI取消字幕快照错误并加载修复，照片保存相机保持正常；见[登记入口修复](../2026-10-19_identity_capture_snapshot/README.md)。此前无法开始的一轮未产生照片。')
analysis=ROOT.parent/'语言模型分析';report='语音登记入口快照修复_20261019.md'
(analysis/report).write_text(text,encoding='utf-8')
note(analysis/'README.md',f'[语音登记入口快照修复]({report})：已加载；取消字幕不再使录音起点人脸状态失效，照片服务保持，新照片待采集。')
print(json.dumps({'status':summary['status'],'ui_runtime':c['runtime'],'database':v['database'],
 'pc_tests':182,'linux_tests':222,'photo_service_enabled':True},ensure_ascii=False))
