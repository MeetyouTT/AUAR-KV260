"""Build opt-in patches against the fresh read-only source snapshot only.

Writes two reviewable candidate source files/manifest; no SSH, deployment,
service operation, credentials, models or data files are involved.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT/'fresh_source'
SOURCE = SNAPSHOT/'aura'
OUTPUT = ROOT/'gui_candidate'/'aura'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Fresh-source integration point changed: '+old[:80])
    return text.replace(old, new, 1)


def build():
    manifest = json.loads((SNAPSHOT/'manifest.json').read_text(encoding='utf-8'))
    files = []
    path = SOURCE/'tools/board_avatar_gtk.py'
    raw = path.read_bytes(); source_sha = hashlib.sha256(raw).hexdigest()
    if manifest['source_sha256'].get('tools/board_avatar_gtk.py') != source_sha:
        raise ValueError('Fresh GTK snapshot no longer matches the independently acquired manifest')
    # Pin from the independently acquired snapshot, never from stale main GUI.
    text = raw.decode('utf-8')
    text = replace_once(text,
        "        self.jobs = self.output = self.bridge = self.mixer = self.services = self.preview_output = self.transcriber = None",
        "        self.board_business = None\n        self.jobs = self.output = self.bridge = self.mixer = self.services = self.preview_output = self.transcriber = None")
    text = replace_once(text,
        "            if conversation_store.read()['enabled']:",
        "            if config.get('board_business',{}).get('enabled'):\n"
        "                if not streaming or not persistent:\n"
        "                    raise ValueError('Board business requires the existing persistent streaming player')\n"
        "                if config.get('portrait_offload',{}).get('enabled'):\n"
        "                    raise ValueError('Board business requires local rendering; no character substitution is implied')\n"
        "                from tools.board_business_gui import prepare_board_business\n"
        "                self.board_business=prepare_board_business(self,config['board_business'],AURA)\n"
        "                self.transcriber=self.board_business.jobs\n"
        "            elif conversation_store.read()['enabled']:")
    old = "            self.controller = AvatarRenderWorker(recording_type(visual_controller,transcriber=self.transcriber,**recording_options),"
    new = ("            if self.board_business is not None:\n"
           "                recording_options.update(self.board_business.recording_options(visual_controller))\n"
           "            recording=recording_type(visual_controller,transcriber=self.transcriber,**recording_options)\n"
           "            if self.board_business is not None:\n"
           "                self.board_business.bind_recording(recording)\n"
           "            self.controller = AvatarRenderWorker(recording,")
    text = replace_once(text, old, new)
    text = replace_once(text,
        "                self.transcriber.identity_snapshot=self.services.identity_snapshot",
        "                self.transcriber.identity_snapshot=self.services.identity_snapshot\n"
        "            if self.board_business is not None:\n"
        "                self.board_business.activate()")
    text = replace_once(text,
        "            self.controller = None\n        if self.native_video:",
        "            self.controller = None\n"
        "        if getattr(self,'board_business',None) is not None:\n"
        "            self.board_business.close()\n"
        "            self.board_business=None\n"
        "        if self.native_video:")
    ast.parse(text)
    for relative, original, updated in [('tools/board_avatar_gtk.py', raw, text.encode('utf-8'))]:
        dest = OUTPUT/relative; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(updated)
        files.append(dict(path=relative, source_sha256=hashlib.sha256(original).hexdigest(),
                          candidate_sha256=hashlib.sha256(updated).hexdigest(), bytes=len(updated)))
    profile = SOURCE/'tools/profile_selection_ui.py'
    raw = profile.read_bytes(); text = raw.decode('utf-8')
    if manifest['source_sha256'].get('tools/profile_selection_ui.py') != hashlib.sha256(raw).hexdigest():
        raise ValueError('Fresh profile snapshot no longer matches the acquired manifest')
    text = replace_once(text, 'def profile_dialog(stage):',
        "def profile_dialog(stage):\n"
        "    if getattr(stage,'board_business',None) is not None:\n"
        "        from tools.board_profile_dialog import local_board_profile_dialog\n"
        "        return local_board_profile_dialog(stage)")
    text = replace_once(text, '请先在Windows授权', '请先在板端本地授权')
    ast.parse(text)
    dest=OUTPUT/'tools/profile_selection_ui.py'; dest.write_bytes(text.encode('utf-8'))
    files.append(dict(path='tools/profile_selection_ui.py', source_sha256=hashlib.sha256(raw).hexdigest(),
                      candidate_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(), bytes=dest.stat().st_size))
    result = dict(status='CANDIDATE_BUILT_NOT_DEPLOYED', source_manifest=manifest,
        entrypoints=files, production_config_changed=False, character_replaced=False,
        note='New opt-in board_business branch. Original defaults retain prior behavior; real cutover requires fresh source/pins and combined validation.')
    (ROOT/'gui_candidate_manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(status=result['status'], files=files), ensure_ascii=False))


if __name__ == '__main__':
    build()
