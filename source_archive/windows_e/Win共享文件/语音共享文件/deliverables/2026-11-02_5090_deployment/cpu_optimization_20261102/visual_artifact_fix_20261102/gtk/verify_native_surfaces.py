"""Pure AST/mock verification; never imports GTK or opens a display/device."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import types

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2]
source = OUT / 'other_components_20261102/live_enrollment_20261102/voice_conversation_address_20261102/candidate_runtime/tools/board_avatar_gtk.py'
candidate = HERE / 'tools/board_avatar_gtk.py'
before, after = source.read_bytes(), candidate.read_bytes()
assert hashlib.sha256(before).hexdigest() == '5e5c492832fc1273d45fa25d0ec692b47c9ffa4b6c6d46e42f176e842b50d70c'
assert hashlib.sha256(after).hexdigest() == 'd3c3d18aad2afdd02e25c5619befc67cfdd3fd8a7ef9f8713b5403a88c9a7bc5'
old_tree, new_tree = ast.parse(before), ast.parse(after)
surfaces = ('preview_image', 'large_preview')
settings = {'set_app_paintable': True, 'set_double_buffered': False}


def is_setting(node):
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    method = call.func
    return (isinstance(method, ast.Attribute) and method.attr in settings and
            isinstance(method.value, ast.Attribute) and method.value.attr in surfaces and
            isinstance(method.value.value, ast.Name) and method.value.value.id == 'self')


added = sorted((node for node in ast.walk(new_tree) if is_setting(node)), key=lambda node: node.lineno)
assert len(added) == 4
assert not any(is_setting(node) for node in ast.walk(old_tree))
for node in added:
    call = node.value
    assert len(call.args) == 1 and not call.keywords and isinstance(call.args[0], ast.Constant)
    assert call.args[0].value is settings[call.func.attr]


class RemoveSettings(ast.NodeTransformer):
    def visit_Expr(self, node):
        return None if is_setting(node) else self.generic_visit(node)


assert ast.dump(old_tree, include_attributes=False) == ast.dump(RemoveSettings().visit(copy.deepcopy(new_tree)), include_attributes=False)


class Surface:
    def __init__(self):
        self.calls = []

    def set_app_paintable(self, value):
        self.calls.append(('set_app_paintable', value))

    def set_double_buffered(self, value):
        self.calls.append(('set_double_buffered', value))


owner = types.SimpleNamespace(**{name: Surface() for name in surfaces})
exec(compile(ast.Module(body=copy.deepcopy(added), type_ignores=[]), '<exact-added-surface-settings>', 'exec'), {'self': owner})
for name in surfaces:
    assert getattr(owner, name).calls == [('set_app_paintable', True), ('set_double_buffered', False)]
preview = OUT / 'cpu_optimization_20261102/gtk/v2/candidate/tools/board_camera_preview.py'
services = OUT / 'cpu_optimization_20261102/gtk/v2/candidate/board/interaction/ui_services.py'
assert hashlib.sha256(preview.read_bytes()).hexdigest() == '67d6c0f2b24ea97e20fdcc7b3383b6444269a6e26f5deb566f2b88746b7daf9b'
assert hashlib.sha256(services.read_bytes()).hexdigest() == 'e4dedf9b3d56d22d9eb93de1e96ad1a69870d553ea50f7dd5082b21e19f381c9'
report = {'schema': 'aura-native-preview-surface-local-check-1', 'passed': True,
          'candidate_sha256': hashlib.sha256(after).hexdigest(), 'exact_surfaces': list(surfaces),
          'surface_calls': {name: getattr(owner, name).calls for name in surfaces},
          'entire_original_AST_unchanged_after_removing_four_new_settings': True,
          'original_map_unmap_attach_mapping_and_all_other_GTK_logic_unchanged': True,
          'preview_and_ui_services_bytes_unchanged': True,
          'same_original_250ms_guard_and_frame_delivery': True,
          'no_new_mirror_alpha_Pixbuf_overlay_bbox_or_frame_queue': True,
          'GTK_GStreamer_display_device_or_model_loaded': False,
          'physical_rendering_or_root_cause_verified': False}
with (HERE / 'NATIVE_SURFACE_LOCAL_CHECK.json').open('x', encoding='utf-8') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
print(json.dumps(report))
