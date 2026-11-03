"""Private selection reference -> hashes only; never selects or grants a scope."""
import stat


def selection_scope_metadata():
    path = Path('/home/root/.local/share/aura-board-business/conversation_selection.json')
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        assert stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
        assert info.st_nlink == 1 and not info.st_mode & 0o077 and info.st_size <= 4096
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(4097)
        assert len(raw) <= 4096
        value = json.loads(raw)
        assert set(value) == {'version', 'conversation_id'} and value['version'] == 1
        cid = value['conversation_id']
        assert isinstance(cid, str) and len(cid) == 32 and all(c in '0123456789abcdef' for c in cid)
        return dict(selection_file_sha256=hashlib.sha256(raw).hexdigest(),
                    scope_token=hashlib.sha256(('conversation:' + cid).encode()).hexdigest(),
                    saved_reference_is_not_a_new_profile_grant=True,
                    raw_identifier_exported=False)
    finally:
        os.close(fd)
