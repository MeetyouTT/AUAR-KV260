"""Local position-only edit for the original external face-position popup.

No device access, service control, or live source write occurs here. The actual
source bytes must be obtained in the later explicitly idle layout window.
"""
import ast
import copy
import hashlib

ORIGINAL_SHA = '6a8bce7270534bb3b0f71dff657eac5da92b46855fdb7c9748a63b678be8ede4'

def prepare(raw, *, new_x=None, new_y=None):
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_SHA, 'Actual external editor source changed; inspect before adapting'
    tree = ast.parse(raw)
    views = [n for n in tree.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'VIEW' for t in n.targets)]
    assert len(views) == 1
    viewport = ast.literal_eval(views[0].value)
    assert isinstance(viewport, tuple) and len(viewport) == 4 and all(type(v) is int for v in viewport)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == 'move'
             and isinstance(n.func.value, ast.Attribute) and n.func.value.attr == 'hint_window'
             and isinstance(n.func.value.value, ast.Name) and n.func.value.value.id == 'self']
    assert len(calls) == 1 and len(calls[0].args) == 2, 'Need the sole face-position popup placement call'
    x, y = calls[0].args
    assert isinstance(x, ast.Constant) and x.value == 92
    assert isinstance(y, ast.Constant) and y.value == 78
    lower_y = viewport[1] + viewport[3] + 8 if new_y is None else new_y
    lower_x = x.value if new_x is None else new_x
    assert type(lower_x) is int and type(lower_y) is int
    assert lower_y > 78
    lines = raw.splitlines(keepends=True)
    edits = []
    for node, value in ((x, lower_x), (y, lower_y)):
        start = sum(map(len, lines[:node.lineno-1])) + node.col_offset
        end = sum(map(len, lines[:node.end_lineno-1])) + node.end_col_offset
        edits.append((start, end, str(value).encode('ascii')))
    changed = raw
    for start,end,value in sorted(edits, reverse=True): changed = changed[:start] + value + changed[end:]
    after = ast.parse(changed)
    a, b = copy.deepcopy(tree), copy.deepcopy(after)
    for candidate in (a, b):
        matching = [n for n in ast.walk(candidate) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == 'move'
                    and isinstance(n.func.value, ast.Attribute) and n.func.value.attr == 'hint_window'
                    and isinstance(n.func.value.value, ast.Name) and n.func.value.value.id == 'self']
        assert len(matching) == 1
        matching[0].args = [ast.Constant(value=0), ast.Constant(value=0)]
    assert ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)
    return changed, dict(before_sha256=ORIGINAL_SHA, after_sha256=hashlib.sha256(changed).hexdigest(),
                         changed_node='sole self.hint_window.move position arguments', old_x=92, new_x=lower_x, old_y=78, new_y=lower_y,
                         viewport=list(viewport), viewport_bottom=viewport[1]+viewport[3], gap_pixels=8,
                         size_style_tracking_logic_and_all_other_AST_unchanged=True,
                         actual_device_apply_or_reload=False)
