# 测试素材与正式角色

`test_fixture/idle_normal` 是两张 16×16 RGBA 工程色条帧，12 FPS。`python3 -B build/check_assets.py` 调用原资产选择器，验证 IDLE 的循环语义、帧序、元数据、PNG 校验和与像素长度。`public_cues` 保存公开业务提示音，字体文件的来源与许可在 `fonts/licenses`。

正式雪妃使用 R4 原生渲染器，配置为 16 FPS。原画面的五件输入分别为 model.runtime.json、model.source.ems.json、source_profile.json、yuk_0.ems.resx.json 和 tex-texture.png。其完整路径和哈希均在 `board/release_9a4f.json`，由原素材持有者在包外提供。头像资源准备还可使用 `src/scripts/prepare_avatar_frames.py` 和 `src/scripts/board_export.py` 处理已有素材。所有输出保存在单独工作副本；色条只验证读取机制。
