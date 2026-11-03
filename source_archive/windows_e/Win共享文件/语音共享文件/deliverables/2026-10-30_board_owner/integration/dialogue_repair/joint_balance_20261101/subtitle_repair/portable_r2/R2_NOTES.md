# ARM 公开夹具修订 R2

R1 在 ARM 失败于测试夹具编译，生产尚未改变。真实 jobs 源含 `from __future__ import annotations`，AST 摘取时 R1 没有把该语义带入新模块，导致旧 Python 解释器立即计算 `str | None`。这不是候选生产修复的执行错误。

R2 只更改 harness：两处 compile 显式指定 `__future__.annotations.compiler_flag` 和 `dont_inherit=True`，恢复原模块注解语义；不改实际摘取的类/方法 AST。为支持 dataclasses 对延期注解的识别，仅在 exec 期间注册一个唯一名字的公开 ModuleType，执行结束立即清理。

新增一项公开检查验证真实 `_Job.entry` 的 union 注解保持字符串、不即时计算，两个编译批次共享同一受控 namespace，且临时模块已清理。原有 18 项、投影 10 项/500 例不扩展。19 + 10/500 已在本机同入口通过。

`run_portable_validation.py` 每次运行记录 `sys.version`、version_info、platform、machine 和各脚本返回码至 `PORTABLE_RUN_RESULT.json`。所需功能最低组合为 Python 3.8（dataclasses / future annotations 自 3.7，AST Module 的 type_ignores 字段自 3.8）；这不是对未运行版本的通过声明。ARM 结果须由唯一设备窗口另行实测。

生产候选仍为 de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2；before/after 和五个公开夹具源与 R1 逐字节一致。原 R1 归档、原测试结果与 ARM 失败证据保留。
