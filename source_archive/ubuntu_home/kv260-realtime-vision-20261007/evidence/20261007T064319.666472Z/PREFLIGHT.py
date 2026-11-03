import os;from pathlib import Path;assert os.uname().machine=='aarch64';assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100';
import subprocess,json
release='/home/root/aura-realtime-vision-20261007/releases/fcc207d4b226988f'
for command in [["python3","-m","unittest","-v","test_vision_core.py"],["python3","realtime_vision.py","--preflight"]]:
 p=subprocess.run(command,cwd=release,capture_output=True,text=True,timeout=25)
 print(p.stdout+p.stderr)
 assert p.returncode==0
import gi
gi.require_version("Gst","1.0")
gi.require_version("GstVideo","1.0")
from gi.repository import Gst,GstVideo
Gst.init(None)
info=GstVideo.VideoInfo()
assert info.from_caps(Gst.Caps.from_string("video/x-raw,format=BGR,width=640,height=480,framerate=30/1"))
assert (info.width,info.height,info.stride[0])==(640,480,1920)
for name in ["v4l2src","appsink","appsrc","videoconvert","ximagesink"]:
 assert Gst.ElementFactory.find(name)
assert Gst.ElementFactory.make("appsrc").find_property("current-level-bytes")
print("GSTREAMER_PREFLIGHT_PASS")
