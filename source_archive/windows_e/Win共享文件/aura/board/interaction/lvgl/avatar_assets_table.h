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
#define AVATAR_FRAME_BYTES     447360u   /* 单帧最大字节 */
#define AVATAR_DOUBLE_BUFFER   894720u   /* 双缓冲 = 2 帧 */
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
    { "IDLE", "待机", "idle_normal", "idle_normal", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 1, 0 },
    { "PRESENT", "注视", "idle_present", "idle_present", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 1, 0 },
    { "LISTENING", "聆听", "idle_listening", "idle_listening", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 1, 0 },
    { "THINKING", "思考", "idle_thinking", "idle_thinking", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 1, 0 },
    { "SPEAKING", "播报", "talking_normal", "talking_normal", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 1, 0 },
    { "SPEAKING_LOW", "播报·低落", "talking_low", "talking_low", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 1, 0 },
    { "CAMERA_LOST", "摄像头丢失", "idle_normal", "emo_puzzled", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 0, "idle_normal" },
    { "NETWORK_LOST", "本地模式", "idle_normal", "idle_offline", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 0, "idle_normal" },
    { "CANCELLED", "已取消", "idle_normal", "idle_normal", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 1, 0 },
    { "ERROR", "错误", "idle_normal", "emo_sad", 100, 466, 480, 9983, 44736000u, 593, 112, 423, 436, 0, "idle_normal" },
};

#define AVATAR_ASSETS_COUNT  (sizeof(AVATAR_ASSETS) / sizeof(AVATAR_ASSETS[0]))

/* 生成时快照：专属素材 6 态 / 复用 1 态 / 兜底 3 态；已打包帧流素材 6 个 */

#endif /* AVATAR_ASSETS_TABLE_H */
