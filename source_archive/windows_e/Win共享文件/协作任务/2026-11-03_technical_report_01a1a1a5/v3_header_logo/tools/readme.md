本修订版由 apply_header_logo.py 给 Word 设置重复页眉，左侧为4cm比赛logo，右侧为自动页码，下方0.5pt细线。build_word.py已接入此步骤。

# 工具使用说明

这些脚本对应本次实际工作。请在完整报告包的新副本中运行，避免改写已经归档的测量和回执。

- build_word.py 用 python-docx 从 report/technical_report.md 生成 Word。脚本中的 Windows 字体路径对应本机。
- export_word.ps1 使用 Microsoft Word 的隐藏 COM 实例更新目录并导出同版 PDF；只打开本报告，不接管其他文档。
- build_diagrams.py 用 ReportLab 和 Poppler 生成五张机制图的 PDF 与 PNG。
- ubuntu_charts.py 从 data/live_resources.csv 与 live_rtt.csv 绘制三组新曲线。可在 Ubuntu 已有 Vitis AI CPU 容器执行，Matplotlib 版本 3.4.3。
- collect_live.py 用已配置的 aura-kv260 SSH 连接只读采集状态、当前 X11 页面、资源与 ICMP。默认约 60 秒；不发录音、推理或运动命令。采样期间仍可能受现场原有业务影响。
- prepare_evidence.py 从采样计算指标，并通过 aura-ubuntu 取四套 XSim 回执。读取临时完整健康状态后只将所需汇总纳入公开证据。
- qa_report.py 用本机打包 Poppler 渲染 PDF 供逐页检查。QA 图片没有包含在交付 ZIP 中。

本机文档工具包没有 LibreOffice 可执行文件，canonical render_docx.py 因找不到 soffice.exe 失败。本报告使用已安装 Microsoft Word 原生导出，再由打包 Poppler 渲染检查，因此 PDF 与交付 Word 的目录、分页来自同一份实际文档。

XSim 的实际命令和日志位于 evidence/ubuntu_rtl。完整工程、模型、固件构建和部署继续使用方案 A 工程包，报告中的命令不是新的工程安装器。
