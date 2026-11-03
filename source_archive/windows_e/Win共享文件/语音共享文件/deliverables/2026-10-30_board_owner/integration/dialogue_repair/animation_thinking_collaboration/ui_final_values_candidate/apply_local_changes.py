"""Remove transient UI property overwrites; local candidate files only."""
import ast
from pathlib import Path

HERE=Path(__file__).resolve().parent


def once(source,before,after):
    if source.count(before)!=1:raise ValueError('Expected one anchor: '+before[:70])
    return source.replace(before,after)


def offset(lines,line,column):
    return sum(len(value) for value in lines[:line-1])+len(lines[line-1].encode('utf-8')[:column].decode('utf-8'))


def main():
    path=HERE/'candidate/aura/tools/board_avatar_gtk.py'
    source=path.read_text(encoding='utf-8')
    source=once(source,"'set_value': 'get_value'}","'set_value': 'get_value', 'set_editable': 'get_editable'}")
    lines=source.splitlines(keepends=True);edits=[]
    # Repeated button setters become local final-value assignments. Preserve
    # the exact original branch conditions and expressions.
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node,ast.FunctionDef) or node.name!='refresh_runtime':continue
        for expression in ast.walk(node):
            if not isinstance(expression,ast.Expr) or not isinstance(expression.value,ast.Call):continue
            call=expression.value
            if (not isinstance(call.func,ast.Attribute) or call.func.attr!='_ui_set' or len(call.args)!=3
                    or ast.get_source_segment(source,call.args[0])!='self.record_button'):continue
            method=ast.literal_eval(call.args[1])
            variable={'set_label':'record_button_label','set_sensitive':'record_button_sensitive',
                      'set_tooltip_text':'record_button_tooltip'}[method]
            edits.append((offset(lines,expression.lineno,expression.col_offset),
                offset(lines,expression.end_lineno,expression.end_col_offset),
                variable+' = ('+ast.get_source_segment(source,call.args[2])+')'))
    if len(edits)!=9:raise ValueError('Expected nine record-button writes')
    for start,end,value in sorted(edits,reverse=True):source=source[:start]+value+source[end:]
    marker='        preview_ref = snapshot.get(\'preview\') if snapshot else None\n'
    source=once(source,marker,
        "        self._ui_set(self.record_button,'set_label',record_button_label)\n"
        "        self._ui_set(self.record_button,'set_sensitive',record_button_sensitive)\n"
        "        self._ui_set(self.record_button,'set_tooltip_text',record_button_tooltip)\n"+marker)
    source=once(source,
        "            self._ui_set(self.controls[name], 'set_sensitive', bool(caps.get(name)) and not view['pending_count'])\n",
        "            if name != 'identity_enroll':\n"
        "                self._ui_set(self.controls[name], 'set_sensitive', bool(caps.get(name)) and not view['pending_count'])\n")
    # These three legacy labels are always replaced by project_business_ui in
    # production. Keep legacy output and active toast behavior unchanged.
    tree=ast.parse(source);lines=source.splitlines(keepends=True);edits=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.FunctionDef) or node.name!='refresh_runtime':continue
        for expression in ast.walk(node):
            if not isinstance(expression,ast.Expr) or not isinstance(expression.value,ast.Call):continue
            call=expression.value
            if not isinstance(call.func,ast.Attribute) or call.func.attr!='_ui_set' or len(call.args)!=3:continue
            widget=ast.get_source_segment(source,call.args[0])
            if widget not in ('self.mode_label','self.host_status_label','self.footer'):continue
            indent=' '*expression.col_offset
            condition="getattr(self,'board_business',None) is None"
            if widget=='self.footer':condition+=' or time.monotonic() < self.toast_until'
            old=''.join(lines[expression.lineno-1:expression.end_lineno])
            new=indent+'if '+condition+':\n'+''.join('    '+line for line in old.splitlines(keepends=True))
            edits.append((offset(lines,expression.lineno,0),offset(lines,expression.end_lineno+1,0),new))
    if len(edits)!=4:raise ValueError('Expected four overridden label writes')
    for start,end,value in sorted(edits,reverse=True):source=source[:start]+value+source[end:]
    source=once(source,'            project_business_ui(self,state)\n',
        "            project_business_ui(self,state)\n"
        "            state['ui_widget_writes']=dict(self._ui_widget_writes)\n")
    ast.parse(source);path.write_text(source,encoding='utf-8')
    path=HERE/'candidate/aura/tools/production_business_ui.py'
    source=path.read_text(encoding='utf-8')
    helper='''def _write_widget(stage, widget, method, value):
    """Use the stage's value guard; retain compatibility with other shells."""
    guarded = getattr(stage, '_ui_set', None)
    if guarded is None:
        getattr(widget, method)(value)
    else:
        guarded(widget, method, value)


'''
    source=once(source,'def project_business_ui(stage, state):\n',helper+'def project_business_ui(stage, state):\n')
    lines=source.splitlines(keepends=True);edits=[]
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node,ast.FunctionDef) or node.name!='project_business_ui':continue
        for expression in ast.walk(node):
            if not isinstance(expression,ast.Expr) or not isinstance(expression.value,ast.Call):continue
            call=expression.value
            if (not isinstance(call.func,ast.Attribute) or call.func.attr not in ('set_text','set_editable','set_sensitive')
                    or len(call.args)!=1):continue
            text='_write_widget(stage, '+ast.get_source_segment(source,call.func.value)+', '+repr(call.func.attr)+', '+ast.get_source_segment(source,call.args[0])+')'
            edits.append((offset(lines,call.lineno,call.col_offset),offset(lines,call.end_lineno,call.end_col_offset),text))
    if len(edits)!=6:raise ValueError('Expected six production setter call sites')
    for start,end,value in sorted(edits,reverse=True):source=source[:start]+value+source[end:]
    ast.parse(source);path.write_text(source,encoding='utf-8')
    print('Prepared two-source final-value UI candidate; no device operation')


if __name__=='__main__':main()
