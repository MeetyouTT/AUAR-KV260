# 初次 fixture 汇总解析失败

初次运行 `prepare_patch_and_fixtures.py` 的 10 个模拟核日志比较均已执行并通过预期断言。
随后脚本把 `failure-diagnosis.ring.output` 错当纯 JSON，汇总阶段发生 JSONDecodeError。
该证据实际由 STATUS/KERNEL/ANCHOR_END_INDEXES/NEW_LINES 等文本段组成。

这是主机 fixture 证据解析错误，没有执行板端操作，也没有影响 retry 的比较函数。
初次生成的 `offline-kernel-fixtures/` 保留。后续改用分段解析并在新的有时间戳目录
重新执行模拟比较及完整真实前后核日志 fixture，不覆盖初次证据。
