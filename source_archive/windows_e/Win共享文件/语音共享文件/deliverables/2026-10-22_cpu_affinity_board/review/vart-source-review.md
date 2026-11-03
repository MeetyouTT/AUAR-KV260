主任务后续更新：已从当时相机449083实际maps读取当前vart.so及libvart-runner.so.3.0.0的SHA，见[数字证据](../evidence/vart-hashes.json)。未关联构建manifest或源码commit，下面“尚未保存SHA”为此前审查时点，源码匹配限制仍成立。更广范围readelf查询曾3秒超时，未取得完整Build ID；之后仅对两个实际VART映射文件作有界哈希，无新runner/DPU作业。

# VART Python绑定的GIL行为：官方源证据与实际版本边界

2026-10-22。本终端仅检索本机已有证据及Xilinx官方源码，没有访问板卡或启动模型。

**已确认官方Vitis-AI v3.0实现会在native `execute_async`调用期间释放GIL，随后重新获取。尚未证明板端实际`vart.so`与这一提交完全一致，不能据此认定本次长尾根因。**

来源固定为官方仓库`Xilinx/Vitis-AI`的`v3.0`，GitHub tree返回commit `2057c588c241c3902353bc618afc8ab214d7aeed`。获取文件与SHA保存在`vart-source/provenance.json`。

- [官方runner_py_module.cpp第258–290行](https://github.com/Xilinx/Vitis-AI/blob/2057c588c241c3902353bc618afc8ab214d7aeed/src/vai_runtime/vart/runner/python/runner_py_module.cpp#L258)：先在GIL保护下把Python缓冲转为TensorBuffer；native执行处局部作用域创建`py::gil_scoped_release`；离开此作用域时重新获取GIL，再把缓冲登记到job映射并返回。Python外层测到的整个API墙钟可以包含native调用、重新取得GIL及后续包装工作，不能当纯DPU计算时间。
- [同源第291–302行wait绑定](https://github.com/Xilinx/Vitis-AI/blob/2057c588c241c3902353bc618afc8ab214d7aeed/src/vai_runtime/vart/runner/python/runner_py_module.cpp#L291)：该lambda未显式释放GIL，调用`self->wait`后清理映射。本结论只针对这个具体绑定代码；不能从API名称“async”推断底层实现等待位置。

已有板端取证`aura-identity-dpu-check-20261018/evidence/20261019T022340.098962Z-startup-diagnose/response.json`记录导入来源为`/usr/lib/python3.9/site-packages/vart.so`。该证据没有保存当前二进制SHA、Build ID或明确源码commit，因此不能自动把官方v3.0等同当前板库。本机还能找到历史镜像提取的`libvart-*.so.3.0.0`，它们属于历史工件，不能代替当前映射/构建核对。

本次trace的API墙钟、调用线程CPU以及自愿/非自愿切换，只能说明等待发生在这一API区间；不能据此分解GIL重获、OS调度、native同步和硬件完成各自耗时。即使实际库核对为此源，存在release/reacquire也只是可解释路径，不能证明这次31ms是哪条路径造成。

后续如需缩小边界，可由主任务独占板卡时只读保存：实际相机进程`/proc/<PID>/maps`中的VART/XIR/XRT映射路径、对应文件SHA与ELF Build ID、现有安装包版本/来源。无需再建runner或相机。完成版本关联后，才设计针对性的受控观测；本记录不建议直接部署C++改造或放宽30ms保护。
