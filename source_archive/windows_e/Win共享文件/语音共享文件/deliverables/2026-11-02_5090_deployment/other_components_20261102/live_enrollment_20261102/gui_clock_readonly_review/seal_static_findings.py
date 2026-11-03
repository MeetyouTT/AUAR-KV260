"""Seal source-only findings; no source execution, network or private paths opened."""
import ast
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
metadata = json.loads((HERE / 'SOURCE_METADATA.json').read_text(encoding='utf-8'))
source_root = HERE / 'current_public_source'
hashes = {p: v['sha256'] for p, v in metadata['sources'].items()}
expected = {
    'board/runtime/board_dialogue_client.py': '600e044dedfc90c70e319e0e91999b8b4b7f648e0a5ca98e2a1bc0ab09a076b2',
    'common/board_timeline_clock.py': '93b65ec3d9ca393b32499845297c78a2f1f71bc19e069b2ce3dc6f69e795af02',
    'board/runtime/board_business.py': 'b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2',
    'tools/production_board_business_gui.py': 'b01f6edb9efe88cf95da60900e5ccc32eec93a24ef3f515ab08f51ae2ee6ada8'}
for name, checksum in expected.items():
    assert hashlib.sha256((source_root / name).read_bytes()).hexdigest() == checksum
refs = {}
for name in expected:
    tree = ast.parse((source_root / name).read_text(encoding='utf-8'))
    for klass in tree.body:
        if isinstance(klass, ast.ClassDef):
            for func in klass.body:
                if isinstance(func, ast.FunctionDef) and func.name in (
                        'start', 'connect', 'retain_connected_socket', '_watch', 'sample_health_date',
                        'initialize_clock', 'observe_http_date', '__init__'):
                    refs[name + ':' + klass.name + '.' + func.name] = func.lineno

report = {
    'schema': 'aura-gui-date-sample-static-readonly-review-1',
    'sealed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'NO_FIXED_WAIT_OR_CLOCK_POLICY_POLLUTION_FOUND_PHASE_MEASUREMENTS_PENDING',
    'fresh_public_source_metadata': metadata,
    'source_references': refs,
    'fixed_source_facts': {
        'gui_initialize_clock_total_deadline_seconds': 3.0,
        'timeline_default_max_rtt_seconds': 1.0,
        'runtime_client_timeline_share_original_monotonic_callable': True,
        'startup_passes_no_rtt_override': True,
        'turn_timeout_ms_is_not_date_sample_rtt_policy': True,
        'watcher_thread_start_is_before_sent_timestamp': True,
        'watcher_event_wait_seconds': 0.02,
        'connect_calls_original_http_connection_connect_once_if_sock_absent': True,
        'connection_retention_has_no_fixed_sleep_or_join': True,
        'timed_interval': 'sent before connect through getresponse headers complete',
        'included': ['socket_connection_establishment', 'request_send', 'headers_wait', 'process_scheduling_within_interval'],
        'excluded': ['watcher_start', 'body_read_and_parse', 'clock_observe', 'anchor_save', 'close_and_join'],
        'close_join_timeout_seconds_outside_rtt': 0.1,
        'fixed_one_second_wait_found': False,
        'application_proxy_or_redirect_in_this_client': False,
        'client_uses_pinned_ipv4_endpoint': True,
        'actual_startup_options_not_extracted_from_manifest': True},
    'interpretation': [
        'sample_rtt_exceeded requires received_monotonic-sent_monotonic > default1s',
        'Independent raw HTTP probes at other instants do not isolate time inside the failing GUI process',
        'Code alone cannot determine which timed subphase consumed the second'],
    'unproved_hypotheses_not_findings': [
        'Cold socket/getaddrinfo or lazy codec import in the GUI process',
        'Local CPU scheduling/GIL contention while model/GUI initialization is active',
        'Transient server/header delay at the exact GUI request instant'],
    'minimal_next_step': 'Root RAM-only original sample probe should time connect/retain/request/getresponse and preserve full original sent-received RTT; reviewer sends no duplicate probes',
    'recovery_policy': [
        'Keep 1s RTT, original3s deadline, source verifier and same-boot monotonic policy unchanged',
        'Do not move sent after connect or subtract local delay from the accepted clock sample',
        'Do not replace/remove anchor or fallback to board wall clock',
        'If a cold-import/setup cost is proved, prepare that setup before starting the untouched original sampled transaction, then root can perform one normal GUI restart',
        'If transient CPU/server delay is proved, resolve that bounded contention before one normal GUI start rather than enlarging the time policy'],
    'reviewer_board_actions': 'Only four public-source file reads and startup manifest hash, via strict known-host SSH helper',
    'reviewer_health_model_service_private_database_axis_or_production_mutations': False,
    'unique_runtime_root_cause_proved': False}
(HERE / 'READONLY_FINDINGS.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
text = '''只读源码审阅：尚未发现固定等待或时钟策略污染，精确运行时根因需分段测量。

当前板卡公开源码 SHA 已核：client600e、clock93b6、runtimeb082、GUI构造b01f。startup680fd在读取期间稳定。生产调用 initialize_clock(timeout=3.)，runtime/client/timeline共享原 time.monotonic；StableTimelineClock沿用默认 max_rtt_seconds=1.，未传覆盖值。turn timeout_ms不参与该RTT策略。

_ConnectionControl.start 先check再启动后台watcher，位于sample的sent时间戳之前。watcher每20ms等Event，不把连接锁持在等待期间。connect只在sock为空时调原HTTPConnection.connect，然后保留真实socket并check；没有固定1s sleep、join、重试或代理。连接timeout设为原启动deadline剩余值，不是新增等待。

sample_rtt_exceeded只根据 received-sent>1s触发。sent在连接前，received在HTTP响应头完成后，所以此区间包括连接建立、请求发送、响应头等待及期间本进程被调度/阻塞的时间；不包括body读取/解析、observe_http_date、锚点保存、finally关闭或最多0.1s join。另一次独立http.client探针5–20ms，不能单凭此数值排除GUI请求当时的连接/调度/服务端延迟。

最小下一步由root执行RAM-only原sample分段测量：connect、retain、request、getresponse，保留完整原sent→received时间。冷socket/getaddrinfo/首次codec导入、本地CPU/GIL争用、当次服务端头等待均只是待验证方向，当前没有足够证据选其一。审阅者不重复health探针，避免改变cold样本。

恢复不改1s门槛、3s原期限、原source verifier、单调时钟/同boot策略；不把sent挪到连接后，不从样本RTT扣本地耗时，不替换/删除锚点或回退板卡墙钟。若测量证明冷初始化耗时，可在原采样事务开始前完成相关准备，再原样采样；若证明瞬态争用，先解决已证实的争用，再由root正常启动一次GUI。任何具体代码/启动顺序变更都需待分段证据。

本轮只通过已核严格known-host SSH读取4份公开源码和startup manifest hash；无health/model探测、服务/模型/私库/轴动作或生产写入。未导出真实业务内容。
'''
(HERE / 'READONLY_FINDINGS.txt').write_text(text, encoding='utf-8')
print(json.dumps({n: hashlib.sha256((HERE/n).read_bytes()).hexdigest()
                  for n in ('READONLY_FINDINGS.json', 'READONLY_FINDINGS.txt', 'SOURCE_METADATA.json')}))
