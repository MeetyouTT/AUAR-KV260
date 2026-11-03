// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
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
