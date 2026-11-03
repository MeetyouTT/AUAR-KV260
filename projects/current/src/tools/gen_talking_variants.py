# -*- coding: utf-8 -*-
"""说话素材**变体**批量生成（用户 2026-10-05 反馈："说话不够自然 → 那就多生成一些素材"）。

**零侵入**：本脚本**不改** ComfyUI 目录下的任何文件 ——
`ComfyUI\\tools\\run_doll_green.py` 是 12 态共用的生成脚本（属共享资产），
本脚本只通过 HTTP API 提交**新 tag**，与之保持
「同一模型 / 同一首帧 / 同一 COMMON_TAIL / 同一 seed 基准」，
仅替换结尾的**动作描述**⇒ 跨素材风格一致（项目硬要求，见 docs 多篇「跨素材一致性核验」）。

产物：`ComfyUI\\output\\DOLLGV2_<TAG>_*.png`（**新 tag ⇒ 不会覆盖任何现有帧**；
      ingest 侧用正则 `^DOLLGV2_<TAG>_\\d+_?\\.png$` 精确匹配，`SPEAKING_NEUTRAL` 不会误吃 `SPEAKING_NEUTRAL_B`）。
      → 随后跑 `tools\\aura_ingest_v2.py`（其 MAP 已加对应条目）抠像入库。

前置：ComfyUI 已在 `127.0.0.1:8188` 运行（本脚本只走 HTTP，不依赖 cwd / 不读本地文件）。

用法（ComfyUI 便携 Python）：
    "<ComfyUI>\\python_standalone\\python.exe" -s <aura>\\tools\\gen_talking_variants.py --only SPEAKING_NEUTRAL_B
    "<ComfyUI>\\python_standalone\\python.exe" -s <aura>\\tools\\gen_talking_variants.py
日志：`%TEMP%\\dollgreen_variants.txt`
"""
import json
import os
import sys
import time
import typing
import urllib.error
import urllib.request

HOST = 'http://127.0.0.1:8188'
LOG = os.path.join(os.environ['TEMP'], 'dollgreen_variants.txt')

# ↓↓↓ 与 run_doll_green.py **逐字一致**（这里改了，那边也必须同步，否则跨素材风格会漂）↓↓↓
UNET = 'minimax_h3_fl2va_pruned_int8_convrot.safetensors'
CLIP = 'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors'
VAE = 'minimax_h3_video_vae_int8_convrot.safetensors'
TURBO = 'minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors'
FIRST = 'doll_green_9x16.png'
W, H = 864, 1536
LEN, STEPS = 39, 8
SAMPLER, SCHED = 'res_multistep', 'simple'
PREFIX = 'DOLLGV2'
SEED_BASE = 420000
# 变体专用 seed 段（400+）：与 run_doll_green.py 的 SEED_MAP（11~22）**不重叠** ⇒ 可复现且不撞
SEED_BASE_OFFSET = 400

BG = ('solid flat chroma key green screen background, the exact same pure green '
      'as in the first frame, evenly lit, absolutely uniform green, no shadow '
      'cast on the background, no gradient on the background, no vignette on '
      'the background, nothing else in frame, ')

# 循环类素材：末帧必须回到首帧姿态（否则无限循环会"跳一下"）
LOOP_LINE = ('the pose at the last frame returns exactly to the pose of the '
             'first frame so the clip loops seamlessly, ')

COMMON_TAIL = ('same girl, same face, same outfit, full body standing pose, '
               'identical framing and identical scale as the first frame, ' + BG +
               'static locked camera, unchanged flat lighting, ' + LOOP_LINE +
               'all movement is calm '
               'but clearly readable with gentle easing at the start and the end, '
               'absolutely consistent color and white balance in every frame, '
               'identical exposure and tone throughout, clean anime; '
               'no visual effects, no glow, no bloom, no particles, '
               'no sparkles, no lens flare, no light rays, no magic, no overlays, '
               'no color shift, no hue change, no saturation change, no tint, '
               'no vignette, no film grain, no motion blur, no distortion, '
               'no whale tail, no tail, no extra objects, no background change, '
               'no scene change, no camera movement, no text, '
               'never walking, never turning around, never leaving the frame')

# ============================ 变体定义（本次新增） ============================
# 设计原则：**只换"手/头的动作"，其余句式沿用主素材**
#   ⇒ 既保证与主素材同代（同一模型 / 同一尾缀），又能让轮换时"看得出变化"。
# 与现存主素材的差异点：
#   SPEAKING_NEUTRAL_B  双手胸前小幅配合（主素材 `talking_neutral` 是**单手腰际**）
#   SPEAKING_NEUTRAL_C  单手侧向小幅 + 轻微转头（主素材**头部几乎不动**）
#   SPEAKING_B          两手交替强调（主素材 `talking_normal` 是**单手两次**）
VARIANTS: typing.Dict[str, str] = {
    'SPEAKING_NEUTRAL_B': (
        'talking calmly and evenly in a neutral tone, the mouth opens and '
        'closes with clearly readable but moderate lip movements of about 10 to '
        '14 syllables across the clip, the head stays calm with only a tiny '
        'sway of about 3 degrees, the face stays neutral and friendly without a '
        'big smile, both hands rise together to just below the chest and make '
        'two small matching emphasis movements of about 6 percent of the body '
        'height around the middle of the clip, then both hands come back down '
        'to the same place at the sides, two natural blinks, '),
    'SPEAKING_NEUTRAL_C': (
        'talking calmly and evenly in a neutral tone, the mouth opens and '
        'closes with clearly readable but moderate lip movements of about 10 to '
        '14 syllables across the clip, the head turns slightly to one side by '
        'about 6 degrees and comes back again while the eyes stay on the '
        'viewer, the face stays neutral and friendly, the right hand makes two '
        'small sideways emphasis movements near the waist of about 5 percent of '
        'the body height and returns to the same place, the left hand stays '
        'relaxed at the side, one slow blink and one natural blink, '),
    'SPEAKING_B': (
        'talking cheerfully and clearly, the mouth opens and closes with '
        'clearly readable lip movements of about 12 to 16 syllables across the '
        'clip, the right hand rises to chest height and makes one gentle '
        'emphasis gesture while the left hand rises a moment later and makes a '
        'smaller answering gesture, the two hands alternate twice and come back '
        'to the same place, the left shoulder lifts slightly once, the head '
        'stays almost still with only a tiny sway of a few degrees, the face '
        'starts calm, brightens into a soft warm smile around the middle of the '
        'clip, and returns to the same calm face at the end, two slow natural '
        'blinks, '),
}


