"""Seal independent local review receipts; no production imports or network."""
import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
FIX = HERE.parent
OUT = HERE.parents[3]
BASE = OUT / 'identity_dialogue_collaboration/baseline'
expected = 'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb'
candidate = FIX / 'candidate_v2/board/identity/voice_enrollment.py'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(candidate) == sha(HERE / 'reviewed_candidate_v2.py') == expected
focused = json.loads((HERE / 'V2_INDEPENDENT_RESULTS.json').read_text(encoding='utf-8'))
assert focused['all_focused_cases_pass'] and focused['focused_case_count'] == 13

def xml_receipt(name):
    path = FIX / name
    root = ET.fromstring(path.read_bytes())
    suites = list(root.iter('testsuite'))
    return {'file': name, 'sha256': sha(path),
            **{key: sum(int(s.attrib.get(key, 0)) for s in suites)
               for key in ('tests', 'failures', 'errors', 'skipped')},
            'failure_cases': sorted(t.attrib.get('classname', '') + '.' + t.attrib.get('name', '')
                                    for t in root.iter('testcase') if t.find('failure') is not None)}

race = xml_receipt('RACE_V2_CANDIDATE_FINAL.xml')
original = [xml_receipt('ORIGINAL_FLOW_' + label + '_V2.xml') for label in ('BASELINE', 'CANDIDATE')]
assert (race['tests'], race['failures'], race['errors']) == (32, 0, 0)
assert original[0]['failure_cases'] == original[1]['failure_cases']
assert all((r['tests'], r['failures'], r['errors']) == (37, 2, 0) for r in original)
test_checks = []
for relative in ('tests/framework/test_simple_enrollment.py', 'tests/framework/test_sampling_voice.py'):
    paths = [BASE / relative, FIX / 'baseline_runtime' / relative, FIX / 'candidate_runtime' / relative]
    hashes = [sha(p) for p in paths]
    assert len(set(hashes)) == 1
    test_checks.append({'relative_path': relative, 'sha256': hashes[0], 'original_assertions_byte_identical': True})

