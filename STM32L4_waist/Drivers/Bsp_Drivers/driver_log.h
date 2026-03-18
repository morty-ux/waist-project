#ifndef __DRIVER_LOG_H
#define __DRIVER_LOG_H

#ifdef __cplusplus
extern "C"
{
#endif

#include "FreeRTOS.h"
#include "queue.h"
#include "task.h"
#include "main.h"

#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdint.h>

#define PRINT_QUEUE_SIZE 10
#define MAX_PRINT_MSG_LEN 128

  /* 调试打印配置 */
#define DEBUG_PRINT_ENABLED // 注释掉此行以禁用所有调试打印

  // 调试级别
  typedef enum
  {
    DEBUG_LEVEL_ERROR = 0,
    DEBUG_LEVEL_WARNING = 1,
    DEBUG_LEVEL_INFO = 2
  } DebugLevel_t;

/**
 * @brief 启用或禁用项目中的所有调试打印语句。
 *
 * 当定义了 DEBUG_PRINT_ENABLED 时，所有调试打印语句（DEBUG_ERROR、DEBUG_WARNING、DEBUG_INFO）
 * 将被启用并打印。当未定义时，所有调试打印语句将被禁用。
 */
#ifdef DEBUG_PRINT_ENABLED
/**
 * @brief 内部宏，用于格式化日志层级、时间和任务名
 */
#define DEBUG_LOG_LEVEL(level, fmt, ...)                                                     \
  do                                                                                         \
  {                                                                                          \
    TickType_t currentTime = xTaskGetTickCount();                                            \
    const char *taskName = pcTaskGetName(NULL);                                              \
    printf("[%lu][%s][%s] " fmt,                                                             \
           currentTime,                                                                      \
           (level == DEBUG_LEVEL_ERROR) ? "ERROR" : (level == DEBUG_LEVEL_WARNING) ? "WARN"  \
                                                                                   : "INFO", \
           taskName,                                                                         \
           ##__VA_ARGS__);                                                                   \
  } while (0)

/**
 * @brief 打印包含当前任务名称和时间戳的错误级调试消息。
 *
 * 该宏用于打印错误级调试消息。它包含当前任务名称和打印消息时的时间戳。
 * 消息使用提供的格式字符串和参数进行格式化。
 *
 * @param fmt 调试消息的格式字符串。
 * @param ... 要格式化和打印的参数。
 */
#define DEBUG_ERROR(fmt, ...) DEBUG_LOG_LEVEL(DEBUG_LEVEL_ERROR, fmt, ##__VA_ARGS__)

/**
 * @brief 打印包含当前任务名称和时间戳的警告级调试消息。
 *
 * 该宏用于打印警告级调试消息。它包含当前任务名称和打印消息时的时间戳。
 * 消息使用提供的格式字符串和参数进行格式化。
 *
 * @param fmt 调试消息的格式字符串。
 * @param ... 要格式化和打印的参数。
 */
#define DEBUG_WARNING(fmt, ...) DEBUG_LOG_LEVEL(DEBUG_LEVEL_WARNING, fmt, ##__VA_ARGS__)

/**
 * @brief 打印包含当前任务名称和时间戳的信息级调试消息。
 *
 * 该宏用于打印信息级调试消息。它包含当前任务名称和打印消息时的时间戳。
 * 消息使用提供的格式字符串和参数进行格式化。
 *
 * @param fmt 调试消息的格式字符串。
 * @param ... 要格式化和打印的参数。
 */
#define DEBUG_INFO(fmt, ...) DEBUG_LOG_LEVEL(DEBUG_LEVEL_INFO, fmt, ##__VA_ARGS__)
#else
#define DEBUG_ERROR(fmt, ...) ((void)0)   // 设置为 `NULL` 以禁用所有调试打印
#define DEBUG_WARNING(fmt, ...) ((void)0) // 设置为 `NULL` 以禁用所有调试打印
#define DEBUG_INFO(fmt, ...) ((void)0)    // 设置为 `NULL` 以禁用所有调试打印

#endif // DEBUG_PRINT_ENABLED

  /**
   * @brief 表示要发送到打印队列的打印消息。
   *
   * 该结构体包含要打印的消息的 `buffer` 以及消息的长度。
   * 它用于在应用程序和打印任务之间传递打印消息。
   */
  typedef struct
  {
    char buffer[MAX_PRINT_MSG_LEN];
    uint16_t len;
  } PrintMessage_t;

  extern QueueHandle_t xPrintQueue;     // 打印消息的队列。在 print.c 中设置
  extern TaskHandle_t xPrintTaskHandle; // 打印任务的句柄。在 print.c 中设置

  /**
   * @brief 通过创建打印队列和打印任务来初始化打印子系统。
   *
   * 该函数设置打印子系统运行所需的基础设施。
   * 它创建一个队列（`xPrintQueue`）来保存打印消息，以及一个任务（`vStartPrintTask`）
   * 用于从队列中取出消息并通过UART发送。
   *
   * `uxPriority` 参数指定打印任务的优先级。应根据系统要求设置为适当的值。
   *
   * 该函数应在系统初始化期间调用，在任何打印操作执行之前。
   *
   * @param uxPriority 打印任务的优先级。
   * @return 如果打印子系统初始化成功则返回 `pdPASS`，否则返回 `pdFAIL`。
   */
  BaseType_t xPrintInit(UBaseType_t uxPriority);

  /**
   * @brief 通过销毁打印队列和打印任务来反初始化打印子系统。
   *
   * 该函数清理打印子系统使用的资源。它删除打印队列（`xPrintQueue`）和打印任务（`xPrintTaskHandle`）。
   * 当打印子系统不再需要时，例如在系统关闭期间，应调用此函数。
   */
  void print_deinit(void);

  /**
   * @brief 打印错误消息并进入无限循环。
   *
   * 该函数用于将错误消息打印到控制台，然后进入无限循环，
   * 有效地停止程序执行。这通常用于程序无法恢复的致命错误。
   *
   * @param msg 要打印的错误消息。
   */
  void print_error(const char *msg);

#ifdef __cplusplus
}
#endif

#endif /* __PRINT_H */