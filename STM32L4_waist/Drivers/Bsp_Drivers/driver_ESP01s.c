#include "driver_ESP01s.h"
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
#include "driver_frame.h"

// ---------------- 内部工具函数 ----------------

// 清除接收缓冲区
static void ESP8266_ClearRxBuffer(ESP8266_Device *dev)
{
    memset(dev->rx_buf, 0, RX_BUF_SIZE);
    dev->rx_len = 0;
}

// ---------------- 中断处理核心逻辑 ----------------

// 1. 开启接收 (初始化时调用)
void ESP8266_Receive_IT_Start(ESP8266_Device *dev)
{
    // 开启空闲中断
    __HAL_UART_ENABLE_IT(dev->huart, UART_IT_IDLE);
    // 开启接收中断（接收一个字节）
    HAL_UART_Receive_IT(dev->huart, &dev->temp_byte, 1);
}

// 2. 接收完成回调 (必须在 HAL_UART_RxCpltCallback 中调用本函数)
// 作用：将单字节搬运到大缓冲区
void ESP8266_RxCpltCallback(ESP8266_Device *dev)
{
    if (dev->rx_len < RX_BUF_SIZE - 1)
    {
        dev->rx_buf[dev->rx_len++] = dev->temp_byte;
        dev->rx_buf[dev->rx_len] = 0; // 保持字符串结尾，方便strstr
    }
    // 继续接收下一个字节
    HAL_UART_Receive_IT(dev->huart, &dev->temp_byte, 1);
}

// 3. 空闲中断处理 (必须在 stm32f1xx_it.c 的 USARTx_IRQHandler 中调用)
// 作用：一帧数据接收完毕，进行解析
void ESP8266_UART_IDLE_Handler(ESP8266_Device *dev)
{
    if (__HAL_UART_GET_FLAG(dev->huart, UART_FLAG_IDLE) != RESET)
    {
        __HAL_UART_CLEAR_IDLEFLAG(dev->huart);

        // 确保字符串结束符，防止 strstr 跑飞
        dev->rx_buf[dev->rx_len] = 0;

        // ---------------- 1. 解析 +IPD 数据 (新增逻辑) ----------------
        // 格式示例: +IPD,0,4:ASDA
        char *p_ipd = strstr((char *)dev->rx_buf, "+IPD,");
        if (p_ipd)
        {
            // 指针跳过 "+IPD," (5字节)
            p_ipd += 5;

            // --- A. 解析 Link ID ---
            // 此时 p_ipd 指向 "0,4:..."
            int id = atoi(p_ipd); // 获取ID

            // 寻找下一个逗号
            char *p_comma = strchr(p_ipd, ',');
            if (p_comma)
            {
                p_ipd = p_comma + 1; // 跳过逗号，指向 "4:..."

                // --- B. 解析 数据长度 ---
                uint16_t len = atoi(p_ipd);

                // 寻找冒号
                char *p_colon = strchr(p_ipd, ':');
                if (p_colon)
                {
                    // --- C. 定位数据内容 ---
                    uint8_t *p_data = (uint8_t *)(p_colon + 1); // 冒号后就是数据

                    // --- D. 调用用户回调 ---
                    // 这里我们通过回调把数据抛出去，不在这里做复杂业务逻辑
                    ESP8266_OnDataReceived(dev, id, p_data, len);
                }
            }
        }

        // ---------------- 2. 异步消息解析 ----------------
        char *p_con = strstr((const char *)dev->rx_buf, ",CONNECT");
        if (p_con && p_con > (char *)dev->rx_buf)
        {
            dev->link_id = *(p_con - 1) - '0';
        }
        else if (strstr((const char *)dev->rx_buf, ",CLOSED"))
        {
            dev->link_id = 0xFF;
        }

        // ---------------- 3. 同步指令响应 ----------------
        if (dev->cmd_state == CMD_WAITING && dev->expected_resp != NULL)
        {
            if (strstr((const char *)dev->rx_buf, dev->expected_resp))
            {
                dev->cmd_state = CMD_Done;
            }
            else if (strstr((const char *)dev->rx_buf, "ERROR"))
            {
                dev->cmd_state = CMD_Error;
            }
        }
    }
}

__weak void ESP8266_OnDataReceived(ESP8266_Device *dev, uint8_t link_id, uint8_t *data, uint16_t len)
{
    Frame_GetArgsFromISR(data,len);
}

// ---------------- 发送与控制逻辑 ----------------

