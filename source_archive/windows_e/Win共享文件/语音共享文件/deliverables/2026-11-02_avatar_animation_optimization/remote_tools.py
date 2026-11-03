import subprocess,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def ssh(script,timeout=60):
    p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=7','aura-ubuntu','python3 -'],input=script.encode(),capture_output=True,timeout=timeout)
    if p.returncode: raise RuntimeError(p.stderr.decode(errors='replace')[-4000:])
    return p.stdout
if __name__=='__main__':
    script='''from pathlib import Path
import subprocess,json,shutil,ctypes.util
result={"compilers":[str(p) for p in Path('/usr/bin').glob('*g++*')],"cxx_version":subprocess.check_output(['c++','--version']).decode().splitlines()[0],"libs":{n:ctypes.util.find_library(n) for n in ['EGL','GLESv2','png16']},"homes":[p.name for p in Path.home().iterdir() if p.is_dir() and not p.name.startswith('.')],"tools":{n:shutil.which(n) for n in ['pkg-config','ar','make','g++-12','g++-13','ninja']}}
print(json.dumps(result,ensure_ascii=False))
'''
    print(ssh(script).decode())
    import importlib.util
    print(json.dumps({n:importlib.util.find_spec(n) is not None for n in ['PIL','numpy','cv2','imageio','imageio_ffmpeg']}))
