"""Retrieval limits must reach the model even when no source fits the query."""
import pytest

from board.runtime.board_memory_policy import BoardContextBuilder


def content(messages):
    return '\n'.join(message['content'] for message in messages[:-1])


def test_empty_cross_boundary_packet_explains_missing_summaries_and_does_not_use_current_facts():
    builder = BoardContextBuilder('你是汐蓝，按已保存资料回答。')
    messages = builder({'messages': [], 'facts': [{'key': '项目', 'value': '不应加入历史回答'}]},
                       '昨天做过什么？', {'items': [], 'status': {'boundary_incomplete': True,
                        'boundary_omitted_summaries': 1, 'absence_proven': False}})
    result = content(messages)
    assert '跨越查询时间边界' in result and '不证明没有记录' in result
    assert '不应加入历史回答' not in result
    assert builder.metrics['history_boundary_incomplete'] is True
    assert builder.metrics['history_items'] == 0


def test_limited_results_keep_scope_filtered_sources_and_report_limit():
    builder = BoardContextBuilder('你是汐蓝。')
    messages = builder({}, '那次发生了什么？', {'items': [{'source': 'timeline_summary',
        'start_utc': 1000, 'end_utc': 1010, 'text': '公开的书单讨论。', 'private_internal_id': 'must-not-appear'}],
        'status': {'result_limited': True, 'matching_count': 21, 'returned_count': 20}})
    result = content(messages)
    assert '条数上限' in result and '公开的书单讨论' in result
    assert 'must-not-appear' not in result
    assert builder.metrics['history_result_limited'] is True


def test_budget_omission_is_counted_without_truncating_source():
    builder = BoardContextBuilder('你是汐蓝。')
    text = '这是无法完整放入上下文的一条历史。' * 200
    messages = builder({}, '回忆那次。', {'items': [{'text': text}], 'status': {}})
    assert text not in content(messages)
    assert '不证明没有记录' in content(messages)
    assert builder.metrics['history_items_omitted'] == 1
    assert builder.metrics['budget_upper_bound'] <= 2048


@pytest.mark.parametrize('packet', [{'items': 'bad', 'status': {}}, {'items': [], 'status': []}, 'bad'])
def test_invalid_retrieval_packets_fail_closed(packet):
    with pytest.raises(ValueError):
        BoardContextBuilder('你是汐蓝。')({}, '回忆。', packet)
