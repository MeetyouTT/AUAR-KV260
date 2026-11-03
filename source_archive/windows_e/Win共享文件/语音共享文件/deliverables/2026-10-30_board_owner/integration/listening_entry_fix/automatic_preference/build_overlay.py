"""Build a pinned two-file production overlay; no board or service access."""
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'source_before' / 'aura'
EXPECTED_GTK = '5ab20a5b86a6982b75447933ce87e9be5b96cb5cc560fa1026c69b574f070fc5'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Exact GTK source anchor changed')
    return text.replace(before, after, 1)


def build():
    path = BASE / 'tools' / 'board_avatar_gtk.py'
    raw = path.read_bytes()
    if sha(raw) != EXPECTED_GTK:
        raise ValueError('Current e345 GTK source pin mismatch')
    text = raw.decode('utf-8')
    text = replace_once(text,
        "            if self.character_pair is not None and config.get('handsfree_dialogue'):\n"
        "                from tools.yuki_business_candidate import CandidateMonitorChoice\n"
        "                recording_options['monitor_settings']=CandidateMonitorChoice(self.character_pair)\n",
        "            if self.character_pair is not None and config.get('handsfree_dialogue'):\n"
        "                if self.board_business is not None and self.board_business.runtime.config.data_origin == 'board':\n"
        "                    from tools.production_listening import ProductionMonitorChoice\n"
        "                    recording_options['monitor_settings']=ProductionMonitorChoice(self.board_business.runtime.config.private_root)\n"
        "                else:\n"
        "                    from tools.yuki_business_candidate import CandidateMonitorChoice\n"
        "                    recording_options['monitor_settings']=CandidateMonitorChoice(self.character_pair)\n")
    text = replace_once(text,
        "                self.board_business.bind_recording(recording)\n"
        "                from tools.production_memory_presentation import bind_presentation\n",
        "                self.board_business.bind_recording(recording)\n"
        "                if config.get('handsfree_dialogue') and self.board_business.runtime.config.data_origin == 'board':\n"
        "                    from tools.production_listening import bind_automatic_listening\n"
        "                    bind_automatic_listening(recording,self.board_business,self.character_pair)\n"
        "                from tools.production_memory_presentation import bind_presentation\n")
    text = replace_once(text,
        "            self.record_button.set_label('结束并暂停' if handsfree.get('conversation_entered') else\n"
        "                                         '暂停免点击' if handsfree.get('enabled') else '恢复免点击')\n",
        "            self.record_button.set_label('暂停聆听' if handsfree.get('enabled') else '开始聆听')\n")
    text = replace_once(text,
        "            self.record_button.set_tooltip_text('暂停会关闭麦克风，并保持暂停直到再次开启')\n",
        "            self.record_button.set_tooltip_text('服务就绪后自动聆听；暂停会关闭麦克风，并记住暂停选择')\n")
    output = ROOT / 'after' / 'aura' / 'tools' / 'board_avatar_gtk.py'
    output.write_bytes(text.encode('utf-8'))
    files = {}
    for relative in ('tools/board_avatar_gtk.py', 'tools/production_listening.py'):
        data = (ROOT / 'after' / 'aura' / relative).read_bytes()
        files['aura/' + relative] = dict(sha256=sha(data), bytes=len(data),
            before_sha256=EXPECTED_GTK if relative.endswith('board_avatar_gtk.py') else None)
    manifest = dict(schema='aura.production-listening-overlay.v1',
                    base_startup_sha256='e34590df7ecd4f74046671c9458edd48ede45d1474b5fbeba63481edd4cb8759',
                    files=files, hardware_executed=False)
    encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    (ROOT / 'overlay_manifest.json').write_bytes(encoded)
    with zipfile.ZipFile(ROOT / 'production_listening.overlay.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(files):
            info = zipfile.ZipInfo(relative, (2026, 10, 30, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (ROOT / 'after' / relative).read_bytes())
    (ROOT / 'extra_source_map.json').write_text(json.dumps({
        relative: str(ROOT / 'after' / relative) for relative in sorted(files)},
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(files=files, manifest_sha256=sha(encoded),
                         zip_sha256=sha((ROOT / 'production_listening.overlay.zip').read_bytes())),
                     ensure_ascii=False))


if __name__ == '__main__':
    build()
