#include "driver_shell.h"


extern QueueSetHandle_t g_control_set;

// --- 内部私有处理函数声明 ---
static void shell_cmd_rb(int argc, char *argv[]);

// --- 指令映射表 ---
// 在这里添加你的新指令
static const shell_cmd_t cmd_list[] = {
    {"RB",   shell_cmd_rb,   "Set Read Back value. Usage: RB <float>"},
};

#define CMD_COUNT (sizeof(cmd_list) / sizeof(shell_cmd_t))


// 接收缓冲区
static char args_copy[SHELL_MAX_LINE_LEN];
uint16_t cmd_len;

// 消息队列句柄
static QueueHandle_t g_xQueueshell;
// shell命令处理句柄
static TaskHandle_t xShellTaskHandle = NULL;
// 任务唤醒信号量
static SemaphoreHandle_t shell_sem;


// 返回消息队列句柄
QueueHandle_t get_shellQueueHandle(void)
{
	return g_xQueueshell;
}




/**
 * @brief 打印任务，负责从打印队列中获取打印消息并将其发送到UART。
 *
 * 该任务负责从 `xPrintQueue` 中出队打印消息，并使用 `HAL_UART_Transmit()` 将消息内容传输到UART。
 * 该任务将无限期阻塞，等待队列中有可用的消息。
 * 在传输消息后，任务将延迟1个时钟节拍，以允许其他任务运行。
 * 该任务旨在由 `print_init()` 函数创建，不应直接启动。
 */
static void vShellExecTask(void *pvParameters)
{
#ifdef STACK_PRINT
		UBaseType_t uxHighWaterMark = uxTaskGetStackHighWaterMark(NULL); 
#endif
  shell_sem = xSemaphoreCreateBinary();
    for (;;)
    {
			/* shell 指令，未接收就挂起任务 */
			if (xSemaphoreTake(shell_sem, portMAX_DELAY) == pdTRUE) {
				Shell_Exec();
				DEBUG_INFO("Shell cmd Ok\n");
#ifdef STACK_PRINT
    uint32_t ulStackRemaining = uxHighWaterMark * 4;
		DEBUG_INFO("%d bytes short of overflow.\r\n", ulStackRemaining);
#endif
			}
    }
}

/**
 * @brief 初始化shell命令处理
 * @param uxPriority 打印任务的优先级。
 * @return 如果打印子系统成功初始化则返回pdPASS，否则返回pdFAIL。
 */
BaseType_t xShellInit(UBaseType_t uxPriority)
{
    // 验证优先级参数
    if (uxPriority > configMAX_PRIORITIES - 1)
    {
        return pdFAIL;
    }
    BaseType_t xReturn = pdPASS;
    // 创建shell调试队列，并加入队列集
		g_xQueueshell = xQueueCreate(SHELL_QUE_SIZE, sizeof(ActuatorTarget));
		xQueueAddToSet(g_xQueueshell, g_control_set);
    if (g_xQueueshell == NULL)
    {
        return pdFAIL;
    }
    // 创建打印任务
    BaseType_t xTaskRetVal = xTaskCreate(vShellExecTask,
                                         "ShellTask",
                                         configMINIMAL_STACK_SIZE*8,
                                         NULL,
                                         uxPriority,
                                         &xShellTaskHandle);
    if (xTaskRetVal != pdPASS)
    {
        DEBUG_INFO("Error creating shell task\n");
        xReturn = pdFAIL;
    }
    if (xReturn == pdFAIL)
    {
        vQueueDelete(g_xQueueshell);
        g_xQueueshell = NULL;
    }

    return xReturn;
}

void Shell_GetArgsFromISR(const char *line, uint16_t max_len)
{
		BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    // 1. 安全拷贝与边界检查
    if (max_len == 0) return;
    if (max_len >= SHELL_MAX_LINE_LEN) max_len = SHELL_MAX_LINE_LEN - 1;
    
    memcpy(args_copy, line, max_len);
    args_copy[max_len] = '\0'; // 强制封口
		cmd_len = max_len;
		xSemaphoreGiveFromISR(shell_sem, &xHigherPriorityTaskWoken);
}

/**
 * @brief 处理整块 DMA 缓冲区
 * @param line 缓冲区首地址，如 "RB 30.5\r\n"
 * @param max_len 实际接收长度
 */
void Shell_Exec() {
    char *argv[SHELL_MAX_ARGS];
    int argc = 0;
		
    // 1. 数据清洗：从后往前查找，把 \r \n 等不可见字符全部替换为 \0
    // 这样可以确保解析 30.5\r\n 时，得到的参数是干净的 "30.5"
    for (int i = cmd_len - 1; i >= 0; i--) {
        if (args_copy[i] == '\r' || args_copy[i] == '\n' || isspace((unsigned char)args_copy[i])) {
            args_copy[i] = '\0';
        } else {
            break; // 遇到第一个合法字符就停止，保留前面的空格用于后续分割
        }
    }

    // 3. 参数切割
    char *p = args_copy;
    while (*p && argc < SHELL_MAX_ARGS) {
        // 跳过前导空格
        while (*p && isspace((unsigned char)*p)) p++;
        if (*p == '\0') break;

        argv[argc++] = p; // 记录参数起始位置

        // 寻找当前参数的结尾
        while (*p && !isspace((unsigned char)*p)) p++;
        if (*p == '\0') break;

        *p++ = '\0'; // 放置结束符，准备寻找下一个参数
    }

    if (argc == 0) return;

    // 4. 指令匹配
    for (int i = 0; i < CMD_COUNT; i++) {
        if (strcmp(argv[0], cmd_list[i].cmd_name) == 0) {
            cmd_list[i].handler(argc, argv);
            return;
        }
    }
}

// --- 4. 具体指令回调实现 ---

static void shell_cmd_rb(int argc, char *argv[]) {
    if (argc < 2) {
        return;
    }
    
    // 提取数字：atof 将字符串转为 float
    float value = atof(argv[1]);
    static ActuatorTarget current_target = {-1.f,-1.f,-1.f,-1.f};
		current_target.RbTarget = value;
		xQueueSendFromISR(g_xQueueshell,&current_target,NULL);
}

