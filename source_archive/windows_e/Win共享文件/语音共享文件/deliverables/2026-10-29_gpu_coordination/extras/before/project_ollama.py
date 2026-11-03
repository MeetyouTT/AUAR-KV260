"""Start local Ollama with weights stored outside the project."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HOST = 'http://127.0.0.1:11435'
STORAGE=json.loads((ROOT/'aura/config/model_storage.local.json').read_text(encoding='utf-8-sig'))

def ensure():
    def ready():
        try:
            with urllib.request.urlopen(HOST + '/api/version', timeout=2) as response:
                return response.status == 200
        except OSError:
            return False
    if ready():
        return
    executable = shutil.which('ollama')
    if not executable:
        raise RuntimeError('Ollama executable not installed')
    env = dict(os.environ, OLLAMA_HOST='127.0.0.1:11435',
        OLLAMA_MODELS=STORAGE['ollama_directory'], OLLAMA_NO_CLOUD='1',
        OLLAMA_NUM_PARALLEL='1', OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_CONTEXT_LENGTH='2048')
    with (HERE/'project_ollama_stdout.log').open('a', encoding='utf-8') as output, \
         (HERE/'project_ollama_stderr.log').open('a', encoding='utf-8') as error:
        process = subprocess.Popen([executable, 'serve'], env=env, cwd=ROOT,
            stdout=output, stderr=error, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (HERE/'project_ollama_process.json').write_text(json.dumps({'pid':process.pid,
        'host':HOST, 'models':env['OLLAMA_MODELS']}), encoding='utf-8')
    for _ in range(30):
        if ready():
            return
        if process.poll() is not None:
            raise RuntimeError('Project Ollama failed; inspect project_ollama_stderr.log')
        time.sleep(1)
    raise RuntimeError('Project Ollama did not become ready')

if __name__ == '__main__':
    ensure()
    print('Project Ollama ready at', HOST)
