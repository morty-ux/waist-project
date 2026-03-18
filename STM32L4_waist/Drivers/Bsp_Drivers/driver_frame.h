#ifndef __DRIVER_FRAME_H__
#define __DRIVER_FRAME_H__

#include <stdint.h>
#include <stdbool.h>
#include "driver_actuator.h"
#include "driver_log.h"
#include "FreeRTOS.h"
#include "queue.h"
#include "semphr.h"  

// ==========================================
// 1. 协议常量定义
// ==========================================
#define FRAME_HEAD      0xA5
#define FRAME_TAIL      0x5A
#define FUNC_CTRL       0xCC  // 控制帧功能码
#define DATA_LEN        16    // 4个float = 16字节
#define FRAME_TOTAL_LEN 21    // 1(头)+1(功)+1(长)+16(数)+1(校)+1(尾)

#define FRAME_QUE_SIZE  10

// ==========================================
// 2. 数据结构定义
// ==========================================

// 强制 1 字节对齐，确保结构体紧凑，无空隙
#pragma pack(push, 1)
// 完整的帧结构体
typedef struct {
    uint8_t  head;      // [0] 0xA5
    uint8_t  func;      // [1] 0xCC
    uint8_t  len;       // [2] 0x10
    float    rb;        // 右后电机
    float    rf;        // 右前电机
    float    lb;        // 左后电机
    float    lf;        // 左前电机
    uint8_t  check;     // [19] 校验位
    uint8_t  tail;      // [20] 0x5A
} Frame_Struct_t;
#pragma pack(pop) // 恢复默认对齐

// 共用体：既是结构体，又是数组 (核心技巧)
typedef union {
    Frame_Struct_t frame;
    uint8_t        buffer[FRAME_TOTAL_LEN];
} Frame_Packet_u;

// ==========================================
// 3. 外部接口声明
// ==========================================

/**
 * @brief 初始化Frame数据处理任务与队列
 * @param uxPriority 任务优先级
 * @return 成功返回 pdPASS，失败返回 pdFAIL
 */
BaseType_t xFrameInit(UBaseType_t uxPriority);

/**
 * @brief 获取Frame消息队列句柄
 * @return QueueHandle_t
 */
QueueHandle_t get_FrameQueueHandle(void);

/**
 * @brief 中断中获取数据并释放信号量唤醒任务
 * @param buf 接收到的数据首地址
 * @param len 接收到的数据长度
 */
void Frame_GetArgsFromISR(uint8_t *buf, uint16_t len);

/**
 * @brief [核心] 缓冲区直接解析 
 * @return true: 解析成功并成功发送到队列; false: 校验失败或长度不对
 */
bool Driver_Frame_ParseBuffer(void);

/**
 * @brief 准备发送数据 (组包)
 * @param pkt 帧数据包指针
 * @param heart 心跳包数据（当前协议体暂未启用该字段）
 * @param rb 右后轮目标值
 * @param rf 右前轮目标值
 * @param lb 左后轮目标值
 * @param lf 左前轮目标值
 */
void Driver_Frame_Pack(Frame_Packet_u *pkt, uint16_t heart, float rb, float rf, float lb, float lf);

#endif // __DRIVER_FRAME_H__