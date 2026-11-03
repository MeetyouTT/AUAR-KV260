"use strict";
const players = [];
const cards = document.getElementById("cards");
const message = document.getElementById("message");

function element(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = text;
  return item;
}

function addVoice(voice, scenes) {
  const card = element("article", "card" + (voice.name === "Vivian" ? " featured" : ""));
  card.dataset.voice = voice.name;
  card.append(element("span", "badge", voice.name === "Vivian" ? "本轮重点" : "对照音色"));
  card.append(element("h2", "", voice.name));
  card.append(element("p", "description", voice.description));
  card.append(element("p", "style", voice.style_note));
  const all = element("button", "play-all", "播放全部四段");
  all.type = "button";
  all.disabled = !voice.complete;
  card.append(all);
  const sceneGroup = element("div", "scenes");
  const buttons = new Map();
  for (const scene of scenes) {
    const button = element("button", "scene", scene.label);
    button.type = "button";
    button.disabled = !voice.clips.some(clip => clip.id === scene.id);
    sceneGroup.append(button);
    buttons.set(scene.id, button);
  }
  card.append(sceneGroup);
  const audio = element("audio");
  audio.controls = true;
  audio.preload = "none";
  audio.setAttribute("aria-label", voice.name + " 试听播放器");
  if (voice.file) audio.src = voice.file;
  else audio.style.display = "none";
  card.append(audio);
  players.push(audio);
  const spoken = element("div", "spoken");
  const caption = element("b", "", "选择一段开始试听");
  const transcript = element("p", "", "每种声音使用相同台词，便于比较。");
  spoken.append(caption, transcript);
  card.append(spoken);
  if (voice.complete) {
    const download = element("a", "download", "下载这款声音的完整试听");
    download.href = voice.file;
    download.download = voice.name + "_试听.wav";
    card.append(download);
  }
  card.append(element("p", "status", voice.complete ? "四段试听已齐备" : `已有 ${voice.clips.length} / ${scenes.length} 段，其余正在准备`));
  let mode = "all";
  let single = null;
  function updateCaption(clip) {
    for (const [id, button] of buttons) button.classList.toggle("active", clip?.id === id);
    caption.textContent = clip ? clip.label : "片段间停顿";
    transcript.textContent = clip ? clip.text : "";
  }
  function play(src, clip) {
    mode = clip ? "single" : "all";
    single = clip;
    audio.src = src;
    updateCaption(clip || voice.clips[0]);
    audio.play().catch(() => {
      message.textContent = "暂时无法播放，请使用播放器的播放按钮重试。";
    });
  }
  all.addEventListener("click", () => play(voice.file, null));
  for (const clip of voice.clips) buttons.get(clip.id).addEventListener("click", () => play(clip.file, clip));
  audio.addEventListener("play", () => {
    for (const other of players) if (other !== audio) other.pause();
    card.classList.add("playing");
    message.textContent = "";
  });
  audio.addEventListener("pause", () => card.classList.remove("playing"));
  audio.addEventListener("ended", () => card.classList.remove("playing"));
  audio.addEventListener("timeupdate", () => {
    const clip = mode === "single" ? single : voice.clips.find(row => audio.currentTime >= row.start_seconds && audio.currentTime < row.end_seconds);
    updateCaption(clip);
  });
  cards.append(card);
}

fetch("comparison.json", {cache: "no-store"})
  .then(response => { if (!response.ok) throw new Error("comparison data"); return response.json(); })
  .then(data => {
    const order = ["Vivian", "Serena", "Kokoro"];
    data.voices.sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name));
    for (const voice of data.voices) addVoice(voice, data.scenes);
  })
  .catch(() => { message.className = "error"; message.textContent = "试听页面尚未就绪。请通过“启动试听”打开，或稍后刷新页面。"; });
