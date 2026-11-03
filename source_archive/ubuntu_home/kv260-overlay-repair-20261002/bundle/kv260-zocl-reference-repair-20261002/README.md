# KV260 ZOCL 修复候选

状态：主机编译及核验通过，板端验证未执行；已按用户要求暂停。

`zocl.ko` 为本轮新编译候选。完整源码基底 commit、补丁摘要和兼容性证据见 BUILD.json；fix.patch 可应用于固定 XRT commit。

先核对 SHA256SUMS，接续方案见 BOARD_VALIDATION_PLAN.md。保持磁盘原驱动及原固件，先完成实时身份核验和原状态备份；候选只从独立 staging 临时加载。

主机核验不能替代板端卸载、推理及恢复验收。没有安装脚本或自动切换入口。
