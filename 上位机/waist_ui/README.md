# 康复医疗仪表盘

基于PySide6和QFluentWidgets的康复医疗设备监控上位机系统，支持ESP8266通信和实时数据监测。

## 项目简介

本项目是一个现代化的康复医疗仪表盘系统，用于实时监测和控制康复设备。系统采用模块化设计，界面美观易用，支持与ESP8266设备进行TCP Socket通信，实现力控参数调节、电机推杆控制等功能。

### 主要功能

- **数据监测界面**：实时显示四个电机通道（左前LF、右前RF、左后LB、右后RB）的推杆长度数据
- **力控参数调节**：通过滑动条和数字框精确控制各通道的参数（0-100）
- **系统状态监控**：实时显示设备连接状态和通讯状态
- **快捷指令**：支持参数自动辨识和系统复位功能
- **通信日志**：独立的通信日志界面，支持命令发送
- **多界面支持**：包含康复训练、趣味游戏、用户自定义等扩展界面

### 技术栈

- **GUI框架**：PySide6 (Qt for Python)
- **UI组件库**：QFluentWidgets
- **通信协议**：TCP Socket (自定义二进制协议)
- **编程语言**：Python 3.10+
- **下位机**：ESP8266 NodeMCU (Arduino)

## 项目结构

```
waist_ui/
├── main.py                          # 主程序入口
├── README.md                       # 项目说明文档
├── config/                         # 配置模块
│   ├── __init__.py
│   └── settings.py                 # 配置管理
├── ui/                            # UI模块
│   ├── __init__.py
│   ├── main_window.py              # MainWindow类（主窗口，5个Tab）
│   ├── data_monitor.py             # DataMonitorInterface和StatusCard类
│   ├── log_interface.py            # LogInterface（通信日志界面）
│   ├── rehab_training.py           # RehabTrainingInterface（康复训练界面）
│   ├── fun_game.py                # FunGameInterface（趣味游戏界面）
│   └── user_custom.py             # UserCustomInterface（用户自定义界面）
├── communication/                  # 通信模块
│   ├── __init__.py
│   ├── tcp_server.py              # TCP服务器（接收ESP8266连接）
│   ├── protocol.py                # 通信协议定义
│   ├── communication_manager.py    # 通信管理器
│   └── esp8266_client.py          # TCP客户端（旧版本）
├── data/                          # 数据处理模块
│   ├── __init__.py
│   └── sensor_data.py             # 传感器数据处理
└── resource/                      # 资源文件
    ├── light/                     # 浅色主题
    │   └── demo.qss
    ├── dark/                      # 深色主题
    │   └── demo.qss
    └── body.png                   # 人体图片
```

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Windows 操作系统（推荐）
- 网络连接（用于ESP8266通信）

### 安装依赖

```bash
pip install PySide6 qfluentwidgets
```

### 运行程序

```bash
cd waist_ui
python main.py
```

## 界面说明

### 界面1：数据监测（主页）

采用**非对称双栏布局 (70% 可视化 : 30% 控制区)**：

**左侧区域 - 患者数字孪生区**
- 使用 `ElevatedCardWidget` 作为容器（白色背景、带阴影）
- 中央放置人体剪影图
- 四个悬浮状态卡片分布在人体图周围：
  - 左前(LF)、右前(RF)、左后(LB)、右后(RB)
- 每个卡片包含：部位名称、数值、进度条、状态徽章

**右侧区域 - 指挥控制中心**

1. **连接状态**
   - 显示设备连接状态（已连接/未连接）
   - 显示设备IP地址

2. **力控参数调节**
   - 四个滑动条分别控制LF、LB、RF、RB四个通道
   - 每个滑动条旁边有数字框，可精确输入数值
   - 滑动条和数字框双向绑定，实时同步

3. **快捷指令**
   - **参数自动辨识**：点击后自动识别设备参数
   - **系统复位**：将所有滑动条和状态卡片重置为0

### 界面2：通信日志

- 日志显示区域（彩色分级：INFO/WARNING/ERROR/DEBUG）
- 命令输入框（可发送自定义命令）
- 清空日志按钮

### 界面3-5

康复训练、趣味游戏、用户自定义界面（预留）

## 通信协议

### 数据包格式

```
[起始符][长度][类型][数据][校验和][结束符]
  0xAA    1字节  1字节  N字节   1字节   0x55
```

### 命令类型 (上位机 → ESP8266)

| 命令码 | 功能 |
|--------|------|
| 0x01 | 设置力控参数 |
| 0x02 | 获取状态 |
| 0x03 | 系统复位 |
| 0x04 | 参数自动辨识 |

### 数据类型 (ESP8266 → 上位机)

| 数据码 | 功能 |
|--------|------|
| 0x10 | 传感器/电机数据 |
| 0x11 | 状态数据 |
| 0x12 | 响应数据 |

### 通信流程

**控制命令（下行）：**
```
UI → CommunicationManager → TCPServer → ESP8266
```

**数据接收（上行）：**
```
ESP8266 → TCPServer → Protocol → CommunicationManager → UI
```

## ESP8266配置

### 硬件

- ESP8266 NodeMCU
- 连接2.4G WiFi热点

### 烧录

1. 使用Arduino IDE打开 `ESP8266CODE/mian.cpp`
2. 修改WiFi配置：
   ```cpp
   const char* WIFI_SSID = "你的WiFi名称";
   const char* WIFI_PASSWORD = "你的WiFi密码";
   ```
3. 修改上位机IP：
   ```cpp
   const char* SERVER_HOST = "192.168.x.x";  // 上位机IP地址
   ```
4. 烧录到ESP8266

### 串口命令

| 命令 | 功能 |
|------|------|
| STATUS | 查看系统状态 |
| RESET | 重启设备 |
| HELP | 显示帮助 |

## 当前状态

| 功能 | 状态 |
|------|------|
| ESP8266 WiFi连接 | ✅ 正常 |
| TCP通信 | ✅ 已建立 |
| 上位机运行 | ✅ 正常 |
| 通信协议 | ✅ 数据已到达ESP8266 |
| 命令解析 | ✅ 正在验证 |

## 配置信息

- ESP8266 WiFi: WIFI305 / 2024305YSU
- 上位机IP: 192.168.3.25
- ESP8266 IP: 192.168.65.99
- TCP端口: 8080

## 开发规范

### 组件使用规范

- 所有文本使用QFluentWidgets字体规范 (`TitleLabel`, `BodyLabel`, `CaptionLabel`)
- 所有图标使用 `FluentIcon`
- 所有按钮使用 `PushButton` / `PrimaryPushButton`
- 所有滑动条使用 `Slider`
- 滑动条和数字框使用 `blockSignals()` 避免循环触发

### 沟通规范

- 修改代码前必须先提问确认需求
- 需求不明确时必须停止，直到完全理解
- 修改完成后必须告知如何验证

## 待开发功能

- [ ] 压力传感器数据支持
- [ ] 康复训练模式
- [ ] 趣味游戏功能
- [ ] 用户自定义功能
- [ ] 数据记录和导出
- [ ] 自动重连机制

## 更新日志

### v1.1.0 (2026-03-05)

**新增功能：**
- 实现与ESP8266的TCP通信
- 添加通信日志界面
- 添加命令发送功能
- 完善协议解析

**ESP8266端：**
- Arduino版本实现
- WiFi连接
- TCP客户端
- 命令协议解析

### v1.0.0 (2026-02-05)

**新增功能：**
- 初始版本发布
- 实现数据监测界面
- 实现力控参数调节功能
- 实现系统状态监控
- 实现快捷指令功能
