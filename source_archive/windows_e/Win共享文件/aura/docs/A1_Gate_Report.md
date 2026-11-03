# A1 Gate 报告 —— 运行时骨架与集成合同

> 版本：V1.0 ｜ 计划日期：2026-09-07 ｜ 验证日期：2026-08-31（骨架提前完成）
> 主持：人3（Runtime & Integration）｜ 参与：全员（B 档 3 人）
> 范围：Week A1（9/1—9/7）人3 交付物
> 环境标签：**PC / SIMULATED**（无实体板卡；板卡 9 月底到货）

---

## 一、Gate 结论

| 结论 | 说明 |
|---|---|
| **有条件通过（Conditional PASS）** | 功能与自动测试全部达标；剩余 2 项闭合项见 §六 |

## 二、A1 交付清单（对应人3 任务书 Week A1）

| 日期 | 任务 | 交付物 | 状态 |
|---|---|---|---|
| 9/1 | 事件、状态和依赖梳理 | `board/runtime/events.py`：事件类型全集 + 优先级 + 队列策略映射 | ✅ |
| 9/2 | Event Envelope + 有界 Event Bus | `board/runtime/event_bus.py`：EventEnvelope / BoundedQueue / EventBus（4 种入队策略） | ✅ |
| 9/3 | FSM 正常与故障状态 | `board/runtime/fsm.py`：9 态 + CANCELLED 瞬时回迁 + EventBus 自动绑定 | ✅ |
| 9/4 | 三层 Validator 骨架 | `board/runtime/validator/`：Schema / Semantic / Policy + ValidationChain | ✅ |
| 9/5 | Adapter 合同与 MockBoard 接入 | `dialogue_client/adapter.py` + `mock_adapter.py`；`mocks/mock_board.py` | ✅ |
| 9/6 | 三类纵向冒烟 | `examples/smoke.py`：正常对话流 / 断链回退 / 取消 / MockBoard 故障注入 | ✅ |
| 9/7 | 主持 A1 Gate | 本报告 | ✅ |

## 三、验证结果（PC 实测）

| 验证项 | 命令 | 结果 |
|---|---|---|
| 单元测试 | `python -m pytest tests/ -q` | **60 passed in ~1.7s**（5 个测试文件） |
| 纵向冒烟 | `python examples/smoke.py` | 4 场景全部通过（见下） |

**执行环境**：Windows 11 开发主机 ｜ Python 3.12.7 ｜ pytest 9.1.1 ｜ jsonschema 4.26.0

**冒烟场景明细**：
1. 正常对话流：person enter → KWS → VAD end → 请求 → 三层校验通过 → SPEAKING → 播完 IDLE
2. 断链回退：NETWORK_LOST（本地模式）→ 本地 KWS 可聆听 → 网络恢复 → IDLE
3. 取消：SPEAKING 中实体键取消 → CANCELLED（瞬时）→ 有人则回 PRESENT
4. MockBoard：camera 掉线注入 + BOX0 寄存器读写 + 环境标签恒为 SIMULATED

## 四、Gate 固定问题逐项回答（V1.0 §14.3）

| # | 固定问题 | 回答 |
|---|---|---|
| 1 | 功能是否真机可运行？ | 开发主机（PC）可运行；实体板卡待 9 月底到货后为 **BOARD_REQUIRED** |
| 2 | 确切硬件/模型/bitstream/软件版本？ | 无板阶段：PC + Python 3.12.7 + pytest 9.1.1 + jsonschema 4.26.0；模型/bitstream 属于板卡阶段，本次不涉及 |
| 3 | 输入、输出、验收阈值？ | 见 §五 数据合同与验收阈值 |
| 4 | 原始证据在哪里？ | 工程代码 `wujing-lite/`；单测/冒烟输出可一键复现（§六 证据索引） |
| 5 | 失败时如何降级？ | 断链→CORE_LOCAL（NETWORK_LOST 本地模式）；请求超时→IDLE；非法响应→丢弃改"不确定"；订阅者异常不中断总线 |
| 6 | 是否满足评分标准？ | 是：A1 为 evidence/05_stability（运行时骨架）与 07_deliverables（数据合同/ADR）的基础，无板阶段证据合规 |
| 7 | 是否引入新外部依赖？ | 仅 `jsonschema`（Python 包，已在 pyproject.toml 声明）；无新硬件依赖 |
| 8 | 是否与"固定式、无转轴"范围一致？ | 是：无任何旋转/舵机/运动相关代码或依赖 |
| 9 | 是否有夸大或无法证明的表述？ | 无：所有结论带 PC/SIMULATED 环境标签，不包含板端实测、LAN 对话或真实 ASR/LLM 声明 |

