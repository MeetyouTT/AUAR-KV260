"use strict";
const audio = document.getElementById("audio");
const label = document.getElementById("label");
const transcript = document.getElementById("text");
const group = document.getElementById("scenes");
const buttons = new Map();
let clips = [];
let mode = "all";
let selected = null;
function update(clip) {
  for (const [id, button] of buttons) button.classList.toggle("active", clip?.id === id);
  label.textContent = clip ? clip.label : "片段间停顿";
  transcript.textContent = clip ? clip.text : "";
}
fetch("comparison.json", {cache:"no-store"}).then(response => {
  if (!response.ok) throw new Error("data"); return response.json();
}).then(data => {
  clips = data.clips;
  audio.src = data.file;
  document.getElementById("download").href = data.file;
  for (const clip of clips) {
    const button = document.createElement("button");
    button.type = "button"; button.className = "scene"; button.textContent = clip.label;
    button.addEventListener("click", () => { mode="single"; selected=clip; audio.src=clip.file; update(clip); audio.play(); });
    buttons.set(clip.id, button); group.append(button);
  }
  document.querySelector(".play-all").addEventListener("click", () => { mode="all"; selected=null; audio.src=data.file; update(clips[0]); audio.play(); });
  audio.addEventListener("timeupdate", () => update(mode === "single" ? selected : clips.find(clip => audio.currentTime >= clip.start_seconds && audio.currentTime < clip.end_seconds)));
}).catch(() => { label.textContent="试听尚未就绪"; transcript.textContent="请稍后刷新页面。"; });
