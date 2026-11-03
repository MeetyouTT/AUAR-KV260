# Mali GLES2 局部 UV 渲染候选

独立副本，未改 host 主文件、candidate_core、原 PNG、TextureBinding 或配置，未连接板卡、未启动服务。保留 AGPL 标记。

生产合并文件仅三个：gles2_renderer.cpp、gles2_renderer.hpp、tile_uv.hpp。第三项是纯 CPU、无 GL 的 header-only 适配器，无新增必需编译 TU。构造函数改为 `Renderer(scene, imported.asset, root)`；host/yuki_host.cpp 和 host/diagnostic_api.cpp 两个构造位置都需传入既有导入结果的 asset。asset 只在构造时读取，不借用其生命周期。

初始化按 ModelAsset::icons 导入矩形，从对应 TextureBinding 的原 PNG 解码一次，裁出带真实图集相邻像素的2px边界，边界在原图边缘截断；不复制图块自身边缘代替邻边。纹理仍为 RGBA8、LINEAR、CLAMP_TO_EDGE、无 mipmap。不上传完整 atlas GPU 纹理。UV 不增减半 texel 偏移、不变换旋转/attr：沿用当前 core 输出的 atlas UV 方向和范围。

Yuki68张 tile 合计27,415,660B（26.15MiB），原 atlas 为64MiB。若驱动把每张内部存储均上取整到2次幂，保守总量为58,073,088B（55.38MiB），尚未包含驱动对象开销。最大宽818、最大高2198；最长头发仍可能受 mediump 精度影响。初始化 CPU 峰值包含64MiB解码整图＋最大约4.06MiB裁图临时缓冲，之后释放。FBO/geometry缓存按既有输出尺寸与 scene capacity 另算。

每帧复制原始 RenderFrame 顶点到预分配空间，以 TextureId＋原 atlas UV 四边识别完整图块；缓存 first_index→tile，同一主/遮罩 range 只处理一次。顶点索引另有 tile 标记，从原始帧转换保证幂等。每帧重新核对范围四边，资源切换不会复用旧 tile。缓存、顶点、索引、GPU主缓冲均在构造时分配，正常固定尺寸 draw 无文件读取、GPU读回、new、map 插入或纹理上传。

未知 UV、UV 歧义、同 first_index 的冲突描述、同顶点属于不同裁图、越界索引/容量、原图外 icon 以及超纹理预算明确报错。当前实现针对 runtime 输出的完整 icon commands；任意裁剪子网格或合并多图块的 command 不在契约内。

索引、坐标、顶点颜色、mask source/definition、混合和五位覆盖 FBO 路径保持原语义。最终合成 quad 使用独立静态 VBO/EBO，仅 resize 时重写 quad；不再同一帧末尾覆盖已提交的模型 VBO。跨帧 GPU 压力与 texture bind 的实际耗时仍需 Mali 实测，不能由此保证零 stall。

CPU 测试入口：

```sh
cmake -S native_integration/precision_candidate -B native_integration/build_precision_cpu
cmake --build native_integration/build_precision_cpu --parallel 1
native_integration/build_precision_cpu/uv_remap_test
```

测试包括主/遮罩共享 range、重复帧、同 range 资源/atlas 切换、真实68图块、边界裁图、显式失败与500次 steady allocation 计数。allocator override 只在测试独立 TU，不进入 renderer。测试无需 JSON、PNG、GL 或 core库链接。

本地没有可用 C++编译器，WSL只读清单命令返回 E_ACCESSDENIED，未运行 C++/GLES测试、未为此安装依赖。父代理统一编译与GPU对照。cpu-layout-evidence.json 仅是已执行的独立 Python 几何/采样检验：本机无 PIL，使用确定性 RGBA＋alpha图案代入真实图集布局，共3468个点含边界外0.4px；不宣称原图像素或Mali输出。理想 bilinear 最大差约1.3e-11/255，Float32局部 UV 往返最大5.61e-5 atlas像素。IEEE-half误差估计也仅是数值模型，不是Mali测量。

后续验收：C++ CPU测试、原PNG裁图实际上传、两pose/六脸/遮罩边缘/全部timeline以及300秒GTK P99。正常draw无读回；capture()仍是显式离线诊断接口，保留便于同条件截图。
