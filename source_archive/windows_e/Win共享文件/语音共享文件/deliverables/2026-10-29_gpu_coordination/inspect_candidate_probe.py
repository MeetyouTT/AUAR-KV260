"""Run only the new read-only probes against existing endpoints."""
import bootstrap
import hashlib,json
from pathlib import Path
from common.gpu_coordination import GpuCoordinator,GpuPolicy,NvidiaMemoryProbe,OllamaResidencyProbe
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
config=json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
probe=NvidiaMemoryProbe();sample=probe.read()
residency=OllamaResidencyProbe(config['ollama_host'],config['model'])
c=GpuCoordinator(GpuPolicy(),probe,llm_residency=residency)
data={'status':'PASS','memory':probe.public(),'llm_residency':residency.status(),'coordinator':c.public(),
 'generation_or_loading_performed':False,'live_sources_changed':False}
old=json.loads((H/'baseline_sources.json').read_text())
assert all(hashlib.sha256((A/name).read_bytes()).hexdigest()==sha for name,sha in old.items())
(H/'candidate_probe.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data))
