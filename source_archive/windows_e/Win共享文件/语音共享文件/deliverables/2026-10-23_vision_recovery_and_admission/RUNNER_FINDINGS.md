# native等待语义的新增核验

板上`/usr/lib/libvart-dpu-runner.so.3.0.0`，485488字节、SHA `bd832bce56ee01878cdc2fec90f6bc7a5877ab7077dc73a5a069f343ea3b290c`，与此前运行库指纹一致。只读查询其动态符号并反汇编命名函数，未导入/运行额外runner。

`vart::dpu::DpuRunnerDdr::wait(int,int)`地址0x54720：BTI、`mov w0,#0`、`ret`。也就是这份库中的DDR实现的wait直接返回成功。`execute_async`的已读取片段有prepare_input与0x5a790对start_dpu2的调用，后续完整正常路径尚未全部反汇编。本次没有读取进程私有内存、修改库、创建新DPU owner，或者证明Python虚调用的具体对象一定是DDR类。

这进一步说明“Python wait只耗0.09ms”本身不能排除设备/驱动耗时，因为相应实现可以在execute_async内完成计算，而wait仅作返回/清理。不能从函数名async推定它立即返回；也不能把native区间全部叫硬件计算时间。现有四点probe仍需用真实故障判断等待发生在native还是重新获取GIL。

官方v3.0参考源码也在DDR的execute_async中依次准备输入、start_dpu2、准备输出，wait直接返回0；它是行为参考，**准确源码提交仍未与板端ELF匹配**。[官方参考源](https://github.com/Xilinx/Vitis-AI/blob/2057c588c241c3902353bc618afc8ab214d7aeed/src/vai_runtime/vart/dpu-runner/src/imp/dpu_runner_ddr.cpp)。获取来源/哈希在`upstream-reference/provenance.json`；原件留本机，交付只附来源与必要结论。

传输工具初次将objdump的“同名debug文件CRC不符、已忽略”警告与stdout合并，导致run_probe的JSON解析失败。实际framed UART退出0且摘要匹配；本机按完整帧重组并校验后，从首个JSON对象提取runner-symbols.json，没有把无调试信息当成额外符号来源。这是证据读取方式的修正，不是模型推理失败。
