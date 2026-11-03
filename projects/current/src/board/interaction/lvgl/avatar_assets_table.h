/* 自动生成，请勿手改：python scripts/board_export.py --header
 * 源：ui/avatar_board_manifest.json + assets/avatar/<素材名>/frames.rgb565
 * 环境标签：PC / SIMULATED（板端实测另行记录）
 * 帧流格式：RGB565 **大端 R5G6B5**，逐帧紧密排列；底色已按 #FCFCF3 合成。
 */
#ifndef AVATAR_ASSETS_TABLE_H
#define AVATAR_ASSETS_TABLE_H

#include <stdint.h>

#define AVATAR_CANVAS_W        1024u
#define AVATAR_CANVAS_H        600u
#define AVATAR_PANEL_BG_RGB565 0xFFFEu   /* #FCFCF3 */
#define AVATAR_BOX_X           593u
#define AVATAR_BOX_Y           32u
#define AVATAR_BOX_W           423u
#define AVATAR_BOX_H           516u
#define AVATAR_FRAME_BYTES     445440u   /* 单帧最大字节 */
#define AVATAR_DOUBLE_BUFFER   890880u   /* 双缓冲 = 2 帧 */
#define AVATAR_CANVAS_RGB565   1228800u   /* 整屏一帧 1024x600x2 */

typedef struct {
    const char *state;          /* 运行时状态，如 SPEAKING_LOW */
    const char *label;          /* 中文标签（UTF-8），如 播报·低落 */
    const char *asset;          /* **实际加载**的素材目录名（帧流所在） */
    const char *asset_mapped;   /* 该状态**映射**的素材名（未就绪时供诊断） */
    uint16_t    frames;         /* 帧数 */
    uint16_t    width;          /* 素材宽（像素） */
    uint16_t    height;         /* 素材高（像素） */
    uint32_t    fps_milli;      /* 帧率 x1000（9.983 -> 9983） */
    uint32_t    rgb565_bytes;   /* 帧流总字节 = width*height*2*frames */
    uint16_t    dst_x, dst_y;   /* 画布绝对落位（contain + 底部对齐） */
    uint16_t    dst_w, dst_h;   /* 落位尺寸（<= avatar_box） */
    uint8_t     ready;          /* 1=专属素材；0=当前为兜底素材 */
    const char *fallback_from;  /* 非空 = 兜底来源素材名 */
} avatar_asset_t;

