"""Native GTK fixture acceptance. Does not use a camera, model or real identity."""
from pathlib import Path
import json
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0, str(ROOT))
from tools.preview_board_touch import LayoutPreview
from tools.board_screen_capture import capture
from board.identity.live import IdentityService
from board.identity.store import IdentityStore
from board.interaction.ui_contract import millis
from board.vision.ui_camera_service import CameraState

OUTPUT = Path('/home/ghmd/aura-identity-ui-20261018/identity-ui')
OUTPUT.mkdir(exist_ok=True)


def main():
    preview = LayoutPreview()
    # Dialog tests use the placeholder; video geometry is checked separately.
    preview.example = False
    stage, Gtk, GLib = preview.stage, preview.gtk, preview.glib
    checks = []
    responses = []
    errors = []
    with tempfile.TemporaryDirectory(prefix='aura-native-identity-') as temp:
        state = CameraState('preview-only', 'fixture-identity')
        store = IdentityStore(Path(temp)/'test.sqlite3', 'synthetic-fixture', 4, .85, .1)
        service = state.identity = IdentityService(store, lambda: None, state.identity_target, lock=state.lock)
        service.ready = True
        generation = [1]
        def frame():
            now = millis();state.captured(now)
            observation = {'target_id': 1, 'tracks': [{'track_id': 1, 'generation': generation[0],
                'visible': True, 'confirmed': True, 'box': (0, 0, 100, 200)}]}
            state.observed(1, now, observation, 0.)
            return observation
        class Extractor:
            def extract(self, *_):return (1, 0, 0, 0), ''
        def infer():
            obs = frame();service.offer(None, 1, millis(), obs, state.camera_epoch)
            packet, service.pending = service.pending, None
            service.process(packet, Extractor())
        infer()
        def view():
            frame()
            if service.result:service.result['stamp'] = millis()
            snapshot = state.snapshot()
            snapshot['source_kind'] = 'fixture'
            snapshot['preview'] = preview.reference
            return {'snapshot': snapshot, 'link': 'READY', 'connection': stage.connection_store.read(),
                    'error': '', 'preview': None, 'results': responses, 'pending_count': 0,
                    'ui_epoch': 'fixture-ui', 'ui_generation': 0}
        counter = [0]
        def submit(action, params):
            counter[0] += 1;snapshot = state.snapshot();now = millis()
            command = {'protocol_version': 'aura-ui-1', 'board_boot_id': 'preview-only',
                'service_epoch': state.epoch, 'command_id': 'native-'+str(counter[0]), 'ui_epoch': 'fixture-ui',
                'ui_generation': 0, 'snapshot_sequence': snapshot['sequence'], 'context': snapshot['context'],
                'issued_mono_ms': now, 'deadline_mono_ms': now+2500, 'action': action, 'params': params}
            ack = state.command(command)
            responses.append(dict(ack, action=action))
            return {'ok': True, 'queued': True, 'message': ack['detail']}
        stage.services = SimpleNamespace(read=view, submit=submit)
        def dispatch(data):
            if data.get('type') == 'service_dialog':
                return stage.command(data)
            return preview.command(data)
        stage.native = dispatch
        stage.show_page('vision');preview.refresh();preview.drain()
        def snapshot(name):
            preview.refresh();preview.drain()
            capture(OUTPUT/(name+'.png'))
        snapshot('unknown')
        assert stage.controls['vision_identity'].get_sensitive()
        checks.append('identity_management_on_presentation_page')

        def descendants(widget):
            yield widget
            if hasattr(widget, 'get_children'):
                for child in widget.get_children():yield from descendants(child)
        def dialog_step(kind):
            dialogs = [w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.Dialog) and w.get_visible()]
            if not dialogs:return True
            dialog = dialogs[-1]
            widgets = list(descendants(dialog))
            try:
                if kind == 'choose_enroll':
                    button = next(w for w in widgets if isinstance(w, Gtk.Button) and w.get_label() == '登记当前对象')
                    button.clicked()
                elif kind == 'name':
                    entry = next(w for w in widgets if isinstance(w, Gtk.Entry))
                    entry.set_text('预览访客');dialog.response(Gtk.ResponseType.OK)
                elif kind in ('confirm_enroll', 'cancel_delete', 'confirm_delete'):
                    assert isinstance(dialog, Gtk.MessageDialog)
                    if kind == 'confirm_enroll':
                        assert '保存人脸特征' in dialog.get_property('secondary-text')
                    dialog.response(Gtk.ResponseType.CANCEL if kind == 'cancel_delete' else Gtk.ResponseType.OK)
                elif kind == 'choose_delete':
                    button = next(w for w in widgets if isinstance(w, Gtk.Button) and w.get_label() == '预览访客')
                    button.clicked()
                checks.append('native_dialog_'+kind)
            except (StopIteration, AssertionError) as exc:
                errors.append(kind+': '+repr(exc));dialog.response(Gtk.ResponseType.CANCEL)
            return False
        try:
            GLib.timeout_add(100, dialog_step, 'choose_enroll')
            GLib.timeout_add(220, dialog_step, 'name')
            GLib.timeout_add(340, dialog_step, 'confirm_enroll')
            stage.controls['vision_identity'].clicked()
            preview.refresh();preview.drain()
            assert store.people()[0]['display_name'] == '预览访客'
            assert stage.insight_labels['identity'].get_text() == '预览访客'
            snapshot('known')
            GLib.timeout_add(100, dialog_step, 'choose_delete')
            GLib.timeout_add(220, dialog_step, 'cancel_delete')
            stage.service_dialog('identity_delete')
            assert len(store.people()) == 1
            checks.append('cancel_delete_keeps_identity')
            GLib.timeout_add(100, dialog_step, 'choose_delete')
            GLib.timeout_add(220, dialog_step, 'confirm_delete')
            stage.service_dialog('identity_delete')
            assert not store.people()
            infer();snapshot('deleted_unknown')
            assert not state.snapshot()['modules']['identity']['display_name']
            checks.append('committed_delete_clears_ui_identity')
            assert not errors, errors
            result = {'status': 'PASS', 'scope': 'HOST_NATIVE_GTK_WITH_SYNTHETIC_EMBEDDINGS',
                      'board_deployed': False, 'checks': checks, 'screenshots': ['unknown.png', 'known.png', 'deleted_unknown.png']}
            (OUTPUT/'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps(result, ensure_ascii=False))
        finally:
            service.close()
            preview.close()


if __name__ == '__main__':main()
