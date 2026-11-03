"""Inspect installed Gst factories/properties only, without pipelines/devices."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
helper=HERE.parents[2]/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('gst_inspection_transport',helper)
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
code='''import os
os.environ['GST_REGISTRY_UPDATE']='no'
import gi,json
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None)
result={'version':Gst.version_string(),'factories':{}}
for name in ('videoconvert','videoscale','videoconvertscale','ximagesink','xvimagesink','glimagesink'):
    factory=Gst.ElementFactory.find(name)
    if not factory:
        result['factories'][name]={'available':False};continue
    item={'available':True,'sink_caps':[t.get_caps().to_string() for t in factory.get_static_pad_templates() if t.direction==Gst.PadDirection.SINK]}
    if name in ('videoconvert','videoscale','videoconvertscale'):
        element=factory.create(None)
        item['properties']={}
        for prop in element.list_properties():
            if prop.name in ('n-threads','method','dither','chroma-resampler','qos','add-borders'):
                value=element.get_property(prop.name)
                item['properties'][prop.name]=int(value) if isinstance(value,int) else bool(value) if isinstance(value,bool) else str(value)
    result['factories'][name]=item
print(json.dumps(result))
'''
data=json.loads(transport.ssh('python3 -B -',code,timeout=15))
with (HERE/'GST_FACTORY_INSPECTION.json').open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2)
print(json.dumps(data))
