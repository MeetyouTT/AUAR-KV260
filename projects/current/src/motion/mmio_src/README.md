本目录是独立 VSRV/2 只读批量读取候选。没有访问 UART、真实 MMIO、板卡或生产服务，没有修改原 bundle、固件或 write 保护。

新增 API：

```c
int vsrv_read_many(void *opaque,const unsigned *offsets,unsigned count,uint32_t *results);
int vsrv_snapshot(void *opaque,uint32_t *results);
```

`read_many` 只接受1..32项原有可读偏移，禁止0x24、未对齐或超范围偏移。整批读取前、后各执行原 platform() 四项文件保护与实时 MMIO ID/ABI/BUILD 核对；没有跨调用缓存。每轮读前后检查ACK，最多3轮。任何参数、平台、身份或序号验证失败时，调用方results保持原样，不返回部分数据。不增加任何写入API，也不修改已有 vsrv_read、vsrv_write、vsrv_open、vsrv_close 的函数体与保护。

固定12项 snapshot 顺序为 `ID, ABI, BUILD, ACK, FLAGS, WIDTH, LEASE, SESSION, EPOCH, REFERENCE, TARGET, ACK`；偏移为 `0,4,8,0x28,0x0c,0x2c,0x30,0x34,0x38,0x40,0x44,0x28`。调用方仍应核对精确ID/ABI/BUILD及首尾ACK，并维持原上下文、命令范围、源期限、逐写保护与单writer合同。租约/flags可在快照期间自然下降，与原驱动状态读取合同相同。

成功status路径原先12次单word read各做四次文件open/read/close，共48次；本候选每整批开始和结束各四次，共8次。18组host fake测试验证此计数。性能收益尚未在目标板测量，不能把文件操作计数当作实测时延。

`python3 build.py` 可复现普通host检查、ASAN/UBSAN检查与指定Vitis GCC的AArch64共享库编译。Host测试使用完整相同C实现，仅替换文件/权限/映射/MMIO为计数与可注入错误的fake，真实文件/MMIO访问0。生产共享库未定义 VSRV_MMIO_TEST，保留AArch64屏障与word访问，没有导出fake回调。

测试覆盖成功12word快照/3word身份/普通数组、全部参数拒绝、boot/CID/FDT/FPGA任一不符、非root、ID/ABI/BUILD不符、整批结束平台变化/身份变化、ACK重试/持续变化拒绝、失败输出不变、旧read逐调用保护、旧write逐调用保护、独占flock、正常open/close及STOP。

共享库路径、SHA256、工具链、结果与原函数体一致性核验见 validation.json。consumer由root统一pin并接入；板级与机械效果仍待实测。
