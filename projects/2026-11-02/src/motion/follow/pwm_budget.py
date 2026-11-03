"""PWM timing constants; this module has no device or clock side effects."""

# The first COMMIT starts a pulse at the confirmed current width. The changed
# target is latched at the next 20ms PWM frame. 23ms covers that entire frame
# boundary and its <=2.5ms pulse, rather than accepting a target with no output.
PWM_FRAME_MS = 20
INITIAL_PWM_MINIMUM_LEASE_MS = 23

# These are existing submission protections, not extra source validity.
SUBMISSION_MARGIN_MS = 20
COMMIT_PREFLIGHT_RESERVE_MS = 3

