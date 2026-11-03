// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
enum {
 YUKI_EXPRESSION_MASK=0xff,
 YUKI_EYES_AUTHORED=0,
 YUKI_EYES_THINKING_CLOSED=0x100,
 YUKI_EYES_ANSWER_OPEN=0x200,
 YUKI_EYES_MASK=0x300,
 YUKI_FEATURE_DIALOGUE_FACIALS=1
};
typedef struct {
 uint64_t owner,sequence,audio_sample;
 uint32_t sample_rate,track,playing,paused,expression,pose;
 float gain,level;
 double captured_at;
} YukiControl;
typedef struct {
 uint64_t frames,author_ticks,owner,sequence,audio_sample,rejected_controls,stale_frames;
 double evaluate_ms,submit_ms,mouth,eye,elapsed_dropped_seconds;
} YukiStats;
// The binary struct layouts stay unchanged. expression's low byte is the
// original six-way expression; its eye-policy bits are the enum above.
// A new adapter requires this capability before creating a native instance.
uint32_t yuki_control_features(void);
// All API calls, including destroy, require the owning GTK/GL thread and context.
void* yuki_create(const char* model,const char* resx,const char* resource_root,uint32_t seed);
const char* yuki_error(void*);
int yuki_control(void*,const YukiControl*); // 1 accepted; 0 invalid/outdated
int yuki_render(void*,double monotonic_seconds,int width,int height,YukiStats*);
int yuki_capture(void*,const char* output,int width,int height); // explicit diagnostics only
void yuki_destroy(void*);
#ifdef __cplusplus
}
#endif
