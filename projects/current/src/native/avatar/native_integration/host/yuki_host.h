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
 YUKI_FEATURE_DIALOGUE_FACIALS=1,
 YUKI_FEATURE_DIALOGUE_MOTION=2
};
enum {
 YUKI_IDLE=0,YUKI_PRESENT,YUKI_AWAKE,YUKI_LISTENING,YUKI_THINKING,
 YUKI_SPEAKING,YUKI_SPEAKING_HAPPY,YUKI_SPEAKING_LOW,
 YUKI_ACK_NOD,YUKI_DENY_SHAKE,YUKI_PUZZLED,YUKI_CANCELLED,YUKI_ERROR,YUKI_PAUSED,
 YUKI_STATE_COUNT
};
enum {YUKI_ACTION_NONE=0,YUKI_ACTION_NOD,YUKI_ACTION_SHAKE,YUKI_ACTION_SURPRISED,YUKI_ACTION_PUZZLED};
typedef struct {
 uint64_t owner,sequence,audio_sample;
 uint32_t sample_rate,track,playing,paused,expression,pose;
 float gain,level;
 double captured_at;
} YukiControl;
// Optional versioned entry point. Keep the original 64-byte audio ABI intact.
// One atomic offer carries the audio lease, dialogue posture and idempotent cue.
typedef struct {
 YukiControl audio;
 uint64_t generation,action_token;
 uint32_t state,action;
} YukiDialogueControl;
typedef struct {
 uint64_t generation,action_token,completed_token,gestures_started,gestures_completed;
 uint32_t state,action;
 float values[8];
} YukiMotionStats;
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
int yuki_control_v2(void*,const YukiDialogueControl*);
int yuki_motion_status(void*,YukiMotionStats*);
int yuki_render(void*,double monotonic_seconds,int width,int height,YukiStats*);
int yuki_capture(void*,const char* output,int width,int height); // explicit diagnostics only
void yuki_destroy(void*);
#ifdef __cplusplus
}
#endif
