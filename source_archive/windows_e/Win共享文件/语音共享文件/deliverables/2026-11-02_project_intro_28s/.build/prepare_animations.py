from pathlib import Path
from PIL import Image
import json

root = Path(__file__).resolve().parent
source = Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-02_avatar_animation_optimization\revision4_dialogue_motion\board_results\previews\after_R4')
assets = root / 'assets'
clips = {'idle': (0, 32), 'listening': (48, 96), 'speaking': (144, 192), 'thinking': (96, 144), 'positive': (208, 256)}
receipt = []
for name, (start, end) in clips.items():
    # Assemble original render frames into an animation. No retouching, compositing or drawn imagery.
    originals = [Image.open(source / f'{i:04d}.png').convert('RGB') for i in range(start, end, 2)]
    palette = originals[0].quantize(colors=256)
    frames = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in originals]
    target = assets / f'{name}.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=125, loop=0, optimize=False, disposal=2)
    receipt.append({'name': name, 'source': str(source), 'first_frame': start, 'end_exclusive': end, 'fps': 8, 'duration_s': len(frames) / 8, 'path': str(target)})
(root / 'animation_sources.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False))
