<!-- aura-architecture-generated -->
# src/ui

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C；运行/使用位置：KV260 PS；PC 为开发基线。

内容：状态投影、汐蓝播放器、字幕与授权操作页面。

边界：单独管理显示状态；不直接打开相机/声卡、改库或写寄存器；板端渲染后端待实测冻结。

依据：P2、C9，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/interaction`
- `ui`
- `tools/realtime_stage.py`
- `tools/realtime_facials.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
