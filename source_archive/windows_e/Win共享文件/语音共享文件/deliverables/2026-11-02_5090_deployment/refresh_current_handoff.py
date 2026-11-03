"""Update root-owned current pointers while preserving accepted historical receipts."""
import datetime
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SHARED = PROJECT.parent
now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime('%Y%m%dT%H%M%S')
lan = json.loads((HERE/'parallel_lan/LAN_READY.json').read_text(encoding='utf-8'))
binding = json.loads((HERE/'gui_selected_binding_applied.json').read_text(encoding='utf-8'))['board_result']
gui_path = HERE/'gui_start_and_verify.json'
gui = json.loads(gui_path.read_text(encoding='utf-8')) if gui_path.exists() else None
network_relative = 'parallel_lan/transactions/'+lan['transaction_id']+'/board_public_probe.json'
network_path = HERE/network_relative
network = json.loads(network_path.read_text(encoding='utf-8')) if network_path.exists() else None
if network:
    assert network['status']=='PUBLIC_BOARD_LLM_AND_TTS_RAM_ONLY_PASS'
    assert network['host_session_id']==lan['session_id']
firewall_path = HERE/'parallel_lan/firewall_result.json'
firewall = json.loads(firewall_path.read_text(encoding='utf-8')) if firewall_path.exists() else None
phase = 'GUI_START_REQUIRES_DIAGNOSIS' if gui else 'GUI_BINDING_REPAIRED_NETWORK_VALIDATION_PENDING'
if gui and gui.get('board_result',{}).get('gui_unit_final',{}).get('active_state')=='activating':
    phase = 'GUI_INITIALIZING'
if network and not gui:
    phase = 'LAN_PUBLIC_PROBE_PASS_GUI_START_PENDING'
if gui and gui.get('software_ready') is True and network:
    phase = 'MODELS_LAN_GUI_SOFTWARE_READY_PHYSICAL_ACCEPTANCE_PENDING'
    if gui.get('physical_page_visibility')=='USER_CONFIRMED_ROLE_MAIN_PAGE':
        phase = 'MODELS_LAN_GUI_READY_AXIS_AND_SPEECH_ACCEPTANCE_PENDING'
display_path=HERE/'display_state_after_gui.json'
display=json.loads(display_path.read_text(encoding='utf-8'))['board_result'] if display_path.exists() else None
current = {
    'schema':'aura-5090-deployment-current-1', 'updated_utc':now.isoformat(), 'phase':phase,
    'local_models_accepted':True, 'accepted_local_receipts_preserved':[
        'STATUS.json','READY_LOCAL.json','source_manifest_5090.json'],
    'historical_local_receipt_scope':'accepted loopback instance; live endpoint and owner are recorded here and in LAN receipts',
    'model_endpoint':lan['endpoint'], 'model_session':lan['session_id'],
    'model_configuration_sha256':lan['configuration_sha256'],
    'model_owner':lan['main_owner'], 'model_tts_owner':lan['tts_owner'],
    'model_daemon':lan['fixed_daemon'], 'lan_transaction':lan['transaction_id'],
    'firewall_status':firewall.get('status') if firewall else 'PENDING',
    'board_link_receipt':network_relative if network else None,
    'board_boot_id':binding['boot_id'], 'camera_owner':binding['camera_owner'],
    'startup_sha256':binding['startup_after_sha256'], 'gui_configuration_sha256':binding['ui_after_sha256'],
    'selected_binding_sha256':binding['new_selected_sha256'], 'selected_binding_source_count':24,
    'gui_receipt':'gui_start_and_verify.json' if gui else None,
    'gui_software_ready':bool(gui and gui.get('software_ready')),
    'gui_owners':gui['board_result']['owners'] if gui and gui.get('software_ready') else None,
    'display_power':display['monitor_power'] if display else None,
    'screensaver_timeout_seconds':display['screensaver_timeout_seconds'] if display else None,
    'saved_listening_enabled':False,
    'physical_page_visibility':gui.get('physical_page_visibility','AWAITING_USER_OBSERVATION') if gui else 'AWAITING_USER_OBSERVATION',
    'platform_firmware':'kv260-benchmark-b4096.bit.bin',
    'wide_platform_execution_ready':False, 'current_boot_motion_authorized':False,
    'persistent_ntp_synchronized':False, 'private_data_exported':False,
    'platform_review':'parallel_platform_review/INDEPENDENT_REVIEW.md',
    'remaining':['real speech and listening acceptance',
        'wide-platform transaction backend and current-boot axis acceptance', 'persistent NTP and cold-boot recovery']}