def wf(tag: str, prompt: str, seed: int, length: int = LEN) -> typing.Dict:
    """与 `run_doll_green.py` 的 `wf()` **逐字一致**（节点编号 / 参数**不得改动**）。"""
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": CLIP, "type": "minimax"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0], "lora_name": TURBO,
                         "strength_model": 1.0}},
        "5": {"class_type": "LoadImage", "inputs": {"image": FIRST}},
        "7": {"class_type": "MiniMaxH3ImageToVideo",
              "inputs": {"clip": ["2", 0], "vae": ["3", 0], "prompt": prompt,
                         "width": W, "height": H, "length": length,
                         "first_frame": ["5", 0], "last_frame": ["5", 0]}},
        "8": {"class_type": "BasicScheduler",
              "inputs": {"model": ["4", 0], "scheduler": SCHED,
                         "steps": STEPS, "denoise": 1.0}},
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": SAMPLER}},
        "10": {"class_type": "BasicGuider",
               "inputs": {"model": ["4", 0], "conditioning": ["7", 0]}},
        "11": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "12": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["11", 0], "guider": ["10", 0],
                          "sampler": ["9", 0], "sigmas": ["8", 0],
                          "latent_image": ["7", 1]}},
        "13": {"class_type": "VAEDecode",
               "inputs": {"samples": ["12", 0], "vae": ["3", 0]}},
        "14": {"class_type": "SaveImage",
               "inputs": {"images": ["13", 0],
                          "filename_prefix": "%s_%s" % (PREFIX, tag)}},
    }


def submit(prompt_graph: typing.Dict) -> str:
    data = json.dumps({"prompt": prompt_graph, "client_id": "cline-dollvariants"}
                      ).encode("utf-8")
    req = urllib.request.Request(HOST + "/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))["prompt_id"]


def wait_done(pid: str, timeout: int = 5400) -> typing.Optional[str]:
    """轮询直到出图 / 出错 / 超时；返回 `'<n> frames'` / `'__ERROR__'` / None。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(HOST + "/history/" + pid, timeout=20) as r:
                h = json.loads(r.read().decode("utf-8"))
        except Exception:
            h = {}
        if pid in h:
            st = h[pid].get('status', {})
            if st.get('status_str') == 'error':
                return '__ERROR__'
            n = 0
            for _n, o in h[pid].get("outputs", {}).items():
                n += len(o.get("images", []))
            return '%d frames' % n
        time.sleep(5)
    return None


def online() -> bool:
    """ComfyUI 是否在线 —— **先探再跑**，避免排了队才发现服务没起来。"""
    try:
        with urllib.request.urlopen(HOST + "/system_stats", timeout=8) as r:
            json.loads(r.read().decode("utf-8"))
        return True
    except Exception:
        return False


def _flush(lines: typing.List[str]) -> None:
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


def main() -> int:
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    todo = [t for t in VARIANTS if not only or t in only]
    L = ["== 说话素材变体生成  首帧 %s  %dx%d  %d 帧  steps=%d  前缀=%s =="
         % (FIRST, W, H, LEN, STEPS, PREFIX),
         "   待跑: %s" % (", ".join(todo) if todo else "(无)"), ""]
    if not todo:
        L.append("未匹配到 tag（可用: %s）" % ", ".join(VARIANTS))
        _flush(L)
        return 2
    if not online():
        L.append("FAIL ComfyUI 未在线（%s）—— 先启动 ComfyUI，再重跑本脚本" % HOST)
        _flush(L)
        return 1
    fail = []
    for tag in todo:
        t0 = time.time()
        try:
            pid = submit(wf(tag, VARIANTS[tag] + COMMON_TAIL,
                            SEED_BASE + SEED_BASE_OFFSET + list(VARIANTS).index(tag)))
        except urllib.error.HTTPError as e:
            L.append('%-20s 提交失败 %s'
                     % (tag, e.read().decode('utf-8', 'ignore')[:400]))
            _flush(L)
            fail.append(tag)
            continue
        L.append('%-20s %d 帧  生成中... prompt_id=%s' % (tag, LEN, pid))
        _flush(L)
        res = wait_done(pid)
        d = time.time() - t0
        L[-1] = '%-20s -> %-12s %6.0fs (%.1f 分)' % (tag, res, d, d / 60.0)
        _flush(L)
        if res is None or res == '__ERROR__':
            fail.append(tag)
    L.append('')
    L.append('FAILED: %s' % (','.join(fail) if fail else 'none'))
    L.append('下一步: 跑 tools\\aura_ingest_v2.py 把新 tag 抠像入库（MAP 已加条目）')
    _flush(L)
    print('日志: %s' % LOG)
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())

