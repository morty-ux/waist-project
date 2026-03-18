#include "driver_log.h"

// 声明uart句柄
extern UART_HandleTypeDef hlpuart1;

QueueHandle_t xPrintQueue = NULL;     // 打印消息的队列
TaskHandle_t xPrintTaskHandle = NULL; // 打印消息任务的句柄

// 队列等待超时定义
#define PRINT_QUEUE_TIMEOUT_TICKS 5


/**
 * @brief 打印任务，负责从打印队列中获取打印消息并将其发送到UART。
 *
 * 该任务负责从 `xPrintQueue` 中出队打印消息，并使用 `HAL_UART_Transmit()` 将消息内容传输到UART。
 * 该任务将无限期阻塞，等待队列中有可用的消息。
 * 在传输消息后，任务将延迟1个时钟节拍，以允许其他任务运行。
 * 该任务旨在由 `print_init()` 函数创建，不应直接启动。
 */
static void vStartPrintTask(void *pvParameters)
{
#ifdef STACK_PRINT
		UBaseType_t uxHighWaterMark = uxTaskGetStackHighWaterMark(NULL); 
#endif
    PrintMessage_t message;
    for (;;)
    {
        // 从打印队列中获取打印消息
        if (xQueueReceive(xPrintQueue, &message, portMAX_DELAY) == pdTRUE)
        {
            HAL_UART_Transmit(&hlpuart1, (uint8_t *)message.buffer, message.len, HAL_MAX_DELAY);
        }
#ifdef STACK_PRINT
				uint32_t ulStackRemaining = uxHighWaterMark * 4;
				DEBUG_INFO("%d bytes short of overflow.\r\n", ulStackRemaining);
#endif
        vTaskDelay(1);
    }
}

/**
 * @brief 初始化打印子系统，通过创建打印队列和打印任务。
 * 这个函数设置了打印子系统操作所需的基础设施。
 * 它创建了一个队列（xPrintQueue）来保存打印消息，并创建了一个任务（vStartPrintTask），
 * 该任务将从队列中获取消息并将其发送到UART。
 * uxPriority参数指定打印任务的优先级。根据系统的要求设置适当的值。
 * 这个函数应该在系统初始化期间调用，在执行任何打印操作之前。
 * @param uxPriority 打印任务的优先级。
 * @return 如果打印子系统成功初始化则返回pdPASS，否则返回pdFAIL。
 */
BaseType_t xPrintInit(UBaseType_t uxPriority)
{
    // 验证优先级参数
    if (uxPriority > configMAX_PRIORITIES - 1)
    {
        return pdFAIL;
    }
    BaseType_t xReturn = pdPASS;
    // 创建打印队列
    xPrintQueue = xQueueCreate(PRINT_QUEUE_SIZE, sizeof(PrintMessage_t));
    if (xPrintQueue == NULL)
    {
        return pdFAIL;
    }
    // 创建打印任务
    BaseType_t xTaskRetVal = xTaskCreate(vStartPrintTask,
                                         "PrintTask",
                                         configMINIMAL_STACK_SIZE*8,
                                         NULL,
                                         uxPriority,
                                         &xPrintTaskHandle);
    if (xTaskRetVal != pdPASS)
    {
        printf("Error creating print task\n");
        xReturn = pdFAIL;
    }
    if (xReturn == pdFAIL)
    {
        vQueueDelete(xPrintQueue);
        xPrintQueue = NULL;
    }

    return xReturn;
}

/**
 * @brief 卸载打印子系统，通过销毁打印队列和打印任务。
 * 这个函数清理打印子系统使用的资源。它删除打印队列（xPrintQueue）和打印任务（xPrintTaskHandle）。
 * 当打印子系统不再需要时，例如在系统关闭期间，应调用此函数。
 */
void print_deinit(void)
{
    if (xPrintQueue != NULL)
    {
        vQueueDelete(xPrintQueue);
        xPrintQueue = NULL;
    }
    if (xPrintTaskHandle != NULL)
    {
        vTaskDelete(xPrintTaskHandle);
        xPrintTaskHandle = NULL;
    }
}

/**
 * @brief 打印错误信息并进入无限循环。
 * 这个函数用于将错误信息打印到控制台，然后进入无限循环，有效地停止程序执行。
 * 这通常用于程序无法从中恢复的严重错误。
 * @param msg 要打印的错误信息。
 */
void print_error(const char *msg)
{
    DEBUG_ERROR("ERROR: %s\n", msg);
    for (;;)
        ;
}


/**
 * @brief 重定向 C 标准库 printf 函数的输出。
 * * 此函数是标准库输出函数的底层钩子（Hook）。printf 格式化后的每个字符都会调用此函数。
 * 它将字符存入静态缓冲区，并在遇到换行符 '\n' 或缓冲区满时，将整行消息打包发送到
 * 打印队列 (xPrintQueue) 中，由异步打印任务统一处理。
 *
 * @param ch 要打印的字符。
 * @param f  文件流指针（在 MicroLIB 重定向中通常忽略）。
 * @return 返回写入的字符，如果失败则返回 EOF。
 */
int fputc(int ch, FILE *f) {
    // 使用 static 保证在多次 fputc 调用之间保留数据
    static PrintMessage_t msg_to_build; 
    static uint16_t index = 0;

    // 1. 存入字符
    msg_to_build.buffer[index++] = (char)ch;

    // 2. 检查发送条件：遇到换行符 \n 或 缓冲区将满
    if (ch == '\n' || index >= MAX_PRINT_MSG_LEN) {
        msg_to_build.len = index;

        if (xPrintQueue != NULL) {
            // 使用非阻塞发送 (0)，防止 printf 在队列满时卡死整个系统
            // 此时发送的是整行数据，避免了串口输出碎裂
            if (xQueueSend(xPrintQueue, &msg_to_build, PRINT_QUEUE_TIMEOUT_TICKS) != pdPASS) {
                // 如果发送失败（队列满），可以选择重置或记录
            }
        }
        
        // 3. 重置索引，准备接收下一行
        index = 0;
    }
    
    return ch;
}