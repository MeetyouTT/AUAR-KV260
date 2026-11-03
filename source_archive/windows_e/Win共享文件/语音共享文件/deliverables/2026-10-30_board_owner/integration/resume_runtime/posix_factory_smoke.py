"""POSIX kernel-writer gate smoke: empty synthetic fixture, no model/device IO.

Invoke with --aura-root pointing at the staged candidate source. The temporary
directory is private and removed on completion; no production store is opened.
"""
import argparse
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time


def run(aura_root):
    import sys
    sys.path.insert(0, str(Path(aura_root).resolve()))
    from board.runtime.board_business import BoardBusinessConfig, create_board_business_runtime
    from common.conversation_selection import ConversationSelection
    if os.name != 'posix':
        raise RuntimeError('POSIX smoke requires Linux; it never simulates a Windows production lock')
    class Timeline:
        boot_id = 'synthetic-writer-smoke'
        def event_time(self): return 1793400000.
        def safe_for_compaction(self): return True
        def compaction_guard(self): return nullcontext()
        def quality_snapshot(self): return {'quality':'fixture', 'safe_for_compaction':True}
    class Client:
        host, port = '192.168.50.1', 8797
        def request(self, *args, **kwargs): raise AssertionError('No model request allowed')
        def sample_health_date(self, *args, **kwargs): raise AssertionError('No network allowed')
    timeline = Timeline()
    with tempfile.TemporaryDirectory(prefix='aura-writer-fixture-') as temporary:
        parent = Path(temporary); root = parent/'private'
        config = BoardBusinessConfig(str(root), (1793300000.,1793500000.), data_origin='board')
        kwargs = dict(asr=object(), system_prompt='公开合成验证。只输出三字段JSON。',
            conversation_selection=ConversationSelection(parent/'selection.json'),
            client=Client(), timeline=timeline, capture_idle=lambda:True)
        first = create_board_business_runtime(config, timeline.boot_id, **kwargs)
        db = root/'timeline.sqlite3'
        before = hashlib.sha256(db.read_bytes()).hexdigest()
        try:
            try:
                second = create_board_business_runtime(config, timeline.boot_id, **kwargs)
            except BlockingIOError:
                duplicate_rejected = True
            else:
                second.close()
                raise AssertionError('A second writer unexpectedly acquired the kernel lease')
            assert hashlib.sha256(db.read_bytes()).hexdigest() == before
        finally:
            first.close()
        reopened = create_board_business_runtime(config, timeline.boot_id, **kwargs)
        reopened.close()
        root.chmod(0o755)
        try:
            try:
                create_board_business_runtime(config, timeline.boot_id, **kwargs)
            except PermissionError:
                broad_permissions_rejected = True
            else:
                raise AssertionError('Non-private production directory was accepted')
        finally:
            root.chmod(0o700)
        link = parent/'link'; link.symlink_to(root, target_is_directory=True)
        linked = BoardBusinessConfig(str(link), (1793300000.,1793500000.), data_origin='board')
        try:
            create_board_business_runtime(linked, timeline.boot_id, **kwargs)
        except ValueError:
            symlink_rejected = True
        else:
            raise AssertionError('Production root symlink was accepted')
        return dict(status='PASS', fixture_only=True, actual_models=False, actual_devices=False,
                    production_databases_opened=False, duplicate_writer_rejected=duplicate_rejected,
                    source_unchanged_before_failed_duplicate=True, reopen_after_close=True,
                    non_private_directory_rejected=broad_permissions_rejected, symlink_rejected=symlink_rejected)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--aura-root',required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.aura_root),separators=(',',':')))