if current['physical_page_visibility']!='USER_CONFIRMED_ROLE_MAIN_PAGE':
    current['remaining'].insert(0,'physical panel visibility')
(HERE/'DEPLOYMENT_CURRENT.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

gui_text = ('板端 GUI 已启动，软件状态见 gui_start_and_verify.json'
    if gui and gui.get('software_ready') is True else
    'GUI 实际选中的旧启动周期绑定已修复，服务启动及网络联调继续进行')
block = ('<!-- 5090-local-deployment-20261102 -->\n'
    '5090 本机部署接续更新（洛杉矶 2026-11-01）：原 27B IQ4_XS 完整 SHA 已通过，权重及 Ollama 数据仍在项目外 D:/AIModels；原 OmniVoice16、104 项依赖、真实 CUDA、模型共存和本机公开 LLM/TTS HTTP 已验收。'
    '当前模型服务为 192.168.50.1:8797，唯一允许推理对端为板卡 192.168.50.2；本机 GET 健康可读，推理 POST 拒绝。'
    f'当前状态统一读语音共享文件/deliverables/2026-11-02_5090_deployment/DEPLOYMENT_CURRENT.json；冻结 STATUS/READY_LOCAL/source_manifest 记录的是先前已验收的回环实例。{gui_text}。'
    '当前 boot 903cfade-b93c-48fa-804e-379be1967313，相机 1333/birth2359；新选用绑定保留原23项校验并追加当前run-config为24项，380组件已核验；'
    f'当前 startup SHA {binding["startup_after_sha256"]}。'
    '保存聆听 false，benchmark 固件，wide 平台实际执行后端尚未就绪，本 boot 的实体动作/方向/跟随尚未验收。时钟已向前校正，持久NTP仍待恢复。'
    'Ubuntu SSH与应用远程项目已接入。勿重复安装/下载、启动旧8792业务、重用旧PID/READY/检查点或重放旧运动请求。\n'
    '<!-- /5090-local-deployment-20261102 -->')
before = HERE/'before'/('current-docs-'+stamp)
before.mkdir(parents=True,exist_ok=False)
for index,path in enumerate((SHARED/'AGENTS.md',SHARED/'README.md',PROJECT/'AGENTS.md')):
    data = path.read_bytes()
    begin = b'<!-- 5090-local-deployment-20261102 -->'
    end = b'<!-- /5090-local-deployment-20261102 -->'
    assert data.count(begin) == data.count(end) == 1
    start,finish = data.index(begin),data.index(end)+len(end)
    shutil.copy2(path,before/(str(index)+'-'+path.name))
    path.write_bytes(data[:start]+block.encode('utf-8')+data[finish:])
pointer = SHARED/'本机部署状态_5090.txt'
shutil.copy2(pointer,before/pointer.name)
pointer.write_text('当前部署状态：'+str(HERE/'DEPLOYMENT_CURRENT.json')+'\n'
    '部署交接：'+str(HERE/'HANDOFF.txt')+'\n'
    '原模型本机验收已完成；当前模型端点192.168.50.1:8797。'+gui_text+'。\n'
    'STATUS.json、READY_LOCAL.json及source_manifest_5090.json保留历史回环验收；板卡实体动作与持久平台恢复尚未验收。\n',encoding='utf-8')
print(json.dumps({'updated':str(HERE/'DEPLOYMENT_CURRENT.json'),'phase':phase,'documents_backed_up':str(before)}))
