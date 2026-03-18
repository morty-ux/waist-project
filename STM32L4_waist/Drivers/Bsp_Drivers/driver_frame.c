#include "driver_frame.h"
#include <string.h> 

// ==========================================
// 外部变量引入
// ==========================================
extern QueueSetHandle_t g_control_set;

// ==========================================
// 内部状态机及相关变量定义
// ==========================================
typedef enum {
    STATE_HEAD = 0,
    STATE_FUNC,
    STATE_LEN,
    STATE_DATA,
    STATE_CHECK,
    STATE_TAIL
} RxState_t;

// 接收缓冲区
static uint8_t frame_buf[FRAME_TOTAL_LEN];
static uint16_t frame_len;

// 消息队列句柄
static QueueHandle_t g_xQueueFrame;
// Frame命令处理任务句柄
static TaskHandle_t xFrameTaskHandle = NULL;
// 任务唤醒信号量
static SemaphoreHandle_t frame_sem;


// ==========================================
// 内部函数：校验计算
// ==========================================

/**
 * @brief 计算校验和
 * 规则: ~(Header + Func + Data)
 * 注意：按照规则，Len 位是不参与计算的
 */
static uint8_t Calculate_Checksum(Frame_Packet_u *pkt) {
    uint8_t sum = 0;
    
    // 1. 加 Header [0] 和 Func [1]
    sum += pkt->buffer[0];
    sum += pkt->buffer[1];
    
    // 2. 加 Data [3] ~ [14] (跳过 Len [2])
    // 数据区偏移量是 3，长度是 DATA_LEN (16 bytes for 4 floats)
    for (int i = 0; i < DATA_LEN; i++) {
        sum += pkt->buffer[3 + i];
    }
    
    return (uint8_t)(~sum);
}


// ==========================================
// 外部接口实现
// ==========================================

/**
 * @brief 返回Frame消息队列句柄
 */
QueueHandle_t get_FrameQueueHandle(void)
{
    return g_xQueueFrame;
}

/**
 * @brief 中断中获取数据并唤醒任务
 */
void Frame_GetArgsFromISR(uint8_t *buf, uint16_t len)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    
    if (len == 0) return;
    if (len > FRAME_TOTAL_LEN) len = FRAME_TOTAL_LEN;
    
    memcpy(frame_buf, buf, len);
    frame_len = len;
    
    // 给出信号量唤醒处理任务
    xSemaphoreGiveFromISR(frame_sem, &xHigherPriorityTaskWoken);
    
    // 如果需要切换上下文
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}

/**
 * @brief [核心] 缓冲区直接解析 
 * @return true: 解析成功
 */
bool Driver_Frame_ParseBuffer()
{
    if (frame_len != FRAME_TOTAL_LEN) {
        return false;
    }

    Frame_Packet_u *pkt = (Frame_Packet_u *)frame_buf;

    // 1. 验证帧头、帧尾、功能码、长度
    if (pkt->frame.head != FRAME_HEAD ||
        pkt->frame.tail != FRAME_TAIL ||
        pkt->frame.func != FUNC_CTRL ||
        pkt->frame.len  != DATA_LEN) 
    {
        return false;
    }

    // 2. 验证校验和
    if (pkt->frame.check != Calculate_Checksum(pkt)) {
        return false;
    }

    // 3. 提取数据并发送到队列 (假设 ActuatorTarget 在 driver_actuator.h 中已定义)
    ActuatorTarget target;
    target.RbTarget = pkt->frame.rb;
    target.RfTarget = pkt->frame.rf;
    target.LbTarget = pkt->frame.lb;
    target.LfTarget = pkt->frame.lf;

    // 注意：这里是在 Task 环境中，所以使用 xQueueSend 而不是 FromISR 版本
    xQueueSend(g_xQueueFrame, &target, (TickType_t)0);

    return true;
}

/**
 * @brief Frame 任务，负责等待信号量并解析数据
 */
static void vFrameExecTask(void *pvParameters)
{
#ifdef STACK_PRINT
    UBaseType_t uxHighWaterMark = uxTaskGetStackHighWaterMark(NULL); 
#endif
    
    frame_sem = xSemaphoreCreateBinary();
    
    for (;;)
    {
        /* 等待中断释放的信号量 */
        if (xSemaphoreTake(frame_sem, portMAX_DELAY) == pdTRUE) {
            
            if (Driver_Frame_ParseBuffer()) {
                DEBUG_INFO("Frame Parse Ok\n");
            } else {
                DEBUG_INFO("Frame Parse Error\n");
            }

#ifdef STACK_PRINT
            uint32_t ulStackRemaining = uxHighWaterMark * 4;
            DEBUG_INFO("Frame task: %d bytes short of overflow.\r\n", ulStackRemaining);
#endif
        }
    }
}

/**
 * @brief 初始化 Frame 处理任务和队列
 */
BaseType_t xFrameInit(UBaseType_t uxPriority)
{
    if (uxPriority > configMAX_PRIORITIES - 1)
    {
        return pdFAIL;
    }
    
    BaseType_t xReturn = pdPASS;
    
    // 创建 Frame 数据队列，并加入队列集
    g_xQueueFrame = xQueueCreate(FRAME_QUE_SIZE, sizeof(ActuatorTarget));
    if (g_xQueueFrame == NULL)
    {
        return pdFAIL;
    }
    xQueueAddToSet(g_xQueueFrame, g_control_set);

    // 创建处理任务
    BaseType_t xTaskRetVal = xTaskCreate(vFrameExecTask,
                                         "FrameTask",
                                         configMINIMAL_STACK_SIZE * 10,
                                         NULL,
                                         uxPriority,
                                         &xFrameTaskHandle);
    if (xTaskRetVal != pdPASS)
    {
        DEBUG_INFO("Error creating frame task\n");
        xReturn = pdFAIL;
    }
    
    if (xReturn == pdFAIL)
    {
        vQueueDelete(g_xQueueFrame);
        g_xQueueFrame = NULL;
    }

    return xReturn;
}


/**
 * @brief 准备发送数据 (组包)
 * @param pkt 帧数据包指针
 */
void Driver_Frame_Pack(Frame_Packet_u *pkt, uint16_t heart, float rb, float rf, float lb, float lf) {
    // 1. 填充固定头部
    pkt->frame.head = FRAME_HEAD;
    pkt->frame.func = FUNC_CTRL;
    pkt->frame.len  = DATA_LEN;
    
    // 2. 填充有效数据
    pkt->frame.rb = rb;
    pkt->frame.rf = rf;
    pkt->frame.lb = lb;
    pkt->frame.lf = lf;
    
    // 注意：目前的 Frame_Struct_t 结构体中没有定义 heart 字段。
    // 如果协议需要包含心跳数据，需要在头文件中的 Frame_Struct_t 添加该字段，并重新计算 DATA_LEN。
        
    // 3. 计算校验和填充尾部
    pkt->frame.check = Calculate_Checksum(pkt);
    pkt->frame.tail  = FRAME_TAIL;
}