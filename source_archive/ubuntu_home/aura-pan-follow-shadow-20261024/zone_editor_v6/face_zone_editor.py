"""Current-display face-only boundary editor. Does not open any motor device."""
import argparse,collections,ctypes,ctypes.util,json,math,os,threading,time,urllib.request
from pathlib import Path
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk,GLib

VIEW=(8,112,568,300)
CONTENT=(92,112,400,300)


def image_ratio(widget_ratio):return (widget_ratio*VIEW[2]-(CONTENT[0]-VIEW[0]))/CONTENT[2]
def widget_ratio(value):return (CONTENT[0]-VIEW[0]+value*CONTENT[2])/VIEW[2]


def face_position(packet,boot,now,left,right):
    if not isinstance(packet,dict):return None,'人脸位置：未确认','UNCONFIRMED'
    source=packet.get('source_mono_ms');anchor=packet.get('face_detection_mono_ms')
    target=packet.get('target') or {};box=target.get('box');score=target.get('score')
    if (packet.get('state')!='READY' or packet.get('target_kind')!='face' or packet.get('board_boot_id')!=boot
            or packet.get('mirror_horizontal') is not True or packet.get('frame_width')!=640 or packet.get('frame_height')!=480
            or type(source) is not int or type(anchor) is not int or not 0<=now-source<250 or not 0<=now-anchor<500
            or not isinstance(box,list) or len(box)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in box)
            or type(score) not in (int,float) or not .9<=score<=1):
        return None,'人脸位置：未确认','UNCONFIRMED'
    x,y,w,h=box
    if min(x,y)<0 or min(w,h)<48 or x+w>640 or y+h>480 or w/640>.7:
        return None,'人脸位置：未确认','UNCONFIRMED'
    if x/640<=left:return box,'人脸位置：左侧越线','LEFT'
    if (x+w/2)/640>right:return box,'人脸位置：右侧越线','RIGHT'
    return box,'人脸位置：区域内','INSIDE'


def setup_font():
    aura=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5/runtime/aura')
    cfg=json.loads((aura/'config/board_avatar_gtk.json').read_text())
    font=(aura/cfg['font_file']).resolve(strict=True)
    fc=ctypes.CDLL(ctypes.util.find_library('fontconfig'))
    fc.FcConfigAppFontAddFile.argtypes=(ctypes.c_void_p,ctypes.c_char_p)
    fc.FcConfigAppFontAddFile.restype=ctypes.c_int
    if not fc.FcConfigAppFontAddFile(None,str(font).encode()):raise RuntimeError('Bundled Chinese font unavailable')
    Gtk.Settings.get_default().set_property('gtk-font-name','Droid Sans Fallback 12')