verdict = {
    'schema': 'aura-face-start-sync-independent-verdict-2',
    'sealed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'verdict': 'PASS_LOCAL_V2_REVIEW_NO_CODE_BLOCKER',
    'before_sha256': '83796dd78c57555ea66eeb2b745a89f8b3670945a4406176cb3486111d9466b8',
    'approved_candidate_sha256': expected,
    'rejected_v1_sha256': '4a93a7d86b9cd6f52d0dcc9b9844767c684a276592b1d63fa0c43a099170e65d',
    'scope': 'Only existing VoiceEnrollment simple-start cached-publication synchronization and is_current forwarding',
    'independent_focused_cases': 13,
    'independent_focused_cases_all_pass': True,
    'v1_counterexample_preserved': 'V1_PRECOMMAND_SESSION_COUNTEREXAMPLE.json',
    'v1_old_B_failed_ready_collect_counterexamples_fixed_in_v2': True,
    'start_command_send_limit': 1,
    'original_full_eight_field_ack_validation': True,
    'ack_has_sampling_session_id': False,
    'claim_requires_new_sequence_post_ack_source_stamp_original_deadline_complete_owner_bound_target_and_collect_front': True,
    'source_timestamp_replaced_with_read_timestamp': False,
    'unknown_unproved_sampling_session_cancelled': False,
    'original_publication_deadline_seconds_max': 2.5,
    'poll_iterations_max': 50,
    'original_authorization_expiry_shortens_wait': True,
    'original_90_second_guidance_window_not_extended_by_cache_wait': True,
    'changed_methods': focused['changed_methods'],
    'handle_change_only_forwards_is_current': True,
    'all_other_voice_methods_ast_identical': True,
    'threshold_quality_ttl_models_permissions_save_and_ack_semantics_changed': False,
    'author_race_xml': race,
    'author_original_flow_xmls': original,
    'original_tests_byte_checks': test_checks,
    'original_flow_boundary': '35 pass / same 2 pre-existing character-alias fixture failures in both; 1 HTTP case deselected',
    'integration_boundary': 'Broader Windows camera integration did not collect because fcntl is unavailable; not counted as passed',
    'live_boundary': 'No live retry by reviewer; actual face auto-save, three voice samples and final ACTIVE link remain to verify after root applies the exact candidate',
    'causality_boundary': 'Reproducible cache race and ready-confirmation timeout established; unique causal link for every live snapshot not proved because prior summaries omitted sampling session identity',
    'devices_network_models_real_databases_accessed_during_this_review': False,
    'production_services_sources_or_candidate_changed_by_reviewer': False,
    'real_names_person_ids_embeddings_photos_transcripts_audio_exported': False,
    'review_artifacts': {name: sha(HERE / name) for name in ('review_v2.py', 'reviewed_candidate_v2.py', 'V2_INDEPENDENT_RESULTS.json')},
    'author_test_adapter_sha256': sha(FIX / 'real_contract_fixture_adapter.py')
}
(HERE / 'REVIEW_VERDICT.json').write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding='utf-8')
report = '''V2 独立本地审阅：通过，无代码阻断点。

候选 voice_enrollment.py SHA256:
a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb
基线 SHA256:
83796dd78c57555ea66eeb2b745a89f8b3670945a4406176cb3486111d9466b8

独立复验 13 个场景全部通过。先用封存 V1 字节重现：初始旧缓存 A，本次命令 C 已 accepted，随后先出现命令前生成的 B failed/ready/collect；V1 对 B 误取消或误认领。V2 对三种 B 均不认领、不取消，等待真实来源戳晚于 ACK 的 C，且只发一次 start。另核 issued<source_stamp<ACK、source_stamp==ACK、旧 A 重新发布、错误 target、始终不发布、取消发生在 start 前/可信认领前/认领后、原授权先到期，均符合边界。只有可信认领后的取消会清理 C。

静态核对：仅 _start_simple 和 handle 发生 AST 差异；handle 仅透传原 is_current。_send、_cancel_sample、guide、_save_ready、目标选择及其他原方法 AST 相同。start ACK 使用原八字段协议，六项归属逐值校验；ACK 没有 sampling session_id。认领还要求新序号、原 observed 时间严格晚于 ACK 且早于原命令期限、完整来源/上下文/库版本/目标绑定、不同于旧 SID、collect/front。时间戳没有替换为读取时刻。至多 50 轮和 2.5 秒，原授权可提前终止；90 秒引导窗口从发命令前计，未顺延。

作者专项 XML 核实 32/32 通过。原流程两版各 37 项：35 通过，同样 2 项旧角色别名 fixture 失败，0 error；另 1 HTTP 项 deselected。两份原测试文件在基线、baseline_runtime、candidate_runtime 字节相同，适配器只补真实 ACK 和明确逻辑源帧推进。Windows 缺 fcntl 的更广相机集成收集失败保留为限制，没有计作通过。

此结论限本地候选。审阅没有 SSH、设备/模型/真实库调用，没有服务、GUI、转轴、生产或候选修改，没有导出真实姓名、ID、模板、照片、语音、转写。现场是否完整保存人脸并完成三段声纹及最终 ACTIVE 关联，仍须 root 应用精确候选后走原流程验收。原缓存竞态可重现，现网 15/15 后实际失败码为采样或确认超时；先前摘要缺会话标识，不能将每条现场观测无条件串为同一会话。
'''
(HERE / 'REVIEW.txt').write_text(report, encoding='utf-8')
print(json.dumps({name: sha(HERE / name) for name in ('REVIEW_VERDICT.json', 'REVIEW.txt', 'V2_INDEPENDENT_RESULTS.json', 'review_v2.py')}, ensure_ascii=False))
