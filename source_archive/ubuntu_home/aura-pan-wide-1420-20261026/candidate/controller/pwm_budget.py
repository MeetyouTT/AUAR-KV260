"""PWM timing constants; this module has no device or clock side effects."""

# The first COMMIT starts a pulse at the confirmed current width. The changed
# target is latched at the next 20ms PWM frame. The wide build must cover
# that boundary plus a complete <=2.5ms pulse and its existing timing guard.
PWM_FRAME_MS = 20
from board.motion.pan_profile import INITIAL_PWM_MINIMUM_LEASE_MS

# These are existing submission protections, not extra source validity.
SUBMISSION_MARGIN_MS = 20
COMMIT_PREFLIGHT_RESERVE_MS = 3

