import fs from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Presentation, PresentationFile } from 'file:///C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';

const buildDir = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = 'E:/Win共享文件/语音共享文件';
const frameRoot = `${projectRoot}/deliverables/2026-11-02_avatar_animation_optimization/revision4_dialogue_motion/board_results/previews/after_R4`;
const sourceRoot = 'E:/AUAR_工程交付_20261102/aura';
const progress = `${projectRoot}/deliverables/2026-11-02_5090_deployment/project_progress_20261102/PROJECT_PROGRESS.json`;
const font = 'Microsoft YaHei';
const C = { paper: '#FCFCF3', ink: '#262D3D', muted: '#656979', red: '#8A334A', pale: '#DBB7BB', white: '#FCFCF3' };
const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const schedule = [];

function text(slide, name, value, x, y, w, h, size, color = C.ink, bold = false, alignment = 'left') {
  const s = slide.shapes.add({ geometry: 'textbox', name, position: { left: x, top: y, width: w, height: h }, fill: 'none', line: { fill: 'none', width: 0 } });
  s.text = value;
  s.text.style = { typeface: font, fontSize: size, bold, color, alignment, verticalAlignment: 'middle', wrap: 'word', autoFit: 'none', insets: 0 };
  return s;
}
function base(duration, notes) {
  const s = p.slides.add();
  s.background.fill = C.paper;
  s.speakerNotes.text = notes;
  schedule.push({ slide: p.slides.items.length, seconds: duration, elements: [], characterClip: null });
  return s;
}
function animate(name, at, duration = 0.45, effect = 10) { schedule.at(-1).elements.push({ name, at, duration, effect }); }
function avatar(s, clip, frame, x = 778, y = 34, height = 686) {
  const width = height * 423 / 516;
  const im = s.images.add({ blob: new Uint8Array(readFileSync(`${frameRoot}/${String(frame).padStart(4, '0')}.png`)), contentType: 'image/png', alt: '项目已有雪妃角色原生离屏渲染', fit: 'contain', position: { left: x, top: y, width, height } });
  schedule.at(-1).characterClip = { clip, x, y, width, height };
  return im;
}
function note(narration, facts, range) {
  return `解说参考：${narration}\n\n资料依据：${facts}\n角色素材：${projectRoot}/deliverables/2026-11-02_avatar_animation_optimization/revision4_dialogue_motion/README_R4.md，原生 GLES 离屏渲染 ${range}。合成音量驱动，非实屏录像，不含现场录音。\n本演示概括项目功能，不构成全功能同时运行、冷启动或性能保证。`;
}

