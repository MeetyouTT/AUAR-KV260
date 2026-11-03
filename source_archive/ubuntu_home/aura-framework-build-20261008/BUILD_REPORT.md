# 框架搭建完成记录

主仓：`/home/ghmd/Win共享文件/共享文件夹/aura`。

框架说明与快速启动：主仓 `docs/PROJECT_FRAMEWORK.md`。
实际状态：主仓 `docs/FRAMEWORK_STATUS.md`。
实际验证输出：主仓 `metrics/raw/framework-validation-20261009/{validation,package_validation}.json`。
重要项目日志：`/home/ghmd/AMD_Smart/logs/daily/2026-10-09-PROJECT-FRAMEWORK-BUILD.md`。

框架 41 项测试通过，固定/可变软件联调各 10 项通过，媒体模拟管线 6 项通过。源包 121 个条目校验通过，移机 doctor/demo/media 从 `/tmp` 工作目录启动通过。

源包：`artifacts/releases/aura-framework-20261009T072032Z-a77949-source.zip`，36,501,183 字节。
SHA256：`1825f5f9120dc842551ebe4b7c69dcad903ecf7e8e493fe95a0f24e3924cfa42`。

`baseline/` 保留任务前 README 和 EventBus 原件。`relocation-q74k_l8l/` 保留实际迁移副本与联调证据。源仓旧声线、素材、报告和演示工具保留。

不将软件模拟写成板测。DPU 项目模型、ByteTrack/Light-ASD 实际推理、MCP01/真实媒体模型/跨机传输、PL 绝对源期限和机构标定仍待接入。未启动硬件或 GUI。
