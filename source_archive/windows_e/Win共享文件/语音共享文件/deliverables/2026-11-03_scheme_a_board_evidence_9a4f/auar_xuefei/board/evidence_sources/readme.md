# 历史采集与比对源码

本目录按实验日期保存原采集/统计脚本，原文件SHA登记在 board/evidence_sources.json。部分脚本保留原实验路径、套件位置和操作条件，作为过程依据。

日常离线复核使用 board/verify_evidence.py，目标板只读安装检查使用 board/bringup/check_runtime.py。新的两个YuNet合成输入采集入口为 board/bringup/run_yunet_synthetic.py，其模型和运行范围列在帮助和上板说明中。
