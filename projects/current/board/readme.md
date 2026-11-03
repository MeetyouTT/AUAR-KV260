# Ubuntu 离线部署

`install.sh` 在一个全新目录中还原目标文件系统的布局。`board/release_9a4f.json` 固定 380 项业务原件，`camera_release.json` 固定独立相机 224 项，`deploy.json` 提供两个服务的实际 drop-in 顺序、相机预检路径、25 项转轴控制文件的目标位置、原件 SHA 及配置映射。

在工程根目录运行。`INPUTS` 是使用者有权读取的原始归档副本，或专为本次整理的依赖目录。本次验证使用 Ubuntu 上保存的旧交付目录和两个更新原件，索引只记录与白名单匹配的文件；索引应保存在包外。

```sh
sh board/install.sh plan
sh board/install.sh index --input-root "$INPUTS" --out "$OUT/inputs.json"
sh board/install.sh board --index "$OUT/inputs.json" --audio "$AUDIO_ZIP" --out "$OUT/offline-board"
sh board/install.sh windows --index "$OUT/inputs.json" --out "$OUT/historical-host"
```

可多次给出 `--input-root`。`--audio` 接受独立的 `auar_board_audio_dependencies.zip`，逐个验证 15 项 ASR、前端、说话人模型和 ARM64 轮子，然后按业务配置的目录写入。省略此参数会在回执中记录 0 项。`stage_result.json` 给出实际组件个数和启动清单 SHA。安装失败时清除临时树，不发布半套目录。

同版外置文件和相同配置全部到位时，`exact_9a4f` 为 true。现场可以通过 `--site private.json` 填写模板中列出的字符串和整数。新值会生成新的启动指纹。角色模型、纹理、Persona 及原生渲染库的签名仍须满足正式角色入口。新编译的 SO 可以单独验证和评审，切换正式绑定需要一份符合实际文件的新发布清单。

四个 GUI 设置采用原读写器生成，按原正式路径安装，权限为 0600。持久服务默认关闭，音量 100、静音关闭、全屏开启，可在现场按用户选择更新。包内提供正式角色入口需要的 index.html 和 player.js。启动器还会检查内核、触摸模块和显示链；摄像头的本次启动标识、私有业务库、注册人脸、声纹、对话记录及密钥由设备自身建立。

`system/image_manifest.json` 记录原 SD 映像的文件名、31,914,983,424 字节、整镜像 SHA 和分区偏移。该镜像为队伍归档，持有者可在 Ubuntu 只读提取第 2 分区。固件导出目录中包含 BIT.BIN、DTBO、XCLBIN 与 shell.json，固件名须与设备树一致。整机上电、触屏、实时推理和执行器检查单独在目标机上执行。

## 历史 ID/STOP 验收源码

`sh board/install.sh bench --index "$OUT/inputs.json" --out "$OUT/id-stop"` 将原 candidate-manifest、两个驱动源文件、固定 libvsrv 输入与验收脚本归位。`python3 -B "$OUT/id-stop/bench_identity_stop.py"` 的缺省行为是打印计划。实板受控前提和开机身份由原脚本核验。历史启动回执只作为精确还原的包外输入，当前开机绑定须从目标机重新生成。
