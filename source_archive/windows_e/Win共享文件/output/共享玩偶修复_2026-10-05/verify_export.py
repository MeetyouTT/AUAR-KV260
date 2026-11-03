from pathlib import Path
import hashlib
import json
import sys
import tempfile
import shutil
import subprocess
import numpy as np
from PIL import Image

ROOT = Path('E:/项目/共享文件夹/aura')
OUT = Path(__file__).resolve().parent
table = json.loads((ROOT / 'ui/avatar_board_manifest.json').read_text(encoding='utf-8'))
errors = []
checked = 0
bg = tuple(table['panel_bg_rgb888']) + (255,)
for resource in table['resources']:
    directory = ROOT / 'assets/avatar' / resource['asset']
    files = sorted(directory.glob('*.png'))
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    hashes = {r['file']: r['sha256'] for r in manifest['entries']}
    blob = directory / 'frames.rgb565'
    if blob.stat().st_size != resource['rgb565_bytes_expected']:
        errors.append('size: ' + resource['asset'])
    with blob.open('rb') as stream:
        for png in files:
            if hashlib.sha256(png.read_bytes()).hexdigest() != hashes[png.name]:
                errors.append('PNG modified: ' + str(png))
            with Image.open(png) as im:
                im = im.convert('RGBA')
                rgb = np.asarray(Image.alpha_composite(Image.new('RGBA', im.size, bg), im).convert('RGB'), dtype=np.uint16)
                encoded = ((rgb[:, :, 0] >> 3) << 11) | ((rgb[:, :, 1] >> 2) << 5) | (rgb[:, :, 2] >> 3)
                expected = encoded.astype('>u2').tobytes()
                if stream.read(len(expected)) != expected:
                    errors.append('RGB565 pixel mismatch: ' + str(png))
            checked += 1
    print('checked', resource['asset'], len(files), flush=True)
states = {r['state'] for r in table['states']}
assert len(states) == 15
assert len(table['resources']) == 16
assert all(r['rgb565_packed'] for r in table['resources'])

# Compile and execute the generated C contract, using an ASCII temporary path.
with tempfile.TemporaryDirectory(prefix='aura_contract_') as tmp:
    tmp = Path(tmp)
    shutil.copyfile(ROOT / 'board/interaction/lvgl/avatar_assets_table.h', tmp / 'avatar_assets_table.h')
    (tmp / 'check.c').write_text('''#include "avatar_assets_table.h"
#include <assert.h>
int main(void) {
  assert(AVATAR_ASSETS_COUNT == 15);
  assert(AVATAR_RESOURCES_COUNT == 16);
  for (unsigned i=0; i<AVATAR_RESOURCES_COUNT; ++i) {
    const avatar_resource_t *r = &AVATAR_RESOURCES[i];
    assert(r->fps_milli == 24000);
    assert(r->rgb565_bytes == r->width*r->height*2u*r->frames);
    for (unsigned j=0; j<r->windows_count; ++j) {
      avatar_window_t w = AVATAR_LOOP_WINDOWS[r->windows_offset+j];
      assert(w.start <= w.end && w.end < r->frames);
    }
  }
  for (unsigned i=0; i<AVATAR_ASSETS_COUNT; ++i) {
    avatar_pool_t p = AVATAR_STATE_POOLS[i];
    assert(p.count > 0);
    for (unsigned j=0; j<p.count; ++j) assert(AVATAR_POOL_INDICES[p.offset+j] < AVATAR_RESOURCES_COUNT);
  }
  assert(AVATAR_BLEND_MS == 150 && AVATAR_POOL_SWITCH_MS == 6000);
  return 0;
}
''', encoding='utf-8')
    subprocess.run(['C:/Users/ZhaoZ/.vscode/mingw64/bin/gcc.exe', '-std=c99', '-Wall', '-Wextra', '-Werror',
                    '-finput-charset=UTF-8', 'check.c', '-o', 'check.exe'], cwd=tmp, check=True)
    subprocess.run([str(tmp / 'check.exe')], cwd=tmp, check=True)
report = {'checked_frames': checked, 'resources': len(table['resources']), 'states': len(states),
          'rgb565_bytes': sum(r['rgb565_bytes'] for r in table['resources']),
          'errors': errors, 'c_header_compiles_and_runs': True}
(OUT / 'export_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False), flush=True)
sys.exit(bool(errors))
