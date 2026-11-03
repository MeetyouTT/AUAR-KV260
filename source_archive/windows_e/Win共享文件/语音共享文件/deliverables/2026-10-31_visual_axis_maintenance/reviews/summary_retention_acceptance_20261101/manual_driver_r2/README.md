# R2：隔离命名空间，仅完成本地验证

R1 已真实失败：内嵌 SOURCE 覆盖 select 模块和 state() 检查函数，导致第二轮轮询 AttributeError、最终检查 TypeError。R1 冻结文件、原观察失败、用户“位置不对或不记得”反馈均保留；观察错误不能证明回答错误的原因。

R2 只把 common、control、observer 的执行字典隔离。现有 79af 控制代码、4a01 观察代码及 UI record_start/stop 不变，无 toggle、select_conversation 或 cancel。15 项本地公开测试通过，包含真实 SOURCE 三轮、accepted request、完整 ACK、自然收尾和最终 guard；尚未实机重试。

任何实机重试仍需新鲜完整 guard、用户就位和明确的重试安排。当前保持暂停，先按授权恢复 R1 回答的哈希和同范围证据。monitor_owned 无公共直接读回的限制保留。
