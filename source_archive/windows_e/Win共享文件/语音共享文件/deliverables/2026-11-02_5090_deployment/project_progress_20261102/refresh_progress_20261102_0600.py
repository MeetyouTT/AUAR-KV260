"""Reconcile progress from saved peer receipts; never access the board or its stores."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.request

BASE = Path(r"E:\Win共享文件\语音共享文件\deliverables\2026-11-02_5090_deployment")
OUT = BASE / "project_progress_20261102"
ENROLL = BASE / "other_components_20261102/live_enrollment_20261102"
EXPECTED = {
    "PROJECT_PROGRESS.json": "686948b28a6d7d05b88cc63c671906cc54ae81c49a0fc88641d58a3815e278d0",
    "PROJECT_PROGRESS.txt": "67984102d0de891fe53d812f33d0d9fc09d55ef2297259820b45cd91e68ad730",
}
source_hashes = {}


def read(path):
    raw = path.read_bytes()
    source_hashes[str(path.relative_to(BASE))] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw.decode("utf-8-sig"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


for name, expected in EXPECTED.items():
    assert hashlib.sha256((OUT / name).read_bytes()).hexdigest() == expected, name

now = dt.datetime.now(dt.timezone.utc)
stamp = now.strftime("%Y%m%dT%H%M%SZ")
backup = OUT / ("before_progress_refresh_" + stamp)
backup.mkdir(exist_ok=False)
for name in EXPECTED:
    (backup / name).write_bytes((OUT / name).read_bytes())

progress = read(OUT / "PROJECT_PROGRESS.json")
axis = read(BASE / "AXIS_CURRENT_HANDOFF.json")
cpu = read(BASE / "cpu_optimization_20261102/CPU_OPT_STATUS.json")
identity = read(ENROLL / "CURRENT_ENROLLMENT_STATUS.json")
ready_path = ENROLL / "voice_entry_trace_20261102/PRE_DEPLOYMENT_READINESS.json"
ready_receipt = read(ready_path)
ready = ready_receipt["board_result"]
inventory_path = ENROLL / "split_commands_20261102/actual_release/VOICE_BEFORE_INVENTORY.json"
inventory_receipt = read(inventory_path)
inventory = inventory_receipt["board_result"]
apply_path = ENROLL / "split_commands_20261102/actual_release/APPLY_RESULT.json"
applied = read(apply_path)["board_result"]

models = {"observed_utc": now.isoformat(), "endpoint": "http://192.168.50.1:8797", "model_inference_requested": False}
try:
    with urllib.request.urlopen(models["endpoint"] + "/health", timeout=10) as response:
        health = json.load(response)
    backend = health["backend"]
    gpu = backend["gpu_coordination"]
    voice = backend["voice"]
    models.update(ok=health["ok"], role=health["role"], model=backend["model"],
                  tts=backend["tts"], num_step=backend["num_step"], tts_ready=backend["tts_ready"],
                  voice_alive=voice["alive"], voice_error_present=bool(voice.get("error")),
                  llm_residency=gpu["llm_residency"], active=health["active"], pending=health["pending"])
except Exception as error:
    models.update(ok=False, error_type=type(error).__name__)
models_name = "LIVE_MODELS_READONLY_" + stamp + ".json"
write(OUT / models_name, models)

modules = [
    {"module": "本机模型与LAN", "status": "原模型部署及板卡LAN实测通过；本轮主机健康复查正常" if models.get("ok") else "部署已验收；本轮主机健康复查失败，见回执",
     "facts": "原27B IQ4_XS / OmniVoice16保持；本轮仅GET健康，不发推理，不重启。当前板卡推理端到端未在本窗口重跑。",
     "evidence": [models_name, "../parallel_lan/LAN_PUBLIC_BOARD_READY.json"]},
    {"module": "板端业务/角色UI", "status": "当前启动主页面已恢复，软件核验通过",
     "facts": "身份窗口13:55 UTC回执：GUI/相机运行，角色可见，380组件一致，业务时钟锚定、单写者持有、故障0；当时PAUSED/麦克风关闭。后续身份维护仍在进行，不是当前此刻操作授权。",
     "evidence": [str(ready_path.relative_to(BASE))]},
    {"module": "视觉感知", "status": "相机/DPU工作；人脸登记及KNOWN已有现场确认",
     "facts": "本次boot相机1332；正式现用模型库1身份/1模板。识别成功不等于声纹完成或人物关联完成。",
     "evidence": [str(inventory_path.relative_to(BASE)), "../other_components_20261102/live_enrollment_20261102/CURRENT_ENROLLMENT_STATUS.json"]},
    {"module": "基础语音对话", "status": "已有两轮真人完整播放实测；新版联合轮次待重验",
     "facts": "先前boot两轮有匹配完整播放回执。录音结束至软件SPEAKING 5.04/5.29秒；不作为本次新版本或声学首声成绩。",
     "evidence": ["../dialogue_latency_20261101/TWO_TURN_LATENCY.json"]},
    {"module": "转轴跟随", "status": "原跟随曾现场通过；本次重启后平台不匹配，专用窗口冻结",
     "facts": "上次boot已发布左停点0.40/右0.45、恢复稳定150ms且至少3张独立有效图像的原算法扩展，42项双端测试通过；右转顿挫实体改善待验。当前boot最后核验为benchmark，原wide未恢复，无当前STOP/参考/方向验收；不重用旧输出关闭回执。",
     "evidence": ["../AXIS_CURRENT_HANDOFF.json", "../maintenance_original_axis_20261101/new_boot_a6d4_readonly_20261102/NEW_BOOT_TECHNICAL_HANDOFF.json"]},
    {"module": "身份与语言协同", "status": "人脸已验收；独立声纹登记现场闭环未完成",
     "facts": "独立人脸/声纹口令及有界原时钟重试已发布，保留原1秒RTT/共同3秒期限。最近正式库存声纹0/人物关联0；身份窗口正在定位口令识别或后续分流，尚无声纹保存成功凭证。按最新要求先独立登记，跨模态关联后置。",
     "evidence": [str(apply_path.relative_to(BASE)), str(inventory_path.relative_to(BASE)), "../other_components_20261102/live_enrollment_20261102/voice_entry_trace_20261102/HANDOFF.txt"]},
    {"module": "记忆", "status": "板端时间轴及摘要已部署；个人权限/长时召回联合待验",
     "facts": "已有摘要清理、数据库快检及真人多轮历史证据。此次未打开数据库，未更新计数；跨身份个人记忆授权与本次新版长时召回不能算已验收。",
     "evidence": ["../memory_status_20261102/MEMORY_CURRENT_082236.json", "../video_demo_readiness_20261101/MEMORY_CURRENT_READONLY.json"]},
    {"module": "板端CPU优化", "status": "GTK代码已发布；相机候选未发布；缺同条件后测",
     "facts": "本次benchmark的40秒before：整板四核CPU 82.59%，相机/DPU进程36.89%、GTK30.32%，采集23.66fps/处理9.90fps。GTK独立投影探针不是整板收益，当前无有效after，不报告CPU降幅。",
     "evidence": ["../cpu_optimization_20261102/CPU_OPT_STATUS.json", "../cpu_optimization_20261102/SUMMARY_RESOURCE_a6d4_benchmark_before.json"]},
    {"module": "开机恢复与全流程演示", "status": "完整冷启动恢复及三分钟联合演示尚未验收",
     "facts": "已实际发生重启后benchmark与旧wide接入不匹配；业务时钟可锚定，板端OS墙钟不可信，持久NTP未验收。需要同boot恢复wide、更新来源绑定、轴验收，再跑完整语音/视觉/角色/身份与记忆联合流程。",
     "evidence": ["../AXIS_CURRENT_HANDOFF.json", str(ready_path.relative_to(BASE))]},
]

# Every evidence entry is relative to the progress folder.
for module in modules:
    for index, evidence in enumerate(module["evidence"]):
        if not evidence.startswith("../") and evidence != models_name:
            module["evidence"][index] = "../" + evidence
    for evidence in module["evidence"]:
        assert (OUT / evidence).is_file(), evidence

progress.update(
    updated_utc=now.isoformat(), client_date="2026-11-02", timezone="America/Los_Angeles",
    overall="基础模块已跑通，人脸已现场确认；独立声纹、当前boot wide/轴恢复、优化后测及联合演示仍未闭环",
    live_board_observed_utc=ready_receipt["host_utc"], live_models_observed_utc=models["observed_utc"],
    live_board_observation_source="Identity chat persisted readiness receipt; original chat made no board query",
    current_boot_id=ready["boot_id"], startup_sha256_at_latest_saved_board_receipt=ready["startup_sha256"],
    latest_saved_board_receipt=str(ready_path.relative_to(BASE)),
    full_five_component_human_acceptance_complete=False, full_three_minute_integrated_demo_ready=False,
    modules=modules,
    next_sequence=[
        "身份窗口完成独立声纹的明确采样提示、三段录入及确认保存闭环；人物关联按用户要求后置",
        "原wide恢复由设备权持有人串行安排，保留原相机Native完整历史和新身份/GTK改动，刷新来源绑定",
        "转轴专用窗口完成本boot STOP/参考/方向，并现场复验左停点与右转顿挫",
        "在相同平台/页面/版本条件补CPU after；相机候选仅在正常生命周期与新鲜final验证后发布",
        "执行本boot两轮完整播放及视觉/角色/身份/记忆/原跟随联合演示，记录CPU、吞吐和分段延迟",
        "验证断电后完整恢复及持续运行，不沿用上次boot的动作或STOP凭证",
    ],
    audit_actions={"board_queries_sent": 0, "board_commands_sent": False, "database_opened": False,
                   "models_restarted": False, "model_inference_requested": False, "private_content_exported": False,
                   "local_progress_documents_updated": True},
    previous_progress_backup=str(backup.relative_to(BASE)),
    evidence_file_sha256=source_hashes,
    field_scope="Point-in-time reconciliation from saved peer receipts plus local host health; not a device handback or authority to act",
)
progress["axis_thread"]["status"] = "idle_frozen_waiting_maintenance_handback"
progress["axis_latest_publication_utc"] = None
progress["axis_publication_scope"] = "Stable150 release retained, publication was previous boot; current boot platform incompatible"
write(OUT / "PROJECT_PROGRESS.json", progress)

text = """项目进程梳理（洛杉矶2026-11-02，约06:00更新）

