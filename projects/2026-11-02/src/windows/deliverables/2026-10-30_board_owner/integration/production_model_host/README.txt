Windows production model-only entry. No scheduled task or boot hook added.

From the project directory in PowerShell:
  .\start_inference.ps1
  .\start_inference.ps1 -Action Status
  .\stop_inference.ps1
  .\start_inference.ps1 -Action Restart
  .\stop_inference.ps1 -ReleaseOwnedModel

The configured existing OmniVoice Python is explicit in
aura/config/model_inference.local.json. -VoicePython remains accepted for the
command environment. The detached runtime itself always uses that configured
voice interpreter. Startup has one original300-second total deadline; TTS
uses that same deadline before loading the fixed27B. The service has no TTL.
The WMI hidden independent parent is the same project launch technique already
used by the old stack; the calling terminal can close after READY.

Listen192.168.50.1:8797, POST only from explicit board peer192.168.50.2:
  /v1/inference/llm, /v1/inference/tts, /v1/inference/cancel
  /v1/inference/warmup (explicit diagnostic only)
  GET /health, GET /v1/inference/preflight
This host may read GET /health for the existing model dashboard. No ASR or
legacy8792 protocol is provided. Root owns the board's only business entry.

Requests remain complete caller-owned messages with protocol_version1,
request_id/board_boot_id/session_id/generation/budget_ms. Windows injects no
persona/history/identity context and opens no business DB. TTS returns only
RAM24k mono PCM16 with hash metadata, using original OmniVoice16/reference.
Model resources/config are reused; LLM weights remainD:/AIModels and Ollama
dataD:/AIModels/Ollama-AURA. No language model is copied or downloaded.

Default Stop cancels current work and closes only this host and its owned TTS.
It leaves the fixed project daemon and its27B keep-alive alone. Immediate Start
after such a Stop may safely refuse while27B remains resident, because cold
TTS-first needs the original calibrated headroom. Explicit Restart (or Stop
-ReleaseOwnedModel) requires this running host truly idle, exact same11435
daemon PID/birth/executable/command/listeners, fixed27B-only residency, and this
host's prior proof that it uniquely loaded that model. It then closes its TTS,
releases only that owned fixed27B, and starts TTS-first again. It never stops
the11435 daemon, default11434, portrait8796 or other model/process. Changed or
absent ownership proof refuses release. A crashed owner's model is not silently
adopted/unloaded; inspect its receipt or wait for the normal30-minute keepalive.
Control requests are session-bound local markers, never taskkill/Stop-Process.

The same original voice8792.instance.lock is held through all startup,
serving, error cleanup and any explicit owned-model release. GPU admission
adaptive/enforcing and calibrated thresholds are unchanged. No automatic
unload, priority change or second TTS is used to make startup pass.

Metadata receipts are latest.json and sessions/<session>/status.json. The
runtime discards stdout/stderr model diagnostics and stores no input/reply/PCM.
The original bounded ownership guards remain:8pending,256request tombstones,
128owner epochs; capacity refusal requires a controlled idle restart.

The old start_voice.ps1 and start_background_models.ps1 are NOT changed yet.
Their exact source archives and prepared compatibility wrapper/gate are here.
Root will explicitly apply them together with business_owner.local.json after
the migration bundle and board single-writer handover are verified. A pending
owner marker must receive root's handover manifest path/SHA before publication.
Direct historical source/test fixtures are never changed.

Validation:7 fake lifecycle/ownership/cleanup tests;7 selected cold-start
budget tests including a125-second virtual cold TTS; actual TTS-first/fixed27B
READY and unchanged default11434; idempotent entry + unique RAM TTS probe;
existing dashboard metadata-only snapshot. No GUI, microphone, physical audio,
identity/private DB, board device or extra performance test was performed.
The actual normal restart command is implemented/fake-checked; the now-ready
service is left running for root's board integration rather than cycled again.
