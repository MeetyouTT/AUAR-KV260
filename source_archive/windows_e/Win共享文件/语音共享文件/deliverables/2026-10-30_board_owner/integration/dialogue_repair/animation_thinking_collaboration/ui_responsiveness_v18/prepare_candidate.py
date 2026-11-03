"""Build a two-source candidate against the verified v18 mapping, locally."""
import ast
import hashlib
import json
from pathlib import Path
import shutil


HERE=Path(__file__).resolve().parent
ANIM=HERE.parent
REPAIR=ANIM.parent

HELPER='''    def _ui_set(self, widget, method, value):
        """Avoid a GTK mutation when its current value already matches."""
        getter = _UI_WIDGET_GETTERS[method]
        stats = getattr(self, '_ui_widget_writes', None)
        if stats is None:
            stats = self._ui_widget_writes = dict(applied=0, skipped=0)
        if getattr(widget, getter)() == value:
            stats['skipped'] += 1
            return False
        getattr(widget, method)(value)
        stats['applied'] += 1
        return True

'''
GETTERS=dict(set_text='get_text',set_label='get_label',set_sensitive='get_sensitive',
    set_visible='get_visible',set_tooltip_text='get_tooltip_text',set_value='get_value')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(source, before, after):
    if source.count(before)!=1:
        raise ValueError('Expected one source anchor: '+before[:60])
    return source.replace(before,after)


def method_source(source,name):
    methods=[node for node in ast.walk(ast.parse(source)) if isinstance(node,ast.FunctionDef) and node.name==name]
    if len(methods)!=1:raise ValueError(name)
    node=methods[0];lines=source.splitlines(keepends=True)
    return ''.join(lines[node.lineno-1:node.end_lineno])


def guard_setters(source):
    lines=source.splitlines(keepends=True)
    offsets=[0]
    for line in lines:offsets.append(offsets[-1]+len(line))
    edits=[]
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node,ast.FunctionDef) or node.name not in ('refresh_runtime','refresh_settings'):
            continue
        for call in ast.walk(node):
            if (not isinstance(call,ast.Call) or not isinstance(call.func,ast.Attribute)
                    or call.func.attr not in GETTERS or len(call.args)!=1 or call.keywords):
                continue
            target=call.func.value
            if isinstance(target,ast.Call):continue  # TextBuffer has a different get_text signature.
            # AST columns are UTF-8 byte positions; convert each position safely.
            start=offsets[call.lineno-1]+len(lines[call.lineno-1].encode('utf-8')[:call.col_offset].decode('utf-8'))
            end=offsets[call.end_lineno-1]+len(lines[call.end_lineno-1].encode('utf-8')[:call.end_col_offset].decode('utf-8'))
            text='self._ui_set('+ast.get_source_segment(source,target)+', '+repr(call.func.attr)+', '+ast.get_source_segment(source,call.args[0])+')'
            edits.append((start,end,text))
    for start,end,text in sorted(edits,reverse=True):source=source[:start]+text+source[end:]
    return source,len(edits)


