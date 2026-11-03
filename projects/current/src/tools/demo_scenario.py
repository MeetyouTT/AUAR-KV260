# -*- coding: utf-8 -*-
"""v2 玩偶状态系统 · 模拟剧本演示（纯逻辑，不依赖 Qt）。

一次跑完两件事：

1. 用**真实 `RuntimeFSM`** 走一遍"模拟一次完整拜访"的剧本事件序列，记录演出
   时间线：事件 → 状态迁移 → 素材名 → 帧数 → 时长 → loop/burst → 是否走了回退链。
   状态机本身是逐字调用生产代码，所以这份时间线就是**真机上会发生的事**；
2. 从 `assets/avatar/` 的**真实帧序列**合成 GIF，配一张 HTML 页面，
   浏览器直接双击就能看到 14 态的最终效果（含 burst 一次性动作）。

用法（ComfyUI 便携 Python；本机无系统 Python）：
    "<PY>" -s tools\\demo_scenario.py
产物：
    docs\\demo_v2\\index.html   剧本时间线 + 各状态动图
    docs\\demo_v2\\*.gif        每态一张（缩略图，页面内联引用）
"""
import html
import json
import os
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from board.interaction import avatar_assets            # noqa: E402
from board.interaction import avatar_timing            # noqa: E402
from board.runtime.event_bus import EventEnvelope      # noqa: E402
from board.runtime.events import EventType             # noqa: E402
from board.runtime.fsm import RuntimeFSM               # noqa: E402

OUTDIR = ROOT / "docs" / "demo_v2"
GIF_W = 160        # GIF 缩略宽度（控制体积；原素材 464x480）
GIF_STRIDE = 2     # 每 2 帧取 1 帧进 GIF，体积减半、观感够用

