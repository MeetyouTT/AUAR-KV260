import os,json
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None);sink=Gst.ElementFactory.make('ximagesink');result=sink.set_state(Gst.State.READY);sink.get_state(Gst.SECOND)
caps=sink.get_static_pad('sink').query_caps(None).to_string();sink.set_state(Gst.State.NULL)
print(json.dumps({'caps':caps,'ready':str(result)}))