def main():
    mapping_path=REPAIR/'release_v18_candidate/v18_evidence/source_mapping.json'
    mapping=json.loads(mapping_path.read_text(encoding='utf-8'))
    if mapping['startup_sha256']!='12a26c81167ecee7293d0d9be77ec7834894d413f07bab6d8a27e4c8cdfe0392':
        raise ValueError('Requires fresh baseline review')
    sources={
        'tools/board_avatar_gtk.py':ANIM/'frame_rate_24_candidate/ui_timing_probe/candidate/aura/tools/board_avatar_gtk.py',
        'tools/x11_display_activity.py':ANIM/'runtime_v16/tools/x11_display_activity.py'}
    for relative,path in sources.items():
        if sha(path)!=mapping['component_pins'][relative]:raise ValueError('Baseline pin differs: '+relative)
        for name in ('before','candidate'):
            target=HERE/name/'aura'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():raise ValueError('Candidate already exists')
            shutil.copyfile(path,target)
    gtk=HERE/'candidate/aura/tools/board_avatar_gtk.py'
    source=gtk.read_text(encoding='utf-8')
    source,count=guard_setters(source)
    source=replace_once(source,'AURA = Path(__file__).resolve().parents[1]',
        '_UI_WIDGET_GETTERS = '+repr(GETTERS)+'\n\nAURA = Path(__file__).resolve().parents[1]')
    source=replace_once(source,'    def refresh_runtime(self, state, settings_text):\n',
        HELPER+'    def refresh_runtime(self, state, settings_text):\n')
    old=method_source(source,'refresh_settings');new=old
    new=replace_once(new,'        mix = self.mixer.read()\n',
        "        settings_started=time.perf_counter();settings_cpu=time.thread_time()\n"
        "        self._ui_widget_writes=dict(applied=0,skipped=0)\n"
        "        mix = self.mixer.read()\n"
        "        mixer_done=time.perf_counter()\n")
    new=replace_once(new,"        if mix['pending']:\n","        scan_done=time.perf_counter()\n        if mix['pending']:\n")
    new=replace_once(new,'        return text\n',
        "        ended=time.perf_counter()\n"
        "        state['ui_settings_timings_ms']=dict(mixer_read=(mixer_done-settings_started)*1000,\n"
        "            device_scan=(scan_done-mixer_done)*1000,widgets=(ended-scan_done)*1000,\n"
        "            total=(ended-settings_started)*1000,thread_cpu=(time.thread_time()-settings_cpu)*1000)\n"
        "        return text\n")
    source=replace_once(source,old,new)
    old=method_source(source,'refresh_runtime');new=old
    new=replace_once(new,'        view = self.services.read()\n',
        "        runtime_started=time.perf_counter();runtime_cpu=time.thread_time()\n"
        "        view = self.services.read()\n        services_done=time.perf_counter()\n")
    marker="        modules = snapshot['modules'] if snapshot else {}\n"
    new=replace_once(new,marker,"        preview_done=time.perf_counter()\n"+marker)
    marker='        self.refresh_voice_face_dialog(transcription)\n'
    new=replace_once(new,'        transcription = state.get(\'local_transcription\',{})\n',
        "        wake_done=time.perf_counter()\n        transcription = state.get('local_transcription',{})\n")
    new=replace_once(new,marker,marker+'        dialog_done=time.perf_counter()\n')
    new += ("        ended=time.perf_counter()\n"
        "        state['ui_runtime_timings_ms']=dict(services_read=(services_done-runtime_started)*1000,\n"
        "            preview_read=(preview_done-services_done)*1000,display_activity=(wake_done-preview_done)*1000,\n"
        "            voice_dialog=(dialog_done-wake_done)*1000,widgets=(ended-dialog_done)*1000,\n"
        "            total=(ended-runtime_started)*1000,thread_cpu=(time.thread_time()-runtime_cpu)*1000)\n"
        "        state['ui_widget_writes']=dict(self._ui_widget_writes)\n")
    source=replace_once(source,old,new)
    old=method_source(source,'tick');new=old
    new=replace_once(new,'        started = time.perf_counter()\n',
        "        started = time.perf_counter()\n        callback_cpu=time.thread_time()\n"
        "        refreshed=False;publish_started=None;publish_ms=0.;callback_succeeded=False\n")
    new=replace_once(new,'            state = packet[\'state\']\n',
        "            refreshed=True\n            state = packet['state']\n"
        "            state['ui_callback_previous']=dict(getattr(self,'ui_callback_previous',{}))\n")
    new=replace_once(new,"            self.bridge.publish(state,packet['jpeg'])\n",
        "            publish_started=time.perf_counter()\n"
        "            self.bridge.publish(state,packet['jpeg'])\n"
        "            publish_ms=(time.perf_counter()-publish_started)*1000\n"
        "            callback_succeeded=True\n")
    marker='        return True\n'
    if not new.endswith(marker):raise ValueError('Tick return anchor')
    new=new[:-len(marker)]+("        finally:\n"
        "            if refreshed:\n"
        "                finished=time.perf_counter()\n"
        "                if publish_started is not None and not callback_succeeded:\n"
        "                    publish_ms=(finished-publish_started)*1000\n"
        "                self.ui_callback_previous=dict(wall_ms=(finished-started)*1000,\n"
        "                    thread_cpu_ms=(time.thread_time()-callback_cpu)*1000,publish_ms=publish_ms,\n"
        "                    completed_mono=time.monotonic(),succeeded=callback_succeeded,\n"
        "                    sequence=getattr(self,'ui_callback_previous',{}).get('sequence',0)+1)\n"
        "        return True\n")
    source=replace_once(source,old,new)
    ast.parse(source);gtk.write_text(source,encoding='utf-8',newline='\n')
    result=dict(schema='aura.ui-responsiveness-baseline.v1',startup_sha256=mapping['startup_sha256'],
        source_manifest_sha256=mapping['source_manifest_sha256'],source_mapping_sha256=sha(mapping_path),
        before_pins={name:sha(HERE/'before/aura'/name) for name in sources},
        guarded_widget_setters=count,native_or_fps_changed=False,threads_or_timers_added=False,
        audio_ack_or_business_files_changed=False,production_modified=False,device_access=False)
    (HERE/'BASELINE.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