# --------------------------------------------------------------------------- #
# 模拟剧本：一次完整拜访（刻意覆盖全部 14 态）
#   (旁白, 事件类型, payload)；None 表示"仅记录当前状态、不发事件"
# --------------------------------------------------------------------------- #
SCENARIO = [
    ("开机无人，空闲", None, {}),
    ("来访者进入，有人了", EventType.SCENE_PERSON_ENTER, {}),
    ("唤醒词命中，先给个反应", EventType.AUDIO_KWS_DETECTED, {}),
    ("检测到句尾，开始聆听", EventType.AUDIO_VAD_END, {}),
    ("聆听结束，进入思考", EventType.AUDIO_VAD_END, {}),
    ("收到回复 emotion=neutral，中性播报", EventType.DIALOGUE_RESPONSE_RECEIVED,
     {"emotion": "neutral"}),
    ("播报播放完毕", EventType.AUDIO_PLAYBACK_STOP, {}),
    ("用户按实体键（不播唤醒反应，直接聆听）", EventType.BOARD_KEY_PRESSED, {}),
    ("检测到句尾，开始聆听", EventType.AUDIO_VAD_END, {}),
    ("聆听结束，进入思考", EventType.AUDIO_VAD_END, {}),
    ("收到回复 emotion=happy，情绪高涨播报", EventType.DIALOGUE_RESPONSE_RECEIVED,
     {"emotion": "happy"}),
    ("播报播放完毕", EventType.AUDIO_PLAYBACK_STOP, {}),
    ("换个人进来", EventType.SCENE_PERSON_ENTER, {}),
    ("唤醒词命中，再给个反应", EventType.AUDIO_KWS_DETECTED, {}),
    ("检测到句尾，开始聆听", EventType.AUDIO_VAD_END, {}),
    ("聆听结束，进入思考", EventType.AUDIO_VAD_END, {}),
    ("收到回复 emotion=sad，低落播报", EventType.DIALOGUE_RESPONSE_RECEIVED,
     {"emotion": "sad"}),
    ("用户按键取消（瞬时态，按否有人在自动回迁）",
     EventType.AUDIO_CANCEL_REQUESTED, {}),
    ("用户按实体键，重新聆听", EventType.BOARD_KEY_PRESSED, {}),
    ("检测到句尾，开始聆听", EventType.AUDIO_VAD_END, {}),
    ("聆听结束，进入思考", EventType.AUDIO_VAD_END, {}),
    ("命令执行成功，avatar_action=ack_nod 点头确认",
     EventType.DIALOGUE_RESPONSE_RECEIVED, {"avatar_action": "ack_nod"}),
    ("点头播完", EventType.AUDIO_PLAYBACK_STOP, {}),
    ("用户请求关灯，玩偶拒绝", EventType.BOARD_KEY_PRESSED, {}),
    ("检测到句尾，开始聆听", EventType.AUDIO_VAD_END, {}),
    ("聆听结束，进入思考", EventType.AUDIO_VAD_END, {}),
    ("avatar_action=deny_shake 摇头拒绝（P1-1 新素材）",
     EventType.DIALOGUE_RESPONSE_RECEIVED, {"avatar_action": "deny_shake",
                                            "emotion": "neutral"}),
    ("摇头播完", EventType.AUDIO_PLAYBACK_STOP, {}),
    ("再来一个人", EventType.SCENE_PERSON_ENTER, {}),
    ("唤醒词命中", EventType.AUDIO_KWS_DETECTED, {}),
    ("检测到句尾，开始聆听", EventType.AUDIO_VAD_END, {}),
    ("聆听结束，进入思考", EventType.AUDIO_VAD_END, {}),
    ("回复没听懂，avatar_action=emo_puzzled 困惑",
     EventType.DIALOGUE_RESPONSE_RECEIVED, {"avatar_action": "emo_puzzled"}),
    ("困惑动画播完", EventType.AUDIO_PLAYBACK_STOP, {}),
    ("摄像头掉了（系统态，不该有情绪表情）", EventType.CAMERA_LOST, {}),
    ("摄像头恢复", EventType.CAMERA_RECOVERED, {}),
    ("局域网断链，切本地模式", EventType.DIALOGUE_NETWORK_LOST, {}),
    ("局域网恢复", EventType.DIALOGUE_NETWORK_RESTORED, {}),
    ("后台 worker 崩溃", EventType.SYSTEM_WORKER_CRASH, {}),
    ("健康检查通过，恢复", EventType.SYSTEM_HEALTH_OK, {}),
    ("最后一次：唤醒 → 聆听 → 思考 → 回复是 surprise 动作",
     EventType.SCENE_PERSON_ENTER, {}),
    ("唤醒词命中", EventType.AUDIO_KWS_DETECTED, {}),
    ("检测到句尾，开始聆听", EventType.AUDIO_VAD_END, {}),
    ("聆听结束，进入思考", EventType.AUDIO_VAD_END, {}),
    ("avatar_action=emo_surprised，惊讶反应", EventType.DIALOGUE_RESPONSE_RECEIVED,
     {"avatar_action": "emo_surprised"}),
]


# --------------------------------------------------------------------------- #
# 1) 状态 → 素材解析（走真实回退链）
# --------------------------------------------------------------------------- #
def frames_of(state_name):
    """状态 → 实际可用素材（沿 avatar_assets.fallback_chain）+ 帧数/fps/时长。

    返回 None 表示回退链全空（真机上会退到 B2V 矢量主体）。
    """
    chain = avatar_assets.fallback_chain(state_name)
    used_dir = avatar_assets.frames_dir(state_name)
    if used_dir is None:
        return None
    asset = used_dir.name
    frames = avatar_assets.list_frames(used_dir)
    fps = avatar_assets.frames_fps(used_dir)
    meta = avatar_assets.read_meta(used_dir)
    return {
        "asset": asset,
        "dir": used_dir,
        "frames": len(frames),
        "fps": fps,
        "seconds": (len(frames) / fps) if fps else 0.0,
        "burst": state_name in avatar_assets.BURST_STATES,
        "fallback": asset != avatar_assets.asset_name(state_name),
        "chain": chain,
        "size": tuple(meta.get("size") or (0, 0)),
    }


