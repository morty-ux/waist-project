# STM32L4 四推杆控制节点

## 1. 项目概述

基于 **STM32L4 + FreeRTOS** 的四推杆控制项目。

| 推杆 | PWM通道 | ADC通道 | 状态 |
|------|---------|---------|------|
| RB（右后） | TIM4 CH1/CH2 (PD15/PD14) | ADC1 IN8 (PA3) | ✅ 闭环控制 |
| RF（右前） | TIM4 CH3/CH4 (PD12/PD13) | ADC1 IN7 (PA2) | ✅ 闭环控制 |
| LF（左前） | TIM5 CH1/CH2 (PF6/PF7) | ADC1 IN2 (PC1) | ✅ 闭环控制 |
| LB（左后） | TIM5 CH3/CH4 (PF8/PF9) | ADC1 IN3 (PC2) | ✅ 闭环控制 |

---

## 2. 硬件接口

### TIM PWM（推杆驱动）
| 推杆 | 定时器 | 通道 | IO |
|------|--------|------|-----|
| RB | TIM4 | CH1/CH2 | PD15/PD14 |
| RF | TIM4 | CH3/CH4 | PD12/PD13 |
| LF | TIM5 | CH1/CH2 | PF6/PF7 |
| LB | TIM5 | CH3/CH4 | PF8/PF9 |

### ADC1 DMA（位置反馈）
| 推杆 | 通道 | IO |
|------|------|-----|
| RF | IN7 | PA2 |
| RB | IN8 | PA3 |
| LB | IN3 | PC2 |
| LF | IN2 | PC1 |

### 串口
| 功能 | 外设 | IO | 波特率 |
|------|------|-----|--------|
| Shell/Log | LPUART1 | PG7/PG8 | 209700 |
| ESP8266 | USART1 | PG9/PG10 | 115200 |

---

## 3. 软件架构

### 核心文件
| 文件 | 作用 |
|------|------|
| `freertos.c` | 任务创建、PID控制主循环 |
| `driver_actuator.c` | 推杆抽象、PWM控制、ADC反馈 |
| `driver_frame.c` | TCP二进制协议解析 |
| `driver_shell.c` | 本地Shell命令 |
| `driver_ESP01s.c` | ESP8266 AT指令、TCP Server |
| `driver_irq.c` | HAL回调分发 |

### 任务
| 任务 | 优先级 | 功能 |
|------|--------|------|
| defaultTask | Normal | ESP初始化、LED闪烁、数据上传 |
| pidControlTask | Realtime | 读取目标 → 4路PID计算 → PWM输出 |

---

## 4. 控制链路

### Shell控制（本地）
```
LPUART1 DMA → Shell解析 → shell队列 → pidControlTask → 4路PID → PWM
```

### TCP控制（Wi-Fi）
```
ESP8266 +IPD → Frame解析 → frame队列 → pidControlTask → 4路PID → PWM
```

### 反馈链路
```
ADC1 DMA (4通道) → Actuator_UpdateFeedback → current_pos_mm → PID
```

---

## 5. 协议格式

**控制帧（21字节）**
```
[0]   head   = 0xA5
[1]   func   = 0xCC
[2]   len    = 0x10
[3:6] rb     = float
[7:10] rf    = float
[11:14] lb   = float
[15:18] lf   = float
[19]  check  = ~(head + func + data)
[20]  tail   = 0x5A
```

### Shell命令
```
RB <float>   // 设置RB目标值
RF <float>   // 设置RF目标值
LF <float>   // 设置LF目标值
LB <float>   // 设置LB目标值
```

---

## 6. 待完成

- [ ] 上传真实状态（非测试值）
- [ ] 异常保护/急停

---

## 7. 快速开始

1. 连接LPUART1（Shell/Log，209700）
2. 或连接WiFi `EnvMonitor` → TCP `8080`
3. 发送控制帧或Shell命令控制推杆
