# 完整内核与 ZOCL 入口复验

本次在独立工作区执行 prepare、kernel、module 三阶段并通过。完整 vmlinux/modules/Module.symvers 和新 ZOCL 均生成；没有安装或加载新内核/模块。

内核并行 8；准备与模块编译并行 4。配置仅 CONFIG_CC_VERSION_TEXT 的 .real 文本差异；release 与原镜像匹配。上游源码与原封存证据保留。

- 新模块 SHA-256：9c1e7c008b07442e8b7beb8d2938fccf5d5ea950b13fc2a6172d330304715b78
- 新模块 srcversion：9BDC942A6014BCCBD1DCB78
- 新模块 vermagic：5.15.36-xilinx-v2022.2 SMP mod_unload aarch64
- Kernel Module.symvers SHA-256：6e582b60f2a379055924117f930e5ca0fac44c98d56f3b374dc3ce278da7b8ed
- 与旧内核符号表一致：True
- 与已板测修复模块逐字节一致：False

完整原始日志在 [evidence/reproduction/c](../evidence/reproduction/c/)。新模块属于本次主机输出；本次没有新的板测。启用仍使用 tested_inputs/ 中已板测输入，不要用编译成功替代实时预检和同图复验。