def run_scenario():
    """用**真实 RuntimeFSM** 走剧本，返回 (fsm, 时间线行表)。"""
    fsm = RuntimeFSM(publish_state_changes=False)
    rows = []
    for say, etype, payload in SCENARIO:
        rejected = False
        change = None
        if etype is not None:
            before = fsm.rejected_count
            change = fsm.handle_event(EventEnvelope(
                event_type=etype, source="demo_scenario",
                created_at_ms=0, payload=payload))
            # 用 rejected_count 的增量判断"这一步被状态机拒绝"（change is None
            # 也可能是自环，两者语义不同：自环=合法但无变化，拒绝=非法转换）。
            rejected = fsm.rejected_count > before
        state = fsm.state.label
        rows.append({"say": say, "event": etype, "payload": payload,
                     "state": state, "info": frames_of(state),
                     "change": change, "rejected": rejected})
    return fsm, rows


# --------------------------------------------------------------------------- #
# 2) 素材帧 → GIF（深底合成，避免 GIF 1 位透明的毛边）
# --------------------------------------------------------------------------- #
BG = (43, 47, 54, 255)     # 与桌宠深色主题接近，便于肉眼判断边缘


def make_gif(state_name, info):
    """把该状态实际使用的素材帧合成 GIF，返回 (文件名, 单帧时长 ms, 帧数)。"""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    files = avatar_assets.list_frames(info["dir"])[::GIF_STRIDE]
    if not files:
        return None, 0, 0
    duration = max(20, int(round(1000.0 / info["fps"] * GIF_STRIDE)))
    out = OUTDIR / ("%s.gif" % state_name.lower())
    pil = []
    for p in files:
        im = Image.open(p).convert("RGBA")
        w, h = im.size
        nh = max(1, int(round(h * GIF_W / float(w))))
        im = im.resize((GIF_W, nh), Image.LANCZOS)
        canvas = Image.new("RGBA", (GIF_W, nh), BG)
        canvas.alpha_composite(im)
        pil.append(canvas.convert("P", palette=Image.ADAPTIVE, colors=128))
    pil[0].save(out, save_all=True, append_images=pil[1:],
                duration=duration, loop=0, optimize=True)
    return out.name, duration, len(pil)


# --------------------------------------------------------------------------- #
# 3) HTML 页面（时间线 + 各状态动图）
# --------------------------------------------------------------------------- #
CSS = """
body{background:#1b1e24;color:#e6e6e6;font-family:'Microsoft YaHei',sans-serif;margin:24px}
h1{font-size:20px;margin:0 0 4px} .sub{color:#8b96a3;font-size:12px;margin-bottom:18px}
h2{font-size:16px;margin:26px 0 10px;border-left:4px solid #4aa08a;padding-left:8px}
table{border-collapse:collapse;font-size:13px;width:100%}
th,td{border:1px solid #333a45;padding:4px 8px;text-align:left;vertical-align:top}
th{background:#252a32;position:sticky;top:0}
tr:nth-child(even) td{background:#20242b}
.burst{color:#ffcf5c;font-weight:bold} .loop{color:#7fd18b}
.fb{color:#ff8a7a} .n{color:#6f7a87}
.grid{display:flex;flex-wrap:wrap;gap:14px}
.card{background:#232830;border:1px solid #333a45;border-radius:8px;padding:10px;width:182px}
.card img{display:block;margin:0 auto 6px;background:#2b2f36;border-radius:6px}
.card .t{text-align:center;font-weight:bold;font-size:13px;margin-bottom:6px}
.k{color:#93a0ad;font-size:12px;line-height:1.6}
.k b{color:#dfe6ee} .warn{color:#ffcf5c}
"""