class Editor:
    def __init__(self,path):
        self.path=path;self.closed=threading.Event();self.condition=threading.Condition()
        self.pending=None;self.drag=False;self.timer=None;self.ratio=.75;self.last_slider_stop=0.
        self.saved_fields={};self.left_camera_ratio=.1
        if path.is_file():
            old=json.loads(path.read_text());self.saved_fields=dict(old)
            self.ratio=float(old.get('right_ratio',.75));self.left_camera_ratio=float(old.get('left_camera_ratio',.1))
        if not math.isfinite(self.left_camera_ratio) or not 0<=self.left_camera_ratio<=.3:
            raise ValueError('Finite left camera boundary in 0..0.3 required')
        self.ratio=max(widget_ratio(.3),min(widget_ratio(.95),self.ratio));self.active=False;self.updating=False
        self.line=self.bar('AURA_FACE_RIGHT_BOUNDARY','#f9a825',7,VIEW[3],False)
        self.left_line=self.bar('AURA_FACE_LEFT_BOUNDARY','#43d17a',5,CONTENT[3],True)
        self.faces=[self.bar('AURA_FACE_TARGET_'+str(i),'#00b8ff',2,2,True) for i in range(5)]
        self.hint_window=Gtk.Window(type=Gtk.WindowType.POPUP);self.hint_window.set_title('AURA_FACE_ZONE_HINT')
        self.hint_window.set_decorated(False);self.hint_window.set_keep_above(True);self.hint_window.set_accept_focus(False)
        self.hint_window.set_resizable(False);self.hint_window.set_default_size(400,30);self.hint_window.move(92,78)
        self.hint_label=Gtk.Label(label='人脸位置：未确认');self.hint_window.add(self.hint_label)
        self.hint_window.connect('realize',lambda widget:widget.get_window().set_pass_through(True))
        self.boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.position_counts=collections.Counter();self.position_events=collections.deque(maxlen=64)
        self.last_position_source=None;self.last_position=None;self.next_position_write=0.
        self.line.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK)
        self.line.connect('button-press-event',self.press);self.line.connect('motion-notify-event',self.motion);self.line.connect('button-release-event',self.release)
        # Popup windows bypass the desktop's automatic maximization policy.
        self.panel=Gtk.Window(type=Gtk.WindowType.POPUP);self.panel.set_title('AURA · 人脸右边界');self.panel.set_decorated(False);self.panel.set_keep_above(True);self.panel.set_resizable(False);self.panel.set_default_size(400,170);self.panel.move(604,393)
        self.panel.connect('delete-event',lambda *_:(self.panel.hide(),True)[1])
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=7);box.set_border_width(10);self.panel.add(box)
        label=Gtk.Label(label='绿线：左边界　橙线：右边界　蓝框/蓝点：人脸');label.set_max_width_chars(26);label.set_line_wrap(True);box.pack_start(label,False,False,0)
        self.scale=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,30,95,1);self.scale.set_value(image_ratio(self.ratio)*100);self.scale.set_digits(0)
        self.scale.connect('format-value',lambda _,v:'右边界 '+str(round(v))+'%');self.scale.connect('value-changed',self.changed);box.pack_start(self.scale,False,False,0)
        self.status=Gtk.Label(label='左侧脸框左沿触绿线，右侧蓝点越橙线。');self.status.set_max_width_chars(26);self.status.set_line_wrap(True);box.pack_start(self.status,False,False,0)
        buttons=Gtk.Box(spacing=8)
        save=Gtk.Button(label='保存并收起');save.connect('clicked',self.save_hide);buttons.pack_start(save,True,True,0)
        stop=Gtk.Button(label='停止转轴');stop.connect('clicked',lambda *_:self.command('pan_stop'));buttons.pack_start(stop,True,True,0);box.pack_start(buttons,False,False,0)
        self.place_line();self.queue_save()
        threading.Thread(target=self.save_worker,name='face-zone-save',daemon=True).start()
        threading.Thread(target=self.poll,name='face-zone-observation',daemon=True).start()

    @staticmethod
    def bar(title,color,w,h,transparent_input):
        window=Gtk.Window(type=Gtk.WindowType.POPUP);window.set_title(title);window.set_decorated(False);window.set_keep_above(True);window.set_accept_focus(False)
        window.set_default_size(w,h);window.resize(w,h)
        box=Gtk.DrawingArea();window.add(box);rgba=Gdk.RGBA();rgba.parse(color)
        def draw(widget,cr):cr.set_source_rgb(rgba.red,rgba.green,rgba.blue);cr.paint();return False
        box.connect('draw',draw)
        if transparent_input:
            def passthrough(widget):
                try:widget.get_window().set_pass_through(True)
                except AttributeError:pass
            window.connect('realize',passthrough)
        return window

    def place_line(self):
        self.line.move(round(VIEW[0]+VIEW[2]*self.ratio)-3,VIEW[1]);self.line.resize(7,VIEW[3])
        self.left_line.move(round(CONTENT[0]+CONTENT[2]*self.left_camera_ratio)-2,CONTENT[1]);self.left_line.resize(5,CONTENT[3])

    def set_ratio(self,value):
        value=max(widget_ratio(.3),min(widget_ratio(.95),value))
        if value!=self.ratio and not self.drag and time.monotonic()-self.last_slider_stop>.3:
            self.command('pan_stop');self.last_slider_stop=time.monotonic()
        self.ratio=value;self.place_line()
        self.updating=True;self.scale.set_value(image_ratio(self.ratio)*100);self.updating=False
        if self.timer:GLib.source_remove(self.timer)
        self.timer=GLib.timeout_add(180,self.queue_save)

    def changed(self,widget):
        if not self.updating:self.set_ratio(widget_ratio(widget.get_value()/100.))
    def press(self,widget,event):
        self.drag=True;self.panel.show_all();self.command('pan_stop');return True
    def motion(self,widget,event):
        if self.drag:self.set_ratio((event.x_root-VIEW[0])/VIEW[2]);return True
        return False
    def release(self,*args):self.drag=False;self.queue_save();return True
    def save_hide(self,*args):self.queue_save();self.panel.hide()

    def queue_save(self):
        self.timer=None
        value=dict(self.saved_fields)
        value.update({'schema':'aura-face-zone-settings-1','board_boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
               'left_ratio':0.,'left_camera_ratio':self.left_camera_ratio,'right_ratio':self.ratio,'target_kind':'face','reference':'face_center',
               'frame_width':640,'frame_height':480,'mirror_horizontal':True,'viewport':list(VIEW),'updated_mono_ms':int(time.monotonic()*1000)})
        with self.condition:self.pending=value;self.condition.notify()
        return False

    def save_worker(self):
        while not self.closed.is_set():
            with self.condition:
                self.condition.wait_for(lambda:self.closed.is_set() or self.pending is not None)
                if self.closed.is_set():return
                value,self.pending=self.pending,None
            try:
                self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_name(self.path.name+'.editor-'+str(os.getpid()))
                with tmp.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush()
                os.chmod(tmp,0o600);os.replace(tmp,self.path)
                GLib.idle_add(self.status.set_text,'已保存左线 '+str(round(value['left_camera_ratio']*100))+'%、右线 '+str(round(image_ratio(value['right_ratio'])*100))+'%；只用人脸位置。')
            except Exception as exc:GLib.idle_add(self.status.set_text,'边界保存失败：'+type(exc).__name__)

    @staticmethod
    def get(opener,port,path):
        with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=.3) as response:return json.load(response)

    def command(self,kind):
        def send():
            try:
                base='http://127.0.0.1:8783';q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':kind}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(q,timeout=2) as r:json.load(r)
            except Exception:pass
        threading.Thread(target=send,daemon=True).start()

    def update(self,active,face,hint='人脸位置：未确认'):
        if active:
            if not self.active:self.line.show_all();self.left_line.show_all()
            self.place_line()
        else:self.line.hide();self.left_line.hide();self.panel.hide()
        if active:self.hint_label.set_text(hint);self.hint_window.show_all()
        else:self.hint_window.hide()
        self.active=active
        if not active or face is None:
            for window in self.faces:window.hide()
            return False
        x,y,w,h=face
        x=round(CONTENT[0]+x/640*CONTENT[2]);y=round(CONTENT[1]+y/480*CONTENT[3]);w=max(2,round(w/640*CONTENT[2]));h=max(2,round(h/480*CONTENT[3]))
        rectangles=((x,y,w,2),(x,y+h-2,w,2),(x,y,2,h),(x+w-2,y,2,h),(x+w//2-2,y+h//2-2,5,5))
        for window,(left,top,width,height) in zip(self.faces,rectangles):window.move(left,top);window.resize(width,height);window.show_all()
        return False

    def poll(self):
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));active=False;next_ui=0
        while not self.closed.wait(.1):
            face=None;hint='人脸位置：未确认';position='UNCONFIRMED';packet={}
            try:
                if time.monotonic()>=next_ui:
                    state=self.get(opener,8783,'/api/state');metric=state['ui_runtime'].get('preview_metrics') or {}
                    active=state.get('ui_page')=='vision' and metric.get('sink_active') and 'large' not in metric.get('active_outputs',[]);next_ui=time.monotonic()+.5
                if active:
                    packet=self.get(opener,8790,'/v1/motion/face/observation')
                    face,hint,position=face_position(packet,self.boot,int(time.monotonic()*1000),self.left_camera_ratio,image_ratio(self.ratio))
            except Exception:pass
            now=time.monotonic();source=(packet.get('source_frame_id'),packet.get('source_mono_ms'))
            if active and (source!=self.last_position_source or position!=self.last_position):
                self.position_counts[position]+=1
                if position!=self.last_position:self.position_events.append(dict(mono_ms=int(now*1000),position=position))
                self.last_position_source,self.last_position=source,position
            if now>=self.next_position_write:
                self.next_position_write=now+.3
                try:
                    value=dict(boot_id=self.boot,active=bool(active),position=position,hint=hint,box=face,
                        source_frame_id=packet.get('source_frame_id'),source_mono_ms=packet.get('source_mono_ms'),
                        updated_mono_ms=int(now*1000),counts=dict(self.position_counts),events=list(self.position_events),
                        controller_commands_sent=0)
                    path=self.path.parent/'face-zone-display-status.json';tmp=path.with_name(path.name+'.'+str(os.getpid()))
                    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)
                except OSError:pass
            GLib.idle_add(self.update,active,face,hint)


def main():
    p=argparse.ArgumentParser();p.add_argument('--settings',type=Path,required=True);args=p.parse_args()
    setup_font();Editor(args.settings);Gtk.main()

if __name__=='__main__':main()
