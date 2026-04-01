#include "driver_shell.h"


extern QueueSetHandle_t g_control_set;

// --- 内部私有函数声明 ---
static void shell_cmd_rb(int argc, char *argv[]);
static void shell_cmd_rf(int argc, char *argv[]);
static void shell_cmd_lf(int argc, char *argv[]);
static void shell_cmd_lb(int argc, char *argv[]);

// --- 命令映射表：命令名 -> 处理函数 ---
static const shell_cmd_t cmd_list[] = {
    {"RB",   shell_cmd_rb,   "Set RB target. Usage: RB <float>"},
    {"RF",   shell_cmd_rf,   "Set RF target. Usage: RF <float>"},
    {"LF",   shell_cmd_lf,   "Set LF target. Usage: LF <float>"},
    {"LB",   shell_cmd_lb,   "Set LB target. Usage: LB <float>"},
};

#define CMD_COUNT (sizeof(cmd_list) / sizeof(shell_cmd_t))


// 接收缓冲区，存储原始输入行
static char args_copy[SHELL_MAX_LINE_LEN];
uint16_t cmd_len;

// Shell任务队列，用于传递解析后的命令参数
static QueueHandle_t g_xQueueshell;
// Shell任务句柄
static TaskHandle_t xShellTaskHandle = NULL;
// 信号量，用于触发Shell任务执行
static SemaphoreHandle_t shell_sem;


// 获取Shell队列句柄（供freertos.c使用）
QueueHandle_t get_shellQueueHandle(void)
{
	return g_xQueueshell;
}



/**
 * @brief Shell任务主函数
 *
 * 等待信号量触发，从队列获取参数，执行命令解析
 * 命令解析成功后向Shell队列发送目标值
 */
static void vShellExecTask(void *pvParameters)
{
#ifdef STACK_PRINT
		UBaseType_t uxHighWaterMark = uxTaskGetStackHighWaterMark(NULL);
#endif
  shell_sem = xSemaphoreCreateBinary();
    for (;;)
    {
			/* 等待信号量，收到触发后执行命令解析 */
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
 * @brief 初始化Shell任务
 * @param uxPriority 任务优先级
 * @return 初始化成功返回pdPASS，失败返回pdFAIL
 */
BaseType_t xShellInit(UBaseType_t uxPriority)
{
    // 检查优先级是否合法
    if (uxPriority > configMAX_PRIORITIES - 1)
    {
        return pdFAIL;
    }
    BaseType_t xReturn = pdPASS;

    // 创建Shell命令队列，消息类型为ActuatorTarget（四路目标值）
		g_xQueueshell = xQueueCreate(SHELL_QUE_SIZE, sizeof(ActuatorTarget));

    // 将Shell队列添加到Queue Set，以便ControlFunction同时监听多个队列
		xQueueAddToSet(g_xQueueshell, g_control_set);

    if (g_xQueueshell == NULL)
    {
        return pdFAIL;
    }

    // 创建Shell执行任务
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

/**
 * @brief 从中断接收数据，保存到缓冲区并触发Shell任务
 *
 * 被LPUART1的IDLE DMA中断回调调用
 * @param line 接收到的数据起始地址
 * @param max_len 实际接收长度
 */
void Shell_GetArgsFromISR(const char *line, uint16_t max_len)
{
		BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    // 安全检查：防止空指针或超长数据
    if (max_len == 0) return;
    if (max_len >= SHELL_MAX_LINE_LEN) max_len = SHELL_MAX_LINE_LEN - 1;

    // 复制数据到本地缓冲区
    memcpy(args_copy, line, max_len);
    args_copy[max_len] = '\0'; // 字符串结束符
		cmd_len = max_len;

    // 给出信号量，触发Shell任务执行
		xSemaphoreGiveFromISR(shell_sem, &xHigherPriorityTaskWoken);
}

/**
 * @brief 解析并执行Shell命令
 *
 * 接收格式如 "RB 30.5\r\n"
 * 解析出命令名和参数，调用对应的处理函数
 */
void Shell_Exec() {
    char *argv[SHELL_MAX_ARGS];
    int argc = 0;

    // 1. 去除行尾的\r\n等不可见字符
    for (int i = cmd_len - 1; i >= 0; i--) {
        if (args_copy[i] == '\r' || args_copy[i] == '\n' || isspace((unsigned char)args_copy[i])) {
            args_copy[i] = '\0';
        } else {
            break;
        }
    }

    // 2. 分割参数，以空格为分隔符
    char *p = args_copy;
    while (*p && argc < SHELL_MAX_ARGS) {
        // 跳过前导空格
        while (*p && isspace((unsigned char)*p)) p++;
        if (*p == '\0') break;

        argv[argc++] = p; // 记录参数起始位置

        // 找到当前参数结束位置
        while (*p && !isspace((unsigned char)*p)) p++;
        if (*p == '\0') break;

        *p++ = '\0'; // 截断当前参数，准备解析下一个
    }

    if (argc == 0) return;

    // 3. 命令匹配：根据命令名找到对应处理函数并调用
    for (int i = 0; i < CMD_COUNT; i++) {
        if (strcmp(argv[0], cmd_list[i].cmd_name) == 0) {
            cmd_list[i].handler(argc, argv);
            return;
        }
    }
}

// --- 命令处理函数实现 ---

// 共用结构体，每次只修改对应字段，其他保持不变
static ActuatorTarget target = {0};

/**
 * @brief RB命令处理：设置右后推杆目标值
 * @param argc 参数个数
 * @param argv 参数列表，argv[0]="RB", argv[1]="30.5"
 */
static void shell_cmd_rb(int argc, char *argv[]) {
    if (argc < 2) {
        return;
    }
    float value = atof(argv[1]);
    target.RbTarget = value;
    xQueueSend(g_xQueueshell, &target, 0);
}

/**
 * @brief RF命令处理：设置右前推杆目标值
 */
static void shell_cmd_rf(int argc, char *argv[]) {
    if (argc < 2) {
        return;
    }
    float value = atof(argv[1]);
    target.RfTarget = value;
    xQueueSend(g_xQueueshell, &target, 0);
}

/**
 * @brief LF命令处理：设置左前推杆目标值
 */
static void shell_cmd_lf(int argc, char *argv[]) {
    if (argc < 2) {
        return;
    }
    float value = atof(argv[1]);
    target.LfTarget = value;
    xQueueSend(g_xQueueshell, &target, 0);
}

/**
 * @brief LB命令处理：设置左后推杆目标值
 */
static void shell_cmd_lb(int argc, char *argv[]) {
    if (argc < 2) {
        return;
    }
    float value = atof(argv[1]);
    target.LbTarget = value;
    xQueueSend(g_xQueueshell, &target, 0);
}