def esc(v):
    return html.escape("" if v is None else str(v))


def build_html(rows, fsm, gifs):
    """产出 docs/demo_v2/index.html（时间线 + 动图 + 统计）。"""
    order = list(dict.fromkeys(r["state"] for r in rows))
    all_states = [s.value for s in fsm.state.__class__]
    # 覆盖统计必须算上**瞬时态**：CANCELLED 进入后会被自动回迁，剧本行里看不到它，
    # 但它确实发生过 → 直接查状态机历史（含 auto 迁移），而不是只看剧本行的快照。
    covered = sorted({h["to"] for h in fsm.history(limit=10 ** 6)} | {"IDLE"},
                     key=all_states.index)
    missing = [s for s in all_states if s not in covered]
    fallbacks = [r for r in rows if r["info"] and r["info"]["fallback"]]
    bursts = [r for r in rows if r["info"] and r["info"]["burst"]]

    parts = ["<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
             "<title>v2 玩偶状态系统 · 模拟剧本演示</title>",
             "<style>%s</style></head><body>" % CSS,
             "<h1>v2 玩偶状态系统 · 模拟剧本演示</h1>",
             "<div class='sub'>状态机为生产代码逐字调用（RuntimeFSM + "
             "avatar_assets）；动图来自 assets/avatar 的真实帧序列。"
             "素材规格 464x480 / 24fps。</div>"]
    parts.append("<h2>一、剧本时间线（%d 步）</h2>" % len(rows))
    parts.append("<table><tr><th>#</th><th>旁白</th><th>事件</th><th>payload</th>"
                 "<th>状态</th><th>素材</th><th>时长</th><th>播放语义</th></tr>")
    for i, r in enumerate(rows, 1):
        info = r["info"]
        if info is None:
            asset, secs, sem = "<span class='fb'>无素材→B2V矢量</span>", "-", "-"
        else:
            fb = " <span class='fb'>[回退]</span>" if info["fallback"] else ""
            asset = "%s%s" % (info["asset"], fb)
            secs = "%.2fs / %d帧" % (info["seconds"], info["frames"])
            sem = ("<span class='burst'>burst 一次性</span>" if info["burst"]
                   else "<span class='loop'>loop 循环</span>")
        ev = r["event"] or "<span class='n'>（仅记录初始态）</span>"
        if r.get("rejected"):
            mark = "<span class='fb'>被拒</span>"
        elif r["event"] and r["change"] is None:
            mark = "<span class='n'>无变化(自环)</span>"
        elif r["event"]:
            mark = "<span class='loop'>迁移</span>"
        else:
            mark = ""
        pl = esc(json.dumps(r["payload"], ensure_ascii=False)) if r["payload"] else "<span class='n'>-</span>"
        parts.append("<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td><b>%s</b> %s</td>"
                     "<td>%s</td><td>%s</td><td>%s</td></tr>"
                     % (i, esc(r["say"]), esc(ev), pl, esc(r["state"]), mark,
                        asset, secs, sem))
    parts.append("</table>")

    parts.append("<h2>二、各状态最终效果（按剧本出现顺序）</h2><div class='grid'>")
    for s in order:
        info = frames_of(s)
        gif = gifs.get(s)
        if not info or not gif or not gif[0]:
            parts.append("<div class='card'><div class='t'>%s</div>"
                         "<div class='k'>无素材（真机退 B2V 矢量主体）</div></div>" % esc(s))
            continue
        tag = ("<span class='burst'>burst 一次性</span>" if info["burst"]
               else "<span class='loop'>loop 循环</span>")
        fb = ("<div class='k warn'>⚠ 走了回退链：%s</div>" % esc(" → ".join(info["chain"]))
              if info["fallback"] else "")
        parts.append(
            "<div class='card'><div class='t'>%s</div>"
            "<img src='%s' width='%d' alt='%s'>"
            "<div class='k'>素材 <b>%s</b> · %dx%d<br>"
            "<b>%d</b> 帧 @<b>%.1f</b>fps ≈ %.2fs<br>%s</div>%s</div>"
            % (esc(s), esc(gif[0]), GIF_W, esc(s), esc(info["asset"]),
               info["size"][0], info["size"][1], info["frames"], info["fps"],
               info["seconds"], tag, fb))
    parts.append("</div>")

    real = [r for r in rows if r["info"]]
    total = sum(r["info"]["seconds"] for r in real)
    parts.append("<h2>三、统计</h2><table>")
    parts.append("<tr><th>项</th><th>值</th></tr>")
    parts.append("<tr><td>剧本步数 / 状态覆盖</td><td>%d 步，覆盖 <b>%d/%d</b> 态</td></tr>"
                 % (len(rows), len(covered), len(all_states)))
    if missing:
        parts.append("<tr><td>未覆盖状态</td><td class='warn'>%s</td></tr>"
                     % esc(", ".join(missing)))
    parts.append("<tr><td>素材总时长（每次状态重现累加）</td><td><b>%.2f s</b></td></tr>" % total)
    parts.append("<tr><td>一次性动作（burst）出现</td><td><b>%d</b> 次 · %s</td></tr>"
                 % (len(bursts), esc(", ".join(sorted({r["state"] for r in bursts})))))
    parts.append("<tr><td>走回退链（素材缺失）</td><td><b>%d</b> 次</td></tr>" % len(fallbacks))
    parts.append("<tr><td>状态机拒绝的非法转换</td><td><b>%d</b> 次</td></tr>" % fsm.rejected_count)
    parts.append("<tr><td>全素材尺寸 / 帧率唯一性</td><td>464x480 · 24fps（见 verify_v2_amp 报告）</td></tr>")
    parts.append("</table></body></html>")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# 4-b) P0-2 长句去重复：按**播放层时间基**出片（方案 §4.1 P0-2 / §6.1）