## 五、数据合同与验收阈值

| 模块 | 输入 | 输出 | 关键阈值 |
|---|---|---|---|
| Event Bus | EventEnvelope | 入队结果 + metrics | 满队列策略：critical 零丢失；frame 丢旧保新 |
| FSM | EventEnvelope 序列 | StateChange / 状态 | 9 态全覆盖；非法转换拒绝不崩溃；相同输入确定性一致 |
| Validator | DialogueResponse + Context | ValidationResult | 伪造视觉事实/过期/越权 100% 拒绝 |
| Adapter | DialogueRequest | DialogueResponse | 超时抛 TimeoutError；断链可重连；旧响应不覆盖新请求 |
| MockBoard | 寄存器/外设操作 | 状态/计数器 | 环境标签恒为 SIMULATED |

## 六、DoD 六项检查（V1.0 §14.1）

| # | DoD 项 | 状态 | 备注 |
|---|---|---|---|
| 1 | 可运行代码 | ✅ | `wujing-lite/board/runtime/` 全链路可运行 |
| 2 | 固定版本和依赖 | ✅ | 依赖冻结于 `pyproject.toml`；git 基线 commit **`9cf7689`**（2026-08-31） |
| 3 | 明确输入/预期输出 | ✅ | `schemas/*.json` 数据合同 + 各模块契约 |
| 4 | 自动测试/回放证据 | ✅ | 60 单测 + 4 冒烟场景，可一键复现 |
| 5 | 原始日志/截图/视频 | ⚠️ | 测试输出可复现；正式证据归档待 `evidence/` 目录建立后固化 |
| 6 | 非作者复核 | ⚠️ | **待第二人复核签字**（A1 Gate 会议） |

## 七、跨角色交接状态

| 流向 | 内容 | 计划 | 状态 |
|---|---|---|---|
| 人1→人3 | MockBoard、寄存器合同、FPGA 状态 | 9/6、9/10 | 待交接（MockBoard 已按 V1.0 §11.2 占位实现） |
| 人2→人3 | Detection/Scene schema、tracker 事件 | 9/4、9/10 | 待交接（scene_state schema 已按 V1.0 §8.4 占位冻结） |

## 八、证据索引

| 证据 | 路径/命令 |
|---|---|
| 事件清单 | `board/runtime/events.py` |
| 架构文档 | `docs/runtime_architecture.md` |
| 数据合同 | `schemas/dialogue_request.schema.json`、`dialogue_response.schema.json`、`scene_state.schema.json` |
| 单测复现 | `python -m pytest tests/ -q` → 60 passed |
| 冒烟复现 | `python examples/smoke.py` → 4 场景通过 |
| 依赖清单 | `pyproject.toml` |

## 九、风险与未决项

| 项 | 类型 | 处置 |
|---|---|---|
| 工程未纳入 git | ✅ 已解决 | 2026-08-31 `git init` + 首次 commit **`9cf7689`**（本地，未关联远程） |
| A1 完成时间早于计划（8/31 vs 9/7） | 正向偏差 | 提前进入 A2（UI/KWS）或补强 Validator 反例集，见 §十 |
| MockBoard/寄存器合同最终以人1 交接为准 | 接口依赖 | 保持接口签名，收到正式合同后仅改实现 |
| LAN 真实 WebSocketAdapter | 后续 | A3 实现，本轮仅 Mock 合同验证 |

## 十、结论

A1 Gate 判定为**有条件通过**：

1. ✅ 运行时骨架（Event Bus / FSM / Validator / Adapter / MockBoard）全部实现并通过 60 项单测与 4 场景冒烟；
2. ✅ 数据合同、队列策略、9 态 FSM、三层校验与"无证据不伪造事实"红线均已落地并验证；
3. ⚠️ 闭合项：git 版本化、第二人复核签字（A1 Gate 会议）、正式 evidence 归档。

**通过门槛复核**：第三人可依据 `wujing-lite/README.md` 一键复现测试与冒烟 → **满足**。

### 签字栏

| 角色 | 姓名 | 日期 | 签字 |
|---|---|---|---|
| 人3（Responsible） | ________ | 2026-09-07 | |
| 复核人（Reviewer） | ________ | 2026-09-07 | |
| 项目负责人 | ________ | 2026-09-07 | |

> 版本记录：V1.0（2026-08-31 生成，Gate 计划日 9/7）。