当前阶段：基础模块已跑通；人脸已现场确认；独立声纹、当前启动的wide/轴恢复、优化后测和完整联合演示仍未闭环。

本机：原27B IQ4_XS与OmniVoice16部署及LAN板卡推理已验收，本轮GET健康复查正常、LLM驻留GPU、TTS就绪；未重启或发推理。

板端：本次boot a6d4a069，身份窗口05:55的保存回执确认角色主页面/GUI/相机运行、380组件一致、故障0、业务时钟锚定；当时暂停聆听、麦克风关闭。身份窗口仍在维护，后续状态以该窗口更新为准。本窗口没有查询或操作板卡。

视觉/人脸：正式现用模型库1身份/1模板，登记COMMITTED并有KNOWN及本人现场确认。人脸验收不等于声纹登记或人物关联验收。

声纹：独立人脸/声纹登记入口及有界原时钟重试已发布；最近正式库存仍为0声纹/0人物关联。现场尚未取得“进入采样→三段录音→确认保存”的完整凭证，身份窗口正在定位口令识别或后续分流；先独立登记，人物关联后置。

转轴：原跟随方向/动作在上一启动周期已获现场确认；左停点0.40/右0.45和中断后稳定150ms/3张有效独立图像再恢复的原算法扩展已发布，双端各42项测试通过，但右转顿挫实体改善未验收。本次板卡重启后仍是benchmark平台，原wide未恢复；轴窗口冻结，无本boot STOP/参考/方向/跟随验收，不沿用旧STOP输出回执。