static const avatar_asset_t AVATAR_ASSETS[] = {
    { "IDLE", "待机", "idle_normal", "idle_normal", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "PRESENT", "注视", "idle_present", "idle_present", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "LISTENING", "聆听", "idle_listening", "idle_listening", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "THINKING", "思考", "idle_thinking", "idle_thinking", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "SPEAKING", "播报", "talking_normal", "talking_normal", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "SPEAKING_NEUTRAL", "播报·中性", "talking_neutral", "talking_neutral", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "SPEAKING_LOW", "播报·低落", "talking_low", "talking_low", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "AWAKE", "唤醒", "emo_surprised", "emo_surprised", 22, 464, 480, 24000, 9799680u, 593, 110, 423, 438, 1, 0 },
    { "PUZZLED", "困惑", "emo_puzzled", "emo_puzzled", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "ACK_NOD", "确认", "ack_nod", "ack_nod", 22, 464, 480, 24000, 9799680u, 593, 110, 423, 438, 1, 0 },
    { "DENY_SHAKE", "拒绝", "deny_shake", "deny_shake", 22, 464, 480, 24000, 9799680u, 593, 110, 423, 438, 1, 0 },
    { "CAMERA_LOST", "摄像头丢失", "idle_offline", "idle_offline", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "NETWORK_LOST", "本地模式", "idle_offline", "idle_offline", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "CANCELLED", "已取消", "idle_normal", "idle_normal", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
    { "ERROR", "错误", "emo_sad", "emo_sad", 39, 464, 480, 24000, 17372160u, 593, 110, 423, 438, 1, 0 },
};

#define AVATAR_ASSETS_COUNT  (sizeof(AVATAR_ASSETS) / sizeof(AVATAR_ASSETS[0]))

/* 生成时快照：专属素材 13 态 / 复用 2 态 / 兜底 0 态；已打包帧流素材 16 个 */

typedef struct { uint16_t start, end; } avatar_window_t;
static const avatar_window_t AVATAR_LOOP_WINDOWS[] = {
    { 28u, 35u },
    { 13u, 20u },
    { 14u, 21u },
    { 28u, 35u },
    { 12u, 19u },
    { 28u, 35u },
    { 28u, 35u },
    { 16u, 23u },
    { 18u, 25u },
    { 28u, 35u },
    { 12u, 19u },
    { 13u, 20u },
    { 12u, 19u },
};
typedef struct {
    const char *asset, *frames_file;
    uint16_t frames, width, height;
    uint32_t fps_milli, rgb565_bytes;
    uint16_t enter_start, enter_end, exit_start, exit_end;
    uint16_t windows_offset, windows_count;
    uint8_t burst;
} avatar_resource_t;
static const avatar_resource_t AVATAR_RESOURCES[] = {
    {"idle_normal", "idle_normal/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 28u, 35u, 38u, 0u, 1u, 0u},
    {"idle_present", "idle_present/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 13u, 20u, 38u, 1u, 1u, 0u},
    {"idle_listening", "idle_listening/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 14u, 21u, 38u, 2u, 1u, 0u},
    {"idle_thinking", "idle_thinking/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 28u, 35u, 38u, 3u, 1u, 0u},
    {"talking_normal", "talking_normal/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 12u, 19u, 38u, 4u, 1u, 0u},
    {"talking_low", "talking_low/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 28u, 35u, 38u, 5u, 1u, 0u},
    {"talking_neutral", "talking_neutral/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 28u, 35u, 38u, 6u, 1u, 0u},
    {"emo_surprised", "emo_surprised/frames.rgb565", 22u, 464u, 480u, 24000u, 9799680u, 0u, 21u, 21u, 21u, 7u, 0u, 1u},
    {"emo_puzzled", "emo_puzzled/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 16u, 23u, 38u, 7u, 1u, 0u},
    {"ack_nod", "ack_nod/frames.rgb565", 22u, 464u, 480u, 24000u, 9799680u, 0u, 21u, 21u, 21u, 8u, 0u, 1u},
    {"deny_shake", "deny_shake/frames.rgb565", 22u, 464u, 480u, 24000u, 9799680u, 0u, 21u, 21u, 21u, 8u, 0u, 1u},
    {"idle_offline", "idle_offline/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 18u, 25u, 38u, 8u, 1u, 0u},
    {"emo_sad", "emo_sad/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 28u, 35u, 38u, 9u, 1u, 0u},
    {"talking_neutral_b", "talking_neutral_b/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 12u, 19u, 38u, 10u, 1u, 0u},
    {"talking_neutral_c", "talking_neutral_c/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 13u, 20u, 38u, 11u, 1u, 0u},
    {"talking_normal_b", "talking_normal_b/frames.rgb565", 39u, 464u, 480u, 24000u, 17372160u, 0u, 12u, 19u, 38u, 12u, 1u, 0u},
};
#define AVATAR_RESOURCES_COUNT 16u
static const uint16_t AVATAR_POOL_INDICES[] = { 0u, 1u, 2u, 3u, 4u, 15u, 6u, 13u, 14u, 5u, 7u, 8u, 9u, 10u, 11u, 11u, 0u, 12u };
typedef struct { uint16_t offset, count; } avatar_pool_t;
/* Same state order as AVATAR_ASSETS. */
static const avatar_pool_t AVATAR_STATE_POOLS[] = {
    { 0u, 1u },
    { 1u, 1u },
    { 2u, 1u },
    { 3u, 1u },
    { 4u, 2u },
    { 6u, 3u },
    { 9u, 1u },
    { 10u, 1u },
    { 11u, 1u },
    { 12u, 1u },
    { 13u, 1u },
    { 14u, 1u },
    { 15u, 1u },
    { 16u, 1u },
    { 17u, 1u },
};
#define AVATAR_BLEND_MS 150u
#define AVATAR_CONTINUOUS_CURSOR_VERSION 1u
#define AVATAR_PRIMARY_WINDOW_ONLY 1u
/* blend is a velocity ramp; use avatar_playback.h, no pose crossfade. */
#define AVATAR_POOL_SWITCH_MS 6000u
#define AVATAR_LOOP_SLOWDOWN_MILLI 3000u
#endif /* AVATAR_ASSETS_TABLE_H */
