from common import *
f=ROOT/'board/scripts/stage.py'
s=f.read_text(encoding='utf8')
mark='def main():\n'
helper='''def copy_image_inputs(image_root, expected, copy_to_stage):
    image_root = image_root.resolve(strict=True)
    if not image_root.is_dir() or image_root == Path(image_root.anchor):
        raise ValueError('--image-root must refer to a separate, mounted image or a copy of its rootfs')
    matched = 0
    for destination, digest in sorted(expected.items()):
        candidate = image_root / destination.lstrip('/')
        try:
            source = candidate.resolve(strict=True)
        except (FileNotFoundError, RuntimeError):
            print('image input missing:', destination)
            continue
        if image_root not in source.parents or not source.is_file():
            print('image input outside root or not a regular file:', destination)
            continue
        if source.stat().st_size > 8 * 1024 * 1024 or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            print('image input has a different SHA-256:', destination)
            continue
        copy_to_stage(source, destination)
        matched += 1
    print('Original-image files matched: {}/{}'.format(matched, len(expected)))
    return matched

'''
if helper not in s:
    assert mark in s;s=s.replace(mark,helper+mark)
    mark="    a=ap.parse_args(); out=a.out.resolve()"
    assert mark in s;s=s.replace(mark,"    ap.add_argument('--image-root',type=Path,help='optional, separately mounted original rootfs; copy only recorded public files with matching SHA-256')\n"+mark)
    mark="    print('PASS: offline rootfs staging:',out)"
    assert mark in s;s=s.replace(mark,'''    gui=read('src/software/config/board_avatar_gtk.json')
    formal=dest(gui['formal_stage_root'])
    if not all((formal / f).is_file() for f in ('index.html', 'player.js')):
        raise RuntimeError('Formal stage files missing from offline tree')
    if a.image_root:
        copy_image_inputs(a.image_root, read('board/config/image_inputs.json')['files'], cp)
'''+mark)
    f.write_bytes(s.encode('utf8'))
f=ROOT/'board/readme.md'
s=f.read_text(encoding='utf8')
title='## 从原卡镜像补全固定文件'
if title not in s:
    s+='\n'+title+'''

归档已按历史板端哈希还原正式舞台的 index.html、player.js、字体和选定音色资源。另有 7 个历史相机校验项在 E 盘和 Ubuntu 归档中只有哈希，逐项记录在 board/config/original_camera_inputs.json。历史 V2 与现役原生算子的 C++ 源、原始 AArch64 目标文件和链接记录分别在 src/camera/native_v2 与 src/camera/native_operator；本次未在匹配的板端 SDK 上重链接出两个原 SHA 的共享库。

如果保有原卡的只读挂载副本，可把下面第三个参数传给暂存工具。它只检查 board/config/image_inputs.json 指定的 12 条公开路径，包括上述 7 项、现役算子共享库，以及固定提示音 3 个 WAV 和其清单。仅复制 SHA 完全匹配的文件，逐项列出缺失或版本不同的文件，最后打印匹配数量。无需网络或连接板卡。

~~~sh
python3 -B board/scripts/stage.py --out "$HOME/auar-rootfs-02" --audio ../auar_board_audio_dependencies.zip --image-root /mnt/kv260-original
~~~

若现有归档只用于审阅或仿真，默认命令即可。没有原镜像时，生成三条固定提示音和重编译共享库得到的是新的部署版本，应走新的绑定和实机验收。
'''
    f.write_bytes(s.encode())
f=ROOT/'report/release_status.md'
s=f.read_text(encoding='utf8')
if 'board/config/image_inputs.json' not in s:
    s+='\n原机专属文件的迁移入口见 board/readme.md。原卡有 7 项历史相机校验输入、1 个现役原生共享库以及 3 段固定系统提示音和清单只在归档中留有哈希、源码或生成步骤。board/config/image_inputs.json 列出精确路径和 SHA，暂存工具的 --image-root 可从只读挂载副本逐项核对补入。\n'
    f.write_bytes(s.encode())
print('stage extension ready')