性能：GTK两源优化已提交且随身份版本恢复界面。相机JPEG优化候选完成离线复核但尚未发布。当前boot benchmark的40秒before为四核整板CPU 82.59%、相机/DPU进程36.89%、GTK30.32%，采集23.66fps/处理9.90fps；没有同条件after，不能宣布整板降幅。

语音/记忆：已有两轮真人完整播放证据；当时录音结束至软件SPEAKING约5.04/5.29秒，完整LLM RPC约1.8–1.9秒、ASR1.1–1.4秒、TTS0.77–0.84秒。不是新版性能或声学首声。板端时间轴/摘要与多轮历史已有证据，个人权限/长时召回与本次版本的联合验收仍待完成，本轮未打开数据库或更新计数。

接续顺序：独立声纹完成并交还维护权→保护原相机完整历史并恢复原wide/刷新来源绑定→轴窗口本boot验证并复验左右停点/顿挫→补同条件CPU后测及相机优化→两轮语音与视觉/玩偶/身份/记忆/原轴跟随联合演示→冷启动完整恢复验收。

职责：身份窗口当前负责GUI/聆听及登记；转轴专用窗口唯一轴写权但冻结；CPU窗口等待短维护/只读后测窗口；原窗口只读汇总及维护全局进度。本轮没有重启服务、访问私库、导出私人内容或发运动。

范围：早期903cfade启动的PID、wide恢复、STOP/参考/方向和模型/对话成绩保留为历史；当前细节以各专用窗口最新回执为准。DEPLOYMENT_CURRENT旧平铺运行字段尚未整批迁换，不能用来发设备命令。本次更新的PROJECT_PROGRESS.json记录新boot、逐模块状态与证据范围。
"""
(OUT / "PROJECT_PROGRESS.txt").write_text(text, encoding="utf-8")
assert json.loads((OUT / "PROJECT_PROGRESS.json").read_text(encoding="utf-8"))["current_boot_id"] == ready["boot_id"]
print(json.dumps({"status": "PROGRESS_RECONCILED", "updated_utc": now.isoformat(),
                  "current_boot": ready["boot_id"], "board_actions": 0, "models_health_ok": models.get("ok"),
                  "modules": len(modules), "backup": str(backup), "progress": str(OUT / "PROJECT_PROGRESS.txt")}, ensure_ascii=False))
