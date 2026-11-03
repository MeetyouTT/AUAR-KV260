"""An uncomputed identity packet must not invalidate an existing fresh result."""


class DeferredIdentity(RuntimeError):
    """Busy or expired optional work; discard without a recognition decision."""

