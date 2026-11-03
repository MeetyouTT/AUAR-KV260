"""Only the selected source, startup configuration and manifest can roll forward."""
import hashlib


def roll_forward(paths, old_hashes, new_bytes, *, read, replace, guard, checkpoint=lambda name: None):
    if len(paths) != 3 or len(set(paths)) != 3 or set(paths) != set(old_hashes) or set(paths) != set(new_bytes):
        raise ValueError('exact_three_target_transaction_required')
    new_hashes = {path: hashlib.sha256(new_bytes[path]).hexdigest() for path in paths}

    def checked():
        guard()
        current = {}
        for path in paths:
            current[path] = hashlib.sha256(read(path)).hexdigest()
            if current[path] not in (old_hashes[path], new_hashes[path]):
                raise ValueError('transaction_target_outside_reviewed_old_new')
        return current

    checked()
    for index, path in enumerate(paths):
        current = checked()
        if current[path] != new_hashes[path]:
            replace(path, new_bytes[path])
        if hashlib.sha256(read(path)).hexdigest() != new_hashes[path]:
            raise ValueError('transaction_readback_mismatch')
        checkpoint(('source', 'startup', 'manifest')[index])
    checked()
    if any(hashlib.sha256(read(path)).hexdigest() != new_hashes[path] for path in paths):
        raise ValueError('transaction_incomplete')
    return new_hashes
