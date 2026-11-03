/* Continuous cursor reference for the v1.2 board input contract.
 * PC numerical parity checked; integration/render performance on KV260 pending.
 * Caller resets on every asset/state entry, requests exit on stop/cancel or
 * pool rotation, and samples with seconds since that entry. Link libm.
 * Burst playback and emergency transitions stay in the caller's event policy.
 * For segmented assets, interpolate floor(cursor) and ceil(cursor) only.
 */
#ifndef AVATAR_PLAYBACK_H
#define AVATAR_PLAYBACK_H
#include <math.h>

typedef struct {
    int stage; /* 0 enter, 1 loop, 2 velocity ramp, 3 exit */
    int requested, to_last, done;
    double from, target, exit_t0;
} avatar_cursor_t;

static inline void avatar_cursor_reset(avatar_cursor_t *p) {
    p->stage = p->requested = p->to_last = p->done = 0;
    p->from = p->target = p->exit_t0 = 0.0;
}
static inline void avatar_cursor_request_exit(avatar_cursor_t *p, int pool_rotation) {
    if (p->stage < 2) { p->requested = 1; p->to_last = pool_rotation; }
}
static inline double avatar_cursor_sample(avatar_cursor_t *p, double t,
        double fps, double start, double a, double b, double last) {
    const double ramp = 0.150;
    double position = 0.0;
    if (fps <= 0.0) fps = 24.0;
    if (t < 0.0) t = 0.0;
    if (p->stage < 2) {
        double enter_end = fmax(0.0, (a - start) / fps);
        if (t < enter_end) { p->stage = 0; position = start + t * fps; }
        else {
            double period = fmax(0.0, 2.0 * (b - a) / fps * 3.0);
            double u = period > 0.0 ? fmod(t - enter_end, period) / period : 0.0;
            p->stage = 1;
            position = a + (b - a) * (1.0 - cos(6.283185307179586 * u)) / 2.0;
        }
        if (p->requested) {
            p->from = position;
            p->target = !p->to_last && position - start < last - position ? start : last;
            p->stage = 2; p->exit_t0 = t;
        }
    }
    if (p->stage >= 2) {
        double elapsed = fmax(0.0, t - p->exit_t0);
        double advance = elapsed < ramp ? fps * elapsed * elapsed / (2.0 * ramp)
                                        : fps * fmax(0.0, elapsed - ramp / 2.0);
        double distance = fabs(p->target - p->from);
        double direction = p->target >= p->from ? 1.0 : -1.0;
        position = p->from + direction * fmin(distance, advance);
        p->done = advance >= distance;
        if (elapsed >= ramp || p->done) p->stage = 3;
    }
    return position;
}
#endif
