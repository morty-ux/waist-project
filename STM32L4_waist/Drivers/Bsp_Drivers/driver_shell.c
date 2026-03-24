#include "driver_shell.h"


extern QueueSetHandle_t g_control_set;

// --- 内部私有函数声明 ---
static void shell_cmd_rb(int argc, char *argv[]);
static void shell_cmd_rf(int argc, char *argv[]);
static void shell_cmd_lf(int argc, char *argv[]);
static void shell_cmd_lb(int argc, char *argv[]);

// --- 命令映射表 ---
static const shell_cmd_t cmd_list[] = {
    {"RB",   shell_cmd_rb,   "Set RB target. Usage: RB <float>"},
    {"RF",   shell_cmd_rf,   "Set RF target. Usage: RF <float>"},
    {"LF",   shell_cmd_lf,   "Set LF target. Usage: LF <float>"},
    {"LB",   shell_cmd_lb,   "Set LB target. Usage: LB <float>"},
};

#define CMD_COUNT (sizeof(cmd_list) / sizeof(shell_cmd_t))


// ���ջ�����
static char args_copy[SHELL_MAX_LINE_LEN];
uint16_t cmd_len;

// ��Ϣ���о��
static QueueHandle_t g_xQueueshell;
// shell��������
static TaskHandle_t xShellTaskHandle = NULL;
// �������ź���
static SemaphoreHandle_t shell_sem;


// ������Ϣ���о��
QueueHandle_t get_shellQueueHandle(void)
{
	return g_xQueueshell;
}




/**
 * @brief ��ӡ���񣬸���Ӵ�ӡ�����л�ȡ��ӡ��Ϣ�����䷢�͵�UART��
 *
 * ��������� `xPrintQueue` �г��Ӵ�ӡ��Ϣ����ʹ�� `HAL_UART_Transmit()` ����Ϣ���ݴ��䵽UART��
 * �������������������ȴ��������п��õ���Ϣ��
 * �ڴ�����Ϣ�������ӳ�1��ʱ�ӽ��ģ������������������С�
 * ������ּ���� `print_init()` ������������Ӧֱ��������
 */
static void vShellExecTask(void *pvParameters)
{
#ifdef STACK_PRINT
		UBaseType_t uxHighWaterMark = uxTaskGetStackHighWaterMark(NULL); 
#endif
  shell_sem = xSemaphoreCreateBinary();
    for (;;)
    {
			/* shell ָ�δ���վ͹������� */
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
 * @brief ��ʼ��shell�����
 * @param uxPriority ��ӡ��������ȼ���
 * @return �����ӡ��ϵͳ�ɹ���ʼ���򷵻�pdPASS�����򷵻�pdFAIL��
 */
BaseType_t xShellInit(UBaseType_t uxPriority)
{
    // ��֤���ȼ�����
    if (uxPriority > configMAX_PRIORITIES - 1)
    {
        return pdFAIL;
    }
    BaseType_t xReturn = pdPASS;
    // ����shell���Զ��У���������м�
		g_xQueueshell = xQueueCreate(SHELL_QUE_SIZE, sizeof(ActuatorTarget));
		xQueueAddToSet(g_xQueueshell, g_control_set);
    if (g_xQueueshell == NULL)
    {
        return pdFAIL;
    }
    // ������ӡ����
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
    // 1. ��ȫ������߽���
    if (max_len == 0) return;
    if (max_len >= SHELL_MAX_LINE_LEN) max_len = SHELL_MAX_LINE_LEN - 1;
    
    memcpy(args_copy, line, max_len);
    args_copy[max_len] = '\0'; // ǿ�Ʒ��
		cmd_len = max_len;
		xSemaphoreGiveFromISR(shell_sem, &xHigherPriorityTaskWoken);
}

/**
 * @brief �������� DMA ������
 * @param line �������׵�ַ���� "RB 30.5\r\n"
 * @param max_len ʵ�ʽ��ճ���
 */
void Shell_Exec() {
    char *argv[SHELL_MAX_ARGS];
    int argc = 0;
		
    // 1. ������ϴ���Ӻ���ǰ���ң��� \r \n �Ȳ��ɼ��ַ�ȫ���滻Ϊ \0
    // ��������ȷ������ 30.5\r\n ʱ���õ��Ĳ����Ǹɾ��� "30.5"
    for (int i = cmd_len - 1; i >= 0; i--) {
        if (args_copy[i] == '\r' || args_copy[i] == '\n' || isspace((unsigned char)args_copy[i])) {
            args_copy[i] = '\0';
        } else {
            break; // ������һ���Ϸ��ַ���ֹͣ������ǰ��Ŀո����ں����ָ�
        }
    }

    // 3. �����и�
    char *p = args_copy;
    while (*p && argc < SHELL_MAX_ARGS) {
        // ����ǰ���ո�
        while (*p && isspace((unsigned char)*p)) p++;
        if (*p == '\0') break;

        argv[argc++] = p; // ��¼������ʼλ��

        // Ѱ�ҵ�ǰ�����Ľ�β
        while (*p && !isspace((unsigned char)*p)) p++;
        if (*p == '\0') break;

        *p++ = '\0'; // ���ý�������׼��Ѱ����һ������
    }

    if (argc == 0) return;

    // 4. ָ��ƥ��
    for (int i = 0; i < CMD_COUNT; i++) {
        if (strcmp(argv[0], cmd_list[i].cmd_name) == 0) {
            cmd_list[i].handler(argc, argv);
            return;
        }
    }
}

// --- 4. ����ָ��ص�ʵ�� ---

static void shell_cmd_rb(int argc, char *argv[]) {
    if (argc < 2) {
        return;
    }
    float value = atof(argv[1]);
    static ActuatorTarget current_target = {-1.f,-1.f,-1.f,-1.f};
		current_target.RbTarget = value;
		xQueueSend(g_xQueueshell, &current_target, 0);
}

static void shell_cmd_rf(int argc, char *argv[]) {
    if (argc < 2) {
        return;
    }
    float value = atof(argv[1]);
    static ActuatorTarget current_target = {-1.f,-1.f,-1.f,-1.f};
		current_target.RfTarget = value;
		xQueueSend(g_xQueueshell, &current_target, 0);
}

static void shell_cmd_lf(int argc, char *argv[]) {
    if (argc < 2) {
        return;
    }
    float value = atof(argv[1]);
    static ActuatorTarget current_target = {-1.f,-1.f,-1.f,-1.f};
		current_target.LfTarget = value;
		xQueueSend(g_xQueueshell, &current_target, 0);
}

static void shell_cmd_lb(int argc, char *argv[]) {
    if (argc < 2) {
        return;
    }
    float value = atof(argv[1]);
    static ActuatorTarget current_target = {-1.f,-1.f,-1.f,-1.f};
		current_target.LbTarget = value;
		xQueueSend(g_xQueueshell, &current_target, 0);
}