#
# 复核结论（.cline-handover.md 第 28 条）：上面的 make_gif 是**逐帧直出**
# （`list_frames(dir)[::GIF_STRIDE]`），与播放层时间基无关 → 改 P0-2 前后出片
# 一模一样，"出片 + 自相关"根本测不到相位/变速。本节按
# `avatar_timing.frame_time + frame_index`（与 qt_widgets 播放层同一份口径）
# 逐帧采样出片，才能看见「入场相位随机化 + 按句长变速」的真实效果。
# --------------------------------------------------------------------------- #
P02_OUTDIR = ROOT / "docs" / "demo_p02"
P02_OUT_FPS = 24.0          # GIF 帧率 = 素材帧率（这样"改前"的精确周期恰好 = 素材时长 1.625s）
P02_SECONDS = 6.0           # 每段演示时长（≈3.7 个素材循环，"循环感"看得清）
P02_ENTRIES = 16            # "多次重新入场"次数（看入场首帧是否分散）
P02_STATE = "SPEAKING_NEUTRAL"   # 演示素材：中性播报（loop，命中率最高的档）

# 三档句长（方案 §6.1：≈10 字 / 30 字 / 80 字）
P02_TEXTS = (
    ("A 短句（10 字）", "好的，我帮你把灯打开。"),
    ("B 中句（30 字）", "我看到画面左侧有一位来访者，他正站在门口，手里拿着一封信。"),
    ("C 长句（80 字）", "我看到画面左侧有一位来访者，他先在门口停了一会儿，然后向房间里走了两步，"
                        "又把手里那封信举起来晃了晃，像是在确认我有没有注意到他；如果你愿意，"
                        "我也可以先替你打个招呼，再问问他今天来找谁。"),
)


