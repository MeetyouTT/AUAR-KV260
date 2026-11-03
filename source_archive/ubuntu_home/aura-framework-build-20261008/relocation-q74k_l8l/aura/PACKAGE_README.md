# AURA·汐蓝框架源包

解压后进入 aura，先读 docs/PROJECT_FRAMEWORK.md 和 docs/FRAMEWORK_STATUS.md。
Python 3.8+ 标准库可运行：

    python -s tools/aura_project.py doctor
    python -s tools/aura_project.py demo
    python -s tools/aura_host.py
    python -s -m unittest discover -s tests/framework -v

Windows 也可双击 tools/run_project.bat；Linux 用 bash tools/run_project.sh。
模拟证据不能替代板端结果；默认物理运动禁用。
媒体 fixture 不执行真实 ASR/VLM/TTS；默认源包不含动画素材。
原设备部署、音频模型、个人身份库、bitstream/overlay 和本机环境未打包。
UI 需要既有素材及对应依赖。release_manifest.json 记录每个条目及是否带素材。
源仓旧 README 中的共享目录相邻交付链接属于历史资料，源包未包含那些目录。