// 发送AT指令并等待中断层面的标志位
static ESP8266_Status ESP8266_SendATCommand(ESP8266_Device *dev, const char *cmd,
                                            const char *expected_resp, uint32_t timeout_ms)
{

    // 1. 准备阶段
    ESP8266_ClearRxBuffer(dev);         // 清空旧数据
    dev->expected_resp = expected_resp; // 告诉中断我们在等什么
    dev->cmd_state = CMD_WAITING;       // 状态设为等待

#ifdef ESP8266_DEBUG
    DEBUG_INFO("[TX]: %s\n", cmd);
#endif

    // 2. 发送数据
    HAL_UART_Transmit(dev->huart, (uint8_t *)cmd, strlen(cmd), 100);

    // 3. 阻塞等待结果 (轮询 volatile 标志位)
    uint32_t start = xTaskGetTickCount();
    while ((xTaskGetTickCount() - start) < timeout_ms)
    {

        // 检查中断里是否修改了这个状态
        if (dev->cmd_state == CMD_Done)
        {
#ifdef ESP8266_DEBUG
            DEBUG_INFO("[RX OK]: %s\n", expected_resp);
#endif
            dev->expected_resp = NULL; // 清除期待
            return ESP8266_OK;
        }

        if (dev->cmd_state == CMD_Error)
        {
            dev->expected_resp = NULL;
            return ESP8266_ERROR_RESPONSE;
        }
    }

    // 4. 超时处理
    dev->expected_resp = NULL;
    return ESP8266_ERROR_TIMEOUT;
}

// 发送AT指令并等待中断层面的标志位
static ESP8266_Status ESP8266_SendATCommandIdx(ESP8266_Device *dev, const char *cmd,
                                               const char *expected_resp, uint32_t timeout_ms, uint8_t idx)
{

    // 1. 准备阶段
    ESP8266_ClearRxBuffer(dev);         // 清空旧数据
    dev->expected_resp = expected_resp; // 告诉中断我们在等什么
    dev->cmd_state = CMD_WAITING;       // 状态设为等待

#ifdef ESP8266_DEBUG
    DEBUG_INFO("[TX]: %s\n", cmd);
#endif

    // 2. 发送数据
    HAL_UART_Transmit(dev->huart, (uint8_t *)cmd, idx, 100);

    // 3. 阻塞等待结果 (轮询 volatile 标志位)
    uint32_t start = xTaskGetTickCount();
    while ((xTaskGetTickCount() - start) < timeout_ms)
    {

        // 检查中断里是否修改了这个状态
        if (dev->cmd_state == CMD_Done)
        {
#ifdef ESP8266_DEBUG
            DEBUG_INFO("[RX OK]: %s\n", expected_resp);
#endif
            dev->expected_resp = NULL; // 清除期待
            return ESP8266_OK;
        }

        if (dev->cmd_state == CMD_Error)
        {
            dev->expected_resp = NULL;
            return ESP8266_ERROR_RESPONSE;
        }
    }

    // 4. 超时处理
    dev->expected_resp = NULL;
    return ESP8266_ERROR_TIMEOUT;
}

// ---------------- 业务功能函数 (与原版基本一致) ----------------

ESP8266_Status ESP8266_Init(ESP8266_Device *dev, UART_HandleTypeDef *huart)
{
    dev->huart = huart;
    dev->link_id = 0xFF;
    dev->expected_resp = NULL;
    dev->cmd_state = CMD_IDLE;

    ESP8266_ClearRxBuffer(dev);
    ESP8266_Receive_IT_Start(dev); // 启动中断

    // 复位一下比较稳妥 (可选)
    // ESP8266_SendATCommand(dev, "AT+RST\r\n", "ready", 2000);

    if (ESP8266_SendATCommand(dev, "AT\r\n", "OK", 500) != ESP8266_OK)
        return ESP8266_ERROR_RESPONSE;

    ESP8266_SendATCommand(dev, "ATE0\r\n", "OK", 500);
    return ESP8266_OK;
}

ESP8266_Status ESP8266_InitAP(ESP8266_Device *dev, const ESP8266_AP_Config *ap_cfg)
{
    ESP8266_SendATCommand(dev, "AT+CWMODE=2\r\n", "OK", 1000);

    char cmd[128];
    sprintf(cmd, "AT+CWSAP=\"%s\",\"%s\",%d,%d\r\n",
            ap_cfg->ssid, ap_cfg->pwd, ap_cfg->channel, ap_cfg->encryption);

    return ESP8266_SendATCommand(dev, cmd, "OK", 3000);
}