{
  const s = base(3, note('AUAR雪妃是一套基于KV260的多模态陪伴机器人。', `${sourceRoot}/readme.md`, '待机片段'));
  avatar(s, 'idle', 0, 704, 18, 702);
  text(s, 'brand', 'AUAR·雪妃', 86, 238, 700, 108, 78, C.red, true);
  text(s, 'subtitle', '基于 KV260 的多模态陪伴机器人', 91, 366, 680, 64, 31, C.ink);
  animate('brand', 0.12, 0.6); animate('subtitle', 0.6, 0.55);
}
{
  const s = base(5, note('相机识别人脸，判断位置，再由单轴机构跟随。', `${sourceRoot}/readme.md；${progress} 的视觉感知和转轴跟随条目。人脸与声纹独立，本页不表示跨模态身份联绑。`, '聆听片段'));
  avatar(s, 'listening', 48, 740, 62, 658);
  text(s, 'title', '视觉感知与跟随', 86, 80, 800, 88, 58, C.ink, true);
  text(s, 'step1', '识别人脸', 91, 256, 530, 72, 47, C.red, true);
  text(s, 'step2', '判断位置', 91, 351, 530, 72, 47, C.ink);
  text(s, 'step3', '转轴跟随', 91, 446, 530, 72, 47, C.ink);
  animate('title', 0.05); animate('step1', 0.45); animate('step2', 1.3); animate('step3', 2.15);
}
{
  const s = base(6, note('语音识别后，本地27B大模型生成回答，再通过语音和角色口型表达。', `${sourceRoot}/src/windows/readme.md；${sourceRoot}/report/release_status.md；${progress} 基础语音对话条目。画面台词为交互示意，不是本次实际模型输出或录音。`, '普通回答片段'));
  avatar(s, 'speaking', 144, 748, 72, 648);
  text(s, 'title', '自然语音对话', 86, 80, 800, 88, 58, C.ink, true);
  text(s, 'user_line', '“今天有点累，\n陪我聊两句。”', 90, 238, 670, 156, 45, C.ink);
  text(s, 'reply_line', '“我陪你聊点轻松的。”', 91, 426, 690, 80, 41, C.red, true);
  text(s, 'tech', '语音识别  /  本地 27B  /  语音与口型', 92, 586, 780, 46, 27, C.muted);
  text(s, 'demo_label', '台词示意', 92, 648, 160, 30, 20, C.muted);
  animate('title', 0.05); animate('user_line', 0.3, 0.5); animate('reply_line', 1.8, 0.6); animate('tech', 2.6, 0.45); animate('demo_label', 0.3, 0.3);
}
{
  const s = base(4, note('系统保留近期上下文，也通过摘要和检索支持话题延续。', `${progress} 记忆条目；${sourceRoot}/report/release_status.md 身份和记忆条目。用户反馈基本可用，不宣称长期或任意跨度的检索已经完整验收。`, '思考片段'));
  avatar(s, 'thinking', 96, 740, 62, 658);
  text(s, 'title', '对话记忆', 86, 80, 800, 88, 58, C.ink, true);
  text(s, 'primary', '保留近期上下文', 91, 266, 690, 82, 49, C.red, true);
  text(s, 'secondary', '历史摘要与检索', 92, 379, 680, 74, 43, C.ink);
  text(s, 'outcome', '让多轮聊天接得上', 93, 535, 660, 52, 31, C.muted);
  animate('title', 0.05); animate('primary', 0.35); animate('secondary', 1.1); animate('outcome', 1.85);
}
{
  const s = base(5, `解说参考：KV260负责感知、记忆和运动控制，Windows主机负责本地语言与语音推理，二者通过局域网协作。\n\n资料依据：${sourceRoot}/readme.md；${sourceRoot}/report/release_status.md；${sourceRoot}/src/windows/readme.md。视觉三模型使用板端DPU，声纹ECAPA在CPU，LLM和TTS在Windows。本页不表示27B运行在FPGA或板端。`);
  s.background.fill = C.ink;
  text(s, 'title', '板端与主机协作', 86, 80, 1050, 88, 58, C.white, true);
  text(s, 'board_name', 'KV260', 90, 245, 490, 100, 74, C.white, true);
  text(s, 'host_name', 'Windows 主机', 744, 260, 476, 84, 49, C.white, true);
  text(s, 'board_jobs', 'DPU 视觉加速\n交互、记忆与运动控制', 94, 386, 565, 128, 34, C.white);
  text(s, 'host_jobs', '27B 本地大模型\nOmniVoice 语音合成', 748, 386, 480, 128, 34, C.white);
  text(s, 'lan', '局域网连接', 498, 597, 285, 55, 29, C.pale, false, 'center');
  animate('title', 0.05); animate('board_name', 0.35); animate('board_jobs', 0.65); animate('host_name', 1.35); animate('host_jobs', 1.65); animate('lan', 2.5);
}
{
  const s = base(3, note('AUAR雪妃，将视觉、语音和记忆结合成陪伴交互原型。', `${sourceRoot}/readme.md；${progress}`, '积极回答片段'));
  avatar(s, 'positive', 208, 704, 18, 702);
  text(s, 'brand', 'AUAR·雪妃', 86, 235, 700, 108, 77, C.red, true);
  text(s, 'closing', '多模态陪伴交互原型', 92, 373, 700, 70, 39, C.ink);
  animate('brand', 0.1, 0.6); animate('closing', 0.65, 0.55);
}

await fs.mkdir(path.join(buildDir, 'renders'), { recursive: true });
for (const [i, slide] of p.slides.items.entries()) {
  const png = await p.export({ slide, format: 'png', scale: 1 });
  await fs.writeFile(path.join(buildDir, 'renders', `slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
}
await (await PresentationFile.exportPptx(p)).save(path.join(buildDir, 'draft.pptx'));
await fs.writeFile(path.join(buildDir, 'timing.json'), JSON.stringify({ advanceTotal: 26, transitionSeconds: 0.3, slides: schedule }, null, 2));
await fs.writeFile(path.join(buildDir, 'snapshot.json'), JSON.stringify(p.toProto()));
console.log(JSON.stringify({ draft: path.join(buildDir, 'draft.pptx'), slides: p.slides.items.length, scheduledAdvanceSeconds: 26 }));
