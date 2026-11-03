class OriginalPublicSourcePins:
    """Byte-only reads for the exact original manifests; no load or execution."""
    LIMIT = 16 * 1024 * 1024

    def __init__(self, allowed):
        require(type(allowed) is dict and 1 <= len(allowed) <= 20, 'Bounded original source allowlist required')
        self.allowed = dict(allowed)
        for value in self.allowed.values():
            digest(value)
        self.files = {}

    @staticmethod
    def identity(value):
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
                value.st_ctime_ns, value.st_mode, value.st_uid, value.st_gid)

    def read(self, entry):
        require(type(entry) is dict and set(entry) == {'path', 'sha256'}
                and self.allowed.get(entry['path']) == entry['sha256'], 'Unreviewed original public source pin')
        path = Path(entry['path'])
        require(path.is_absolute() and str(path) == entry['path'] and path.resolve() == path
                and not path.is_symlink(), 'Redirected original public source')
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_size <= self.LIMIT, 'Nonregular or oversized original source')
            raw = stream.read(self.LIMIT + 1)
            after = os.fstat(stream.fileno())
        current = os.stat(str(path), follow_symlinks=False)
        require(len(raw) <= self.LIMIT and self.identity(before) == self.identity(after) == self.identity(current)
                and sha(raw) == entry['sha256'], 'Original source changed or checksum differs')
        record = (raw, self.identity(after))
        if entry['path'] in self.files:
            require(record == self.files[entry['path']], 'Original source changed since first read')
        self.files[entry['path']] = record
        return raw

    def unchanged(self):
        for path in list(self.files):
            self.read({'path': path, 'sha256': self.allowed[path]})