ESP8266_Status ESP8266_CreateTCPServer(ESP8266_Device *dev, uint16_t port)
{
    char cmd[32];
    ESP8266_SendATCommand(dev, "AT+CIPMUX=1\r\n", "OK", 1000);

    sprintf(cmd, "AT+CIPSERVER=1,%d\r\n", port);
    return ESP8266_SendATCommand(dev, cmd, "OK", 1000);
}

ESP8266_Status ESP8266_SendData(ESP8266_Device *dev, const char *data)
{
    if (dev->link_id == 0xFF)
        return ESP8266_ERROR_CONNECT;

    char cmd[64];
    // 使用 sprintf 自动计算长度
    sprintf(cmd, "AT+CIPSEND=%d,%d\r\n", dev->link_id, (int)strlen(data));
    // 1. 发送长度指令，等待 ">"
    if (ESP8266_SendATCommand(dev, cmd, ">", 1000) == ESP8266_OK)
    {
        // 2. 发送实际数据，等待 "SEND OK"
        return ESP8266_SendATCommand(dev, data, "SEND OK", 2000);
    }
    return ESP8266_ERROR_RESPONSE;
}

ESP8266_Status ESP8266_SendDataIdx(ESP8266_Device *dev, const char *data, uint8_t idx)
{
    if (dev->link_id == 0xFF)
        return ESP8266_ERROR_CONNECT;

    char cmd[64];
    // 使用 sprintf 指定长度
    sprintf(cmd, "AT+CIPSEND=%d,%d\r\n", dev->link_id, idx);
    // 1. 发送长度指令，等待 ">"
    if (ESP8266_SendATCommand(dev, cmd, ">", 1000) == ESP8266_OK)
    {
        // 2. 发送实际数据，等待 "SEND OK"
        return ESP8266_SendATCommandIdx(dev, data, "SEND OK", 2000, idx);
    }
    return ESP8266_ERROR_RESPONSE;
}

/**
 * @brief 发送电机/传感器数据到上位机
 * @param dev ESP8266设备句柄
 * @param rb  右后数据
 * @param rf  右前数据
 * @param lb  左后数据
 * @param lf  左前数据
 */
void Upload_Data(ESP8266_Device *dev, float rb, float rf, float lb, float lf)
{
    // 1. 定义发送缓冲区
    // 大小计算: 头(1)+功能(1)+长度(1)+数据(16)+校验(1)+尾(1) = 21字节
    uint8_t send_buf[21];
    uint8_t idx = 0;

    // 2. 填充帧头 (Header)
    send_buf[idx++] = 0xA5;

    // 3. 填充功能位 (Function Code) - 0xCF 代表数据帧
    send_buf[idx++] = 0xCF;

    // 4. 填充数据长度 (Length)
    // 4个float，每个4字节，共16字节 (0x10)
    send_buf[idx++] = 16;

    // 5. 填充数据位 (Data Body)
    // 使用 memcpy 直接拷贝内存，避免指针强转带来的对齐问题
    // 注意：MCU通常是小端序(Little Endian)，PC(x86)也是小端序，直接拷贝即可
    memcpy(&send_buf[idx], &rb, 4);
    idx += 4;
    memcpy(&send_buf[idx], &rf, 4);
    idx += 4;
    memcpy(&send_buf[idx], &lb, 4);
    idx += 4;
    memcpy(&send_buf[idx], &lf, 4);
    idx += 4;

    // 6. 计算校验位 (Checksum)
    // 规则：~(帧头 + 功能位 + 数据位)  注意：你的C++代码里没加长度位
    uint8_t check_sum = 0;

    // 加帧头
    check_sum += send_buf[0];
    // 加功能位
    check_sum += send_buf[1];
    // 加数据位 (从第3个字节开始，长度为16)
    // 注意：跳过 send_buf[2] (长度位)，因为你的Qt解析代码 calculateChecksum 没加长度
    for (int i = 0; i < 16; i++)
    {
        check_sum += send_buf[3 + i];
    }

    // 取反
    check_sum = ~check_sum;

    // 7. 填充校验位和帧尾
    send_buf[idx++] = check_sum;
    send_buf[idx++] = 0x5A; // 帧尾

    // 8. 发送数据
    // !!! 注意 !!!
    // float 数据中经常包含 0x00，不能当做字符串发送 (不能用 strlen)
    // 必须调用支持指定长度的发送函数
    ESP8266_SendDataIdx(dev, (char *)send_buf, sizeof(send_buf));
}