def make_gif_from_indices(info, indices, out_path, out_fps=P02_OUT_FPS):
    """按帧索引序列合成 GIF —— **真正经过播放层时间基**（区别于逐帧直出）。"""
    files = avatar_assets.list_frames(info["dir"])
    if not files or not indices:
        return None
    duration = max(20, int(round(1000.0 / out_fps)))
    pil = []
    for idx in indices:
        im = Image.open(files[max(0, min(int(idx), len(files) - 1))]).convert("RGBA")
        w, h = im.size
        nh = max(1, int(round(h * GIF_W / float(w))))
        im = im.resize((GIF_W, nh), Image.LANCZOS)
        canvas = Image.new("RGBA", (GIF_W, nh), BG)
        canvas.alpha_composite(im)
        pil.append(canvas.convert("P", palette=Image.ADAPTIVE, colors=128))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pil[0].save(str(out_path), save_all=True, append_images=pil[1:],
                duration=duration, loop=0, optimize=True)
    return out_path.name


def p02_one(label, text, info, before_gif, period_before):
    """单个句长档：出「改后」GIF + 周期指标（「改前」由 p02_run 统一出一份）。"""
    fps, n, burst, seconds = info["fps"], info["frames"], info["burst"], info["seconds"]
    speed = avatar_timing.speed_for_text(text)
    phase = avatar_timing.random_phase(seconds)
    after = avatar_timing.sample_frame_indices(n, fps, burst, P02_SECONDS,
                                               phase=phase, speed=speed, out_fps=P02_OUT_FPS)
    tag = label.split()[0]
    per_after = avatar_timing.exact_period(after)
    return {
        "label": label, "text": text, "chars": len(text),
        "est_seconds": avatar_timing.estimate_seconds(text), "speed": speed,
        "phase": phase,
        "gif_before": before_gif,
        "gif_after": make_gif_from_indices(info, after, P02_OUTDIR / ("%s_after.gif" % tag)),
        "period_before": period_before, "period_after": per_after,
        "cycle_before": (period_before / P02_OUT_FPS) if period_before else None,
        "cycle_after": (per_after / P02_OUT_FPS) if per_after else None,
    }


def p02_phase_spread(info, entries=P02_ENTRIES, at_seconds=0.3):
    """模拟重复入场 → 同一时刻的帧索引集合（改前恒 1 种 / 改后分散）。"""
    fps, n, burst, seconds = info["fps"], info["frames"], info["burst"], info["seconds"]
    fixed, spread = set(), set()
    for _ in range(entries):
        fixed.add(avatar_timing.frame_index(at_seconds, n, fps, burst))
        ph = avatar_timing.random_phase(seconds)
        t = avatar_timing.frame_time(at_seconds, burst=burst, phase=ph)
        spread.add(avatar_timing.frame_index(t, n, fps, burst))
    return sorted(fixed), sorted(spread)


