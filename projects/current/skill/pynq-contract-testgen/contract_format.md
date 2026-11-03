# 接口合同格式 v1

完整正例见 `examples/adder/contract.json` 与 `examples/crc32/contract.json`。所有列出的根字段均需提供；未知字段会被拒绝。

| 字段 | 含义 |
| --- | --- |
| schema_version | 固定为整数 1 |
| name | 小写 ASCII 标识符，作为工程标签 |
| ip_name | HWH/PYNQ 中的真实 IP 路径，可含 `/` 分层 |
| data_width | 固定为整数 32 |
| addr_range | 所需 IP 地址窗口字节数，4 的倍数；不得超过 HWH 中实际窗口 |
| metadata_source | synthetic_fixture、vivado_export 或 user_supplied；真实运行要求 vivado_export |
| timeout_ms | 1..60000 的整数，启动到观察完成的超时上限 |
| poll_interval_ms | 0..timeout_ms 的整数，轮询间隔 |
| registers | 最多 256 个、按字对齐且无重叠的寄存器定义 |
| inputs / outputs | 数据寄存器逻辑名列表，要求非空且不重叠 |
| control | 启动值、完成掩码与协议定义 |

每个寄存器提供 `name`、`offset`、`width=32`、`access`（ro/wo/rw）、`read_effect`（none/clear）。可选 `hwh_name` 将逻辑名映射到 HWH 寄存器名，默认等于 name。偏移可为 JSON 整数或 `0x` 前缀字符串。

control 中 start 包含 register 和 value，表示对指定寄存器写入整个 32 位命令字。done 包含 register、mask 和 value；当 `read_value & mask == value` 时完成。done_reset 必须为 on_start，表示硬件在启动时清除旧完成状态。首版不支持其他握手协议，数据与控制寄存器不能相互复用。

测试向量是非空列表，每项包含唯一 id、inputs 和 expected。inputs/expected 键必须分别与合同输入/输出完全一致；所有值均为 0..4294967295 的 JSON 整数，不接受负数、浮点、bool 或缺少期望值。

生成器在 HWH 中识别 MODULE 的 FULLNAME/INSTANCE、REGISTER 的 NAME 与 PROPERTY 中的 ADDRESS_OFFSET/SIZE/ACCESS，以及 MEMRANGE 的 BASEVALUE/HIGHVALUE。支持 XML 命名空间；其他元数据变体可能需要适配。多地址窗口、缺少完整寄存器定义等不会被默认为通过。

HWH 的 ACCESS 仅检查读写权限，不验证读清除、命令语义或算法；这些条件必须由可信接口资料与后续对应层级测试确认。合成样例可静态 MATCHED，但报告仍明确是 synthetic_fixture，board_verified 为 false。
