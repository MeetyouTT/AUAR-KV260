"""Build a portable local audition page from verified generated files."""
import hashlib
import html
import json
from pathlib import Path
import wave

HERE = Path(__file__).resolve().parent


def main():
    cases = json.loads((HERE/'cases.json').read_text(encoding='utf-8'))['cases']
    engines = ['qwen','omnivoice_16','omnivoice_32']
    labels = ['Qwen 当前音色对照','OmniVoice 16 步','OmniVoice 32 步']
    reports = {}
    for engine in engines:
        path = HERE/'runs'/engine/'report.json'
        if path.exists():
            report = json.loads(path.read_text(encoding='utf-8'))
            for clip in report['clips']:
                audio = HERE/clip['file']
                if hashlib.sha256(audio.read_bytes()).hexdigest() != clip['sha256']:
                    raise ValueError('SHA mismatch: '+str(audio))
                with wave.open(str(audio)) as w:
                    if (w.getframerate(),w.getnchannels(),w.getsampwidth()) != (24000,1,2):
                        raise ValueError('WAV format mismatch')
            reports[engine] = report
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>汐蓝 · 语音活人感对照</title><style>body{font:16px system-ui;background:#f7f9fc;color:#20304a;margin:32px auto;max-width:1250px;padding:0 20px}h1{font-size:28px}table{width:100%;border-collapse:collapse;background:white}td,th{padding:16px;border:1px solid #dae2ef;text-align:left;vertical-align:top}th{background:#e9effa}audio{max-width:100%;width:240px}small{display:block;color:#59677a;margin-top:8px}textarea{width:92%;min-height:55px;margin-top:10px}button{padding:10px;margin:12px 0;cursor:pointer}.note{padding:16px;background:#fff4d7;line-height:1.7}</style>',
        '<h1>汐蓝 · 语音活人感对照</h1><p>同一段柔亮俏皮参考、相同台词、音量近似对齐。先听短回应与安慰，再比较长句节奏。</p>',
        '<p>固定声音参考（原始逐字转写含历史名字）：<audio controls preload="none" src="../2026-10-06_voice_selected_soft_young/reference/soft_young.wav"></audio></p>',
        '<p class="note">评价：①像在和我说话 ②情绪是否恰当 ③是否仍是同一角色，各 1–5 分。关注重音、停顿、句尾和拖腔。技术通过不等于人耳认可。计时是完整合成耗时，不含模型加载，未测实际开口延迟；每次加载后的首次生成可能更慢，详见报告。</p>',
        '<button onclick="exportNotes()">导出我的试听评价</button><table><thead><tr><th>场景</th>']
    parts += ['<th>'+label+'</th>' for label in labels]
    parts.append('</tr></thead><tbody>')
    for case in cases:
        parts.append('<tr><td><b>'+html.escape(case['label'])+'</b><p>'+html.escape(case['text'])+'</p><small>'+html.escape(case['focus'])+'</small></td>')
        for engine in engines:
            clip = next((c for c in reports.get(engine,{}).get('clips',[]) if c['id']==case['id']),None)
            if clip:
                parts.append('<td><audio controls preload="none" src="'+html.escape(clip['file'],quote=True)+'"></audio>'
                    +f'<small>音频 {clip["duration_seconds"]:.2f}s · 合成 {clip["generation_seconds"]:.3f}s · RTF {clip["rtf"]:.3f}</small>'
                    +'<textarea data-key="'+engine+'/'+case['id']+'" placeholder="自然感 / 情绪 / 音色，各 1–5 分；备注"></textarea></td>')
            else:
                parts.append('<td>尚未生成</td>')
        parts.append('</tr>')
    parts.append('</tbody></table><script>document.querySelectorAll("audio").forEach(a=>a.addEventListener("play",()=>document.querySelectorAll("audio").forEach(b=>{if(a!==b)b.pause()})));function exportNotes(){const notes={date:new Date().toISOString(),ratings:{}};document.querySelectorAll("textarea").forEach(t=>notes.ratings[t.dataset.key]=t.value);const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(notes,null,2)],{type:"application/json"}));a.download="listening_ratings.json";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}</script></html>')
    (HERE/'index.html').write_text('\n'.join(parts),encoding='utf-8')
    print('PAGE BUILT; verified clips:',sum(len(r['clips']) for r in reports.values()))


if __name__=='__main__':
    main()
