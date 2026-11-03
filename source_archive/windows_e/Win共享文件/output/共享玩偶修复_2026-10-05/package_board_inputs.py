from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path('E:/项目/共享文件夹/aura')
OUT = Path(__file__).resolve().parent
table = json.loads((ROOT / 'ui/avatar_board_manifest.json').read_text(encoding='utf-8'))
files = [ROOT / p for p in ['ui/avatar_board_manifest.json', 'ui/ui_state.schema.json',
    'ui/ui_layout_spec.json', 'ui/ui_tokens.json', 'board/interaction/lvgl/avatar_assets_table.h']]
for r in table['resources']:
    folder = ROOT / 'assets/avatar' / r['asset']
    files.extend(p for p in [folder / n for n in ['frames.rgb565', 'meta.json', 'segments.json', 'motion.json']] if p.is_file())
entries = [{'file': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
readme = '''AURA avatar board inputs — 2026-10-05
Environment: PC / SIMULATED export; KV260 performance is NOT measured.
15 runtime states, 16 resources, 573 frames, 24fps, 464x480.
frames.rgb565: big-endian R5G6B5, #FCFCF3 alpha composite.
Resolve each frames_file relative to assets/avatar.
Read states.asset_pool / resources.segments and the C pool/window tables.
Play enter -> loop windows -> 150ms blend -> exit; rotate equivalent speaking resources after 6s plus exit.
AWAKE completion without active speech emits AUDIO_PLAYBACK_STOP; active speech actions emit AUDIO_PLAYBACK_START.
Use stream/double-buffer loading: 445440 bytes per frame; 890880 bytes per double buffer.
The 243.41MiB resource bundle is a disk size, not a requirement to keep every frame in RAM.
These are resource inputs, not a runnable KV260 image or a completed LVGL deployment.
Before hardware release measure audio capture/playback, visual cadence, cancellation and long-run stability.
release_manifest.json lists SHA256 and size for each payload file.
'''
archive = OUT / 'aura_avatar_board_inputs_2026-10-05.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as z:
    for p in files:
        z.write(p, p.relative_to(ROOT).as_posix())
    z.writestr('README_BOARD_INPUTS.txt', readme)
    z.writestr('release_manifest.json', json.dumps({'environment': 'PC / SIMULATED',
        'states': 15, 'resources': 16, 'frames': 573, 'files': entries}, indent=2))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
report = {'archive': str(archive), 'bytes': archive.stat().st_size,
          'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'payload_files': len(files),
          'archive_crc_ok': True}
(OUT / 'board_package.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False), flush=True)

handover = ROOT / '.cline-handover.md'
handover.write_text(handover.read_text(encoding='utf-8') + '''

## 2026-10-05 本地修复闭环（覆盖上文相关待办状态）

Tk/Qt共用board/interaction/avatar_player.py；真实tick的语音结束显示过渡及唤醒完成事件已接通。
UiState与业务FSM绑定同一EventBus，正式入口tools/demo_qt.py；10项边界回归覆盖实际tick/Qt绘制/事件总线及取消启动竞态。
完整pytest 480项通过；15态合同0失败0警告；16套RGB565共573帧已重导，逐帧独立比对一致，C头文件编译执行通过。
板端包与日志：工作区output/共享玩偶修复_2026-10-05。当前交接说明docs/共享播放器修复与验证_2026-10-05.md。
保留待验收：KV260/MCP01真实录放音、显示性能、同步、打断与长时间整机稳定性；没有设备实测证据。
''', encoding='utf-8')
