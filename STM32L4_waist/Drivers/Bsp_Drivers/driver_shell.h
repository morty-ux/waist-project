#ifndef __DRIVER_SHELL_H
#define __DRIVER_SHELL_H

#include "driver_log.h"
#include "driver_actuator.h"
#include "FreeRTOS.h"
#include "queue.h"
#include "semphr.h"  

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SHELL_MAX_LINE_LEN    64   // 单条指令最大长度
#define SHELL_MAX_ARGS        4    // 最大参数数量 (例如: CMD ARG1 ARG2)
#define SHELL_QUE_SIZE 10

// 指令处理函数指针定义
typedef void (*shell_func_t)(int argc, char *argv[]);

// 指令映射表结构体
typedef struct {
    const char *cmd_name;    // 指令名, 如 "RB"
    shell_func_t handler;    // 对应的处理函数
    const char *help;        // 帮助信息
} shell_cmd_t;


BaseType_t xShellInit(UBaseType_t uxPriority);
QueueHandle_t get_shellQueueHandle(void);
void Shell_Exec();

// 外部调用接口
void Shell_GetArgsFromISR(const char *line, uint16_t max_len);

#endif
