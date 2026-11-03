"""Packet deferral is distinct from an unconfirmed native execution failure."""


class PrimaryAdmissionDeferred(RuntimeError):
    """Keep the detector/owner and wait for the next real captured frame."""
