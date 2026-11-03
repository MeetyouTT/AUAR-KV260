"""Build an offline follow-up from the accepted layout source; never deploy it."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
base=(HERE/'editor_layout_only/face_zone_editor.py').read_bytes()
assert hashlib.sha256(base).hexdigest()=='6d0e979034d051bd19addc4876297d80d05ff9cb41febcb5b6824b66b87a663c'
text=base.decode('utf-8')


def replace(before,after):
    global text
    assert text.count(before)==1, before
    text=text.replace(before,after)


replace('        self.saved_fields={};self.left_camera_ratio=.1\n',
'''        self.saved_fields={};self.left_camera_ratio=.1
        self._display_lock=threading.Lock();self._display_pending=None;self._display_idle=None;self._display_generation=0
        self._face_expiry_source=None;self._face_expiry_token=0
''')
replace('        self.visibility_channel=None;self.poll_wakeup=threading.Event()\n',
'''        self.visibility_channel=None;self.poll_wakeup=threading.Event()
        self.hint_window.connect('destroy',self.close)
''')

methods='''    def enqueue_display(self,active,face,hint,packet,preview,visibility_revision):
        # Separate from the original settings save queue and debounce timer.
        with self._display_lock:
            if self.closed.is_set():return
            self._display_pending=(active,face,hint,packet,preview,visibility_revision)
            if self._display_idle is None:
                self._display_idle=GLib.idle_add(self._flush_display,self._display_generation)

    def _flush_display(self,generation):
        with self._display_lock:
            if generation!=self._display_generation:return False
            value=self._display_pending;self._display_pending=None;self._display_idle=None
        if value is not None and not self.closed.is_set():self.update(*value)
        return False

    def _clear_display_pending(self):
        with self._display_lock:
            self._display_generation+=1
            source=self._display_idle;self._display_idle=None;self._display_pending=None
        if source is not None:GLib.source_remove(source)

    def _cancel_face_expiry(self):
        self._face_expiry_token+=1
        if self._face_expiry_source is not None:GLib.source_remove(self._face_expiry_source)
        self._face_expiry_source=None

    def _expire_face(self,token,deadline,visibility_revision):
        # A dispatched old timeout must not clear a newer timer or face.
        if self.closed.is_set() or token!=self._face_expiry_token:return False
        self._face_expiry_source=None
        same_page=(self.visibility_channel is None or visibility_revision==self.visibility_channel.gate.snapshot()['revision'])
        now=int(time.monotonic()*1000)
        if same_page and now<deadline:
            self._face_expiry_source=GLib.timeout_add(max(1,deadline-now),self._expire_face,token,deadline,visibility_revision)
            return False
        self._face_expiry_token+=1
        for window in self.faces:window.hide()
        self.hint_label.set_text('人脸位置：未确认')
        return False

    def close(self,*args):
        if self.closed.is_set():return
        self.closed.set();self._clear_display_pending();self._cancel_face_expiry();self.poll_wakeup.set()
        with self.condition:self.condition.notify_all()
        if self.visibility_channel is not None:self.visibility_channel.close()

'''
needle="    def update(self,active,face,hint='人脸位置：未确认'):\n"
replace(needle,methods+"    def update(self,active,face,hint='人脸位置：未确认',packet=None,preview=None,visibility_revision=None):\n")
replace('''        if self.visibility_channel is not None:
            active=bool(active and self.visibility_channel.gate.allows_overlay())
        if active:
''','''        if self.closed.is_set():return False
        if self.visibility_channel is not None:
            if visibility_revision is not None and visibility_revision!=self.visibility_channel.gate.snapshot()['revision']:return False
            active=bool(active and self.visibility_channel.gate.allows_overlay())
        self._cancel_face_expiry();deadline=None
        if active and face is not None:
            now=int(time.monotonic()*1000)
            current,_,_=face_position(packet,self.boot,now,self.left_camera_ratio,image_ratio(self.ratio))
            reference=preview.get('frame_reference') if isinstance(preview,dict) else None
            valid_preview=(isinstance(reference,dict) and isinstance(packet,dict) and preview.get('frame_visible') is True
                and isinstance(reference.get('camera_epoch'),str) and bool(reference['camera_epoch'])
                and reference['camera_epoch']==(packet or {}).get('camera_epoch')
                and type(reference.get('frame_id')) is int and reference['frame_id']>=0
                and type(reference.get('captured_mono_ms')) is int and 0<=reference['captured_mono_ms']<=now)
            if current!=face or not valid_preview:face=None;hint='人脸位置：未确认'
            else:deadline=min(packet['source_mono_ms']+250,packet['face_detection_mono_ms']+500)
        if active:
''')
replace('''        for window,(left,top,width,height) in zip(self.faces,rectangles):window.move(left,top);window.resize(width,height);window.show_all()
        return False
''','''        for window,(left,top,width,height) in zip(self.faces,rectangles):window.move(left,top);window.resize(width,height);window.show_all()
        self._face_expiry_source=GLib.timeout_add(max(1,deadline-int(time.monotonic()*1000)),self._expire_face,
            self._face_expiry_token,deadline,visibility_revision)
        return False
''')
replace('''        if page!='vision':
            self.drag=False
            self.update(False,None)
''','''        if page!='vision':
            self.drag=False;self._clear_display_pending()
            self.update(False,None)
''')
replace('active=False;next_ui=0;following={};page_revision=-1\n',
        'active=False;next_ui=0;following={};preview={};page_revision=-1\n')
replace("            face=None;hint='人脸位置：未确认';position='UNCONFIRMED';packet={}\n",
        "            visibility_revision=page_revision if self.visibility_channel is not None else None\n            face=None;hint='人脸位置：未确认';position='UNCONFIRMED';packet={}\n")
replace("                    active=state.get('ui_page')=='vision' and metric.get('sink_active') and 'large' not in metric.get('active_outputs',[]);next_ui=time.monotonic()+.5\n",
        "                    active=state.get('ui_page')=='vision' and metric.get('sink_active') and 'large' not in metric.get('active_outputs',[]);preview=metric;next_ui=time.monotonic()+.5\n")
replace('            GLib.idle_add(self.update,active,face,hint)\n',
        '            self.enqueue_display(active,face,hint,packet,preview,visibility_revision)\n')
replace('    setup_font();editor=Editor(args.settings);editor.install_page_visibility();Gtk.main()\n',
'''    setup_font();editor=Editor(args.settings);editor.install_page_visibility()
    try:Gtk.main()
    finally:editor.close()
''')

after=text.encode('utf-8');tree=ast.parse(after);before_tree=ast.parse(base)
protected_functions=('image_ratio','widget_ratio','face_position','setup_font')
before_class=next(n for n in before_tree.body if isinstance(n,ast.ClassDef) and n.name=='Editor')
after_class=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Editor')
protected_methods=('bar','place_line','set_ratio','changed','press','motion','release','save_hide','queue_save','save_worker','get','command','install_page_visibility')
for scope_a,scope_b,names in ((before_tree.body,tree.body,protected_functions),(before_class.body,after_class.body,protected_methods)):
    for name in names:
        a=next(n for n in scope_a if isinstance(n,ast.FunctionDef) and n.name==name)
        b=next(n for n in scope_b if isinstance(n,ast.FunctionDef) and n.name==name)
        assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),name
assert 'self.hint_window.move(8,420)' in text
dest=HERE/'editor_freshness_v2';dest.mkdir(exist_ok=True)
assert not (dest/'face_zone_editor.py').exists(), 'Keep versioned candidates immutable'
(dest/'face_zone_editor.py').write_bytes(after)
(dest/'face_zone_editor.diff').write_text(''.join(difflib.unified_diff(base.decode().splitlines(True),text.splitlines(True),fromfile='accepted-layout/face_zone_editor.py',tofile='offline-freshness-v2/face_zone_editor.py')),encoding='utf-8')
manifest=dict(status='OFFLINE_EDITOR_FRESHNESS_V2_NOT_DEPLOYED',before_sha256=hashlib.sha256(base).hexdigest(),
    after_sha256=hashlib.sha256(after).hexdigest(),hint_geometry_preserved=[8,420,400,30],
    original_face_source250_anchor500_checks_and_geometry_and_motion_and_saving_functions_unchanged=True,
    new_behavior=['Recheck original face_position in the actual GUI callback.',
        'Independent timeout at min(source+250,anchor+500) hides five face windows and sets unconfirmed.',
        'Latest pending display update coalesced; page revision/generation prevents stale callbacks reviving old faces.',
        'Old timeout token cannot erase the current timeout ID or face; close clears only display sources.'],
    preview_gate='Visible preview with a valid same-camera-epoch reference; no strict frame ID equality or new preview-age threshold.',
    published_GTK_or_editor_candidates_or_board_modified=False,validation_pending=True)
(dest/'CANDIDATE.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest))