def build_p02_html(rows, info, fixed, spread):
    """产出 docs/demo_p02/index.html：改前/改后动图对比 + 指标。"""
    parts = ["<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
             "<title>P0-2 长句去重复 · 改前/改后对比</title>",
             "<style>%s</style></head><body>" % CSS,
             "<h1>P0-2 长句去重复 · 改前 / 改后对比</h1>",
             "<div class='sub'>取帧口径与播放层同一份：<b>board/interaction/avatar_timing.py</b>"
             "（qt_widgets 播放层调用它）。下方 GIF 由该口径<b>逐帧采样</b>合成，不是逐帧直出。"
             "素材 %s · %d 帧 @%.2ffps · %.3fs，每段演示 %.0fs。</div>"
             % (esc(info["asset"]), info["frames"], info["fps"], info["seconds"],
                P02_SECONDS)]
    parts.append("<h2>一、改的是什么</h2>")
    parts.append("<table><tr><th>手段</th><th>改前</th><th>改后</th></tr>"
                 "<tr><td>入场相位</td><td>进入状态必从第 0 帧起（相位恒 0）"
                 "→ 每次说长句都是同一段入场动作</td>"
                 "<td>进入 loop 状态抽 <b>phase ∈ [0, %.3fs)</b>，每次入场都不同</td></tr>"
                 "<tr><td>播放速度</td><td>恒 1.0 → 循环节恒 = 素材时长 %.3fs</td>"
                 "<td>按回复字数估句长 → <b>speed ∈ [0.85, 1.15]</b></td></tr>"
                 "<tr><td>burst 一次性动作</td>"
                 "<td colspan='2'>不受影响：不加相位、不变速，仍从第 0 帧起播（AWAKE / ACK_NOD）</td></tr>"
                 "</table>" % (info["seconds"], info["seconds"]))
    parts.append("<h2>二、三档句长：改前 / 改后动图</h2>")
    for r in rows:
        parts.append("<h3>%s</h3><div class='sub'>%s<br>预计口播 %.1fs · speed=%.3f · "
                     "入场相位 %.3fs · 精确周期：改前 %s → 改后 %s</div>"
                     % (esc(r["label"]), esc(r["text"]), r["est_seconds"], r["speed"],
                        r["phase"],
                        ("%.3fs" % r["cycle_before"]) if r["cycle_before"] else "-",
                        ("%.3fs" % r["cycle_after"]) if r["cycle_after"] else "无（已打散）"))
        parts.append("<div class='grid'>")
        parts.append("<div class='card'><div class='t'>改前（共用：相位 0 / 速度 1.0）</div>"
                     "<img src='%s' width='160' height='166'></div>" % esc(r["gif_before"]))
        parts.append("<div class='card'><div class='t'>改后（随机相位 / 变速）</div>"
                     "<img src='%s' width='160' height='166'></div>" % esc(r["gif_after"]))
        parts.append("</div>")
    parts.append("<h2>三、指标（可复核）</h2><table>")
    parts.append("<tr><th>档位</th><th>字数</th><th>预计句长</th><th>speed</th>"
                 "<th>入场相位</th><th>改前精确周期</th><th>改后精确周期</th></tr>")
    for r in rows:
        parts.append("<tr><td>%s</td><td>%d</td><td>%.1fs</td><td><b>%.3f</b></td>"
                     "<td>%.3fs</td><td>%s</td><td><b>%s</b></td></tr>"
                     % (esc(r["label"]), r["chars"], r["est_seconds"], r["speed"], r["phase"],
                        ("%.3fs（= 素材时长）" % r["cycle_before"]) if r["cycle_before"] else "-",
                        ("%.3fs" % r["cycle_after"]) if r["cycle_after"] else "无（已打散）"))
    parts.append("</table>")
    parts.append("<h2>四、入场一致性（模拟 %d 次重新入场，t=0.3s 取的帧）</h2><table>"
                 "<tr><th></th><th>首帧取值范围</th><th>种数</th></tr>"
                 "<tr><td>改前</td><td>%s</td><td><b>%d</b></td></tr>"
                 "<tr><td>改后</td><td>%s</td><td><b>%d</b></td></tr></table>"
                 % (P02_ENTRIES, esc(fixed), len(fixed), esc(spread), len(spread)))
    parts.append("</body></html>")
    return "\n".join(parts)


