# 配置加载和目标文件名

`src/common/config.py` 定位同级的工程根。`src/tools/aura_project.py --config config/runtime.sim.json doctor` 读取框架配置，固定的 `model_manifest.json` 校验两份视觉输入。`character_profile.local.json` 是这里已核过 SHA 的虚构角色选择，模拟示例需要这个实际文件名。

正式 GUI、服务和相机通过各自原加载器读取具体路径。`board/deploy.json` 的 `templates` 给出模板原位、真实加载文件名、完整原件 SHA 与每个现场值的类型。保留 `.example.json` 的配置在离线安装时还原到真实文件名。带 `$site` 的字段从包外的 JSON 对象按完整字段名读取，可用 `sh board/install.sh plan` 查看。原件匹配时可直接恢复原始字节。正式角色选择及 Persona 等强绑定配置保留原件的实际字节。

独立相机以 `src/camera/runtime` 为根。Windows 历史服务有独立的五份配置模板与同名覆盖文件，分别位于 `src/host/model_service/windows_config` 和 `windows_overrides`。安装器按对应 profile 选择，避免在主板端目录混入不同版本。
