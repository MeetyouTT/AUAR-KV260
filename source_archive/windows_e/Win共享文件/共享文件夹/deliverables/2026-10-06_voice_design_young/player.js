"use strict";
const players = [];
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
fetch("comparison.json", {cache: "no-store"})
  .then(response => { if (!response.ok) throw new Error("data"); return response.json(); })
  .then(data => {
    for (const voice of data.voices) {
      const card = el("article", "card " + (voice.is_reference ? "reference" : "new"));
      card.append(el("span", "badge", voice.is_reference ? "同台词对照" : "新声线"));
      card.append(el("h2", "", voice.name));
      card.append(el("p", "description", voice.description));
      const button = el("button", "listen", "播放两句短样");
      button.type = "button";
      const audio = el("audio");
      audio.src = voice.file;
      audio.controls = true;
      audio.preload = "metadata";
      audio.setAttribute("aria-label", voice.name + " 试听播放器");
      players.push(audio);
      button.addEventListener("click", () => {
        if (!audio.paused) audio.pause();
        else audio.play().catch(() => { document.getElementById("message").textContent = "暂时无法播放，请使用播放器按钮重试。"; });
      });
      audio.addEventListener("play", () => {
        for (const other of players) if (other !== audio) other.pause();
        card.classList.add("playing");
        button.textContent = "暂停试听";
      });
      function stop() { card.classList.remove("playing"); button.textContent = "播放两句短样"; }
      audio.addEventListener("pause", stop);
      audio.addEventListener("ended", stop);
      const script = el("div", "script");
      script.append(el("b", "", "相同台词"), el("p", "", data.text));
      const download = el("a", "download", "下载这段试听");
      download.href = voice.file;
      download.download = voice.name + ".wav";
      card.append(button, audio, script, download);
      document.getElementById("cards").append(card);
    }
  })
  .catch(() => { document.getElementById("message").textContent = "试听尚在准备，请稍后刷新页面。"; });