def p02_run():
    """P0-2 出片 + 指标（返回 HTML 路径；演示素材缺失时返回 None）。"""
    info = frames_of(P02_STATE)
    print("")
    print("=== P0-2 长句去重复（按播放层时间基出片）===")
    if info is None:
        print("[skip] %s 无素材，无法出片" % P02_STATE)
        return None
    print("演示素材: %s  %d 帧 @%.2ffps  %.3fs  %s"
          % (info["asset"], info["frames"], info["fps"], info["seconds"],
             "burst" if info["burst"] else "loop"))
    # 「改前」对三档是**同一段**（相位 0 / 速度 1.0）→ 只出一份，避免 3 份重复的 1.5MB GIF
    before = avatar_timing.sample_frame_indices(info["frames"], info["fps"], info["burst"],
                                                P02_SECONDS, phase=0.0, speed=1.0,
                                                out_fps=P02_OUT_FPS)
    period_before = avatar_timing.exact_period(before)
    before_gif = make_gif_from_indices(info, before, P02_OUTDIR / "before.gif")
    print("改前（三档共用）：精确周期 %s 点 = %.3fs（= 素材时长）"
          % (period_before, (period_before or 0) / P02_OUT_FPS))
    rows = []
    for label, text in P02_TEXTS:
        r = p02_one(label, text, info, before_gif, period_before)
        rows.append(r)
        print("[%s] %d 字 → 预计 %.1fs → speed %.3f → 精确周期 %s → %s"
              % (r["label"], r["chars"], r["est_seconds"], r["speed"],
                 ("%.3fs" % r["cycle_before"]) if r["cycle_before"] else "-",
                 ("%.3fs" % r["cycle_after"]) if r["cycle_after"] else "无（已打散）"))
    fixed, spread = p02_phase_spread(info)
    print("入场首帧: 改前 %d 种 %s → 改后 %d 种（前 8 个 %s）"
          % (len(fixed), fixed, len(spread), spread[:8]))
    P02_OUTDIR.mkdir(parents=True, exist_ok=True)
    page = P02_OUTDIR / "index.html"
    page.write_text(build_p02_html(rows, info, fixed, spread), encoding="utf-8")
    print("P0-2 页面: %s" % page)
    return page


# --------------------------------------------------------------------------- #
# 5) 入口
# --------------------------------------------------------------------------- #
def main():
    fsm, rows = run_scenario()

    print("=== 剧本时间线（真实 RuntimeFSM 驱动）===")
    for i, r in enumerate(rows, 1):
        info = r["info"]
        if info is None:
            tail = "无素材 → B2V 矢量"
        else:
            tail = "%s %d帧 @%.1ffps %.2fs %s%s" % (
                info["asset"], info["frames"], info["fps"], info["seconds"],
                "burst" if info["burst"] else "loop",
                " [回退]" if info["fallback"] else "")
        print("%2d | %-16s | %-30s | %s"
              % (i, r["state"], (r["event"] or "-"), tail))

    order = list(dict.fromkeys(r["state"] for r in rows))
    gifs = {}
    print("")
    for s in order:
        info = frames_of(s)
        if info is None:
            print("[skip] %-16s 无素材（真机退 B2V 矢量）" % s)
            continue
        gifs[s] = make_gif(s, info)
        print("[gif ] %-16s -> %-24s %2d 帧 / %3d ms 每帧"
              % (s, gifs[s][0], gifs[s][2], gifs[s][1]))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    page = OUTDIR / "index.html"
    page.write_text(build_html(rows, fsm, gifs), encoding="utf-8")

    all_states = [s.value for s in fsm.state.__class__]
    # 同 build_html：覆盖统计要算瞬时态（CANCELLED 进 history 后立刻被自动回迁，
    # 剧本行里看不到它），所以取 history 里出现过的所有状态。
    hist_states = sorted({h["to"] for h in fsm.history(limit=10 ** 6)} | {"IDLE"},
                         key=all_states.index)
    missing = [s for s in all_states if s not in hist_states]
    burst_states = sorted({r["state"] for r in rows
                           if r["info"] and r["info"]["burst"]})
    print("")
    print("状态覆盖 : %d/%d %s" % (len(hist_states), len(all_states),
                                  ("缺 " + ",".join(missing)) if missing else "（全覆盖）"))
    print("burst 动作: %d 次（%s）"
          % (len([r for r in rows if r["info"] and r["info"]["burst"]]),
             ",".join(burst_states)))
    print("回退次数 : %d" % len([r for r in rows
                                 if r["info"] and r["info"]["fallback"]]))
    print("非法转换 : %d" % fsm.rejected_count)
    print("页面     : %s" % page)
    p02_run()
    return 0


if __name__ == "__main__":
    sys.exit(main())


