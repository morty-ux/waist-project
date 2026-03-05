/*
    ESP8266 TCP客户端 - Arduino版本
    功能：连接WiFi、连接上位机TCP服务器、收发数据

    硬件：ESP8266 NodeMCU
    上位机IP：192.168.3.25
    端口：8080

    使用方法：
    1. 修改下方的 WIFI_SSID 和 WIFI_PASSWORD 为你的WiFi
    2. 用Arduino IDE编译并烧录到ESP8266
    3. 打开串口监视器查看运行状态

    串口命令（通过USB串口）：
    - STATUS             查看状态
    - RESET              重启
    - HELP               帮助
*/

#include <ESP8266WiFi.h>
#include <WiFiClient.h>

// ==================== 函数声明 ====================

void connectWiFi();
void connectToServer();
void disconnectServer();
void receiveData();
void sendSensorData();
void sendPacket(byte cmdType, byte* data, int length);
void parsePacket(byte* packet, int length);
void sendStatusResponse();
void handleSerialCommand();
void processCommand(String cmd);

// ==================== 配置参数 ====================

// WiFi配置 - 请修改这里！
const char* WIFI_SSID = "rick的WiFi";        // 你的WiFi名称
const char* WIFI_PASSWORD = "12345678"; // 你的WiFi密码

// 上位机TCP服务器配置
const char* SERVER_HOST = "192.168.65.68";  // 上位机IP地址
const int SERVER_PORT = 8080;               // 上位机端口

// 通信协议
const byte START_BYTE = 0xAA;
const byte END_BYTE = 0x55;

// 命令类型 (上位机 -> ESP8266)
const byte CMD_SET_FORCE = 0x01;
const byte CMD_GET_STATUS = 0x02;
const byte CMD_RESET = 0x03;
const byte CMD_IDENTIFY = 0x04;

// 数据类型 (ESP8266 -> 上位机)
const byte DATA_SENSOR = 0x10;
const byte DATA_STATUS = 0x11;
const byte DATA_RESPONSE = 0x12;

// ==================== 全局变量 ====================

WiFiClient client;
bool isConnected = false;
unsigned long lastHeartbeat = 0;
unsigned long lastReconnectAttempt = 0;

// LED引脚 (NodeMCU上是D4，即GPIO2)
const int LED_PIN = D4;

// 传感器数据
int sensorValues[4] = {0, 0, 0, 0};  // LF, LB, RF, RB

// 串口命令缓冲区
String serialBuffer = "";

// ==================== 初始化 ====================

void setup() {
    // 初始化LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);  // LED低电平点亮

    // 初始化串口
    Serial.begin(115200);
    delay(500);

    Serial.println("");
    Serial.println("==================================");
    Serial.println("ESP8266 TCP Client - Arduino");
    Serial.println("==================================");
    Serial.println("输入 HELP 查看命令帮助");
    Serial.println("");

    // 初始化WiFi
    WiFi.mode(WIFI_STA);
    connectWiFi();
}

// ==================== 主循环 ====================

void loop() {
    // 处理串口命令
    handleSerialCommand();

    // WiFi连接管理
    if (WiFi.status() != WL_CONNECTED) {
        digitalWrite(LED_PIN, LOW);  // 快闪表示未连接WiFi
        delay(100);
        digitalWrite(LED_PIN, HIGH);
        delay(100);
        connectWiFi();
    }

    // TCP连接管理
    if (WiFi.status() == WL_CONNECTED) {
        if (!isConnected) {
            digitalWrite(LED_PIN, LOW);  // 慢闪表示正在连接
            delay(500);
            digitalWrite(LED_PIN, HIGH);
            delay(500);
            connectToServer();
        }

        if (isConnected) {
            digitalWrite(LED_PIN, LOW);  // 常亮表示已连接

            // 接收上位机命令
            receiveData();

            // 不再自动发送数据，等待上位机查询
        } else {
            // 断线重连
            if (millis() - lastReconnectAttempt >= 3000) {
                connectToServer();
                lastReconnectAttempt = millis();
            }
        }
    }

    delay(10);
}

// ==================== WiFi连接 ====================

void connectWiFi() {
    if (WiFi.status() == WL_CONNECTED) {
        return;
    }

    Serial.print("[INFO] 正在连接WiFi: ");
    Serial.println(WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry < 20) {
        delay(500);
        Serial.print(".");
        retry++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("");
        Serial.print("[OK] WiFi已连接! IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("");
        Serial.println("[ERROR] WiFi连接失败!");
    }
}

// ==================== TCP连接 ====================

void connectToServer() {
    if (client.connected()) {
        return;
    }

    Serial.print("[INFO] 连接服务器 ");
    Serial.print(SERVER_HOST);
    Serial.print(":");
    Serial.println(SERVER_PORT);

    if (client.connect(SERVER_HOST, SERVER_PORT)) {
        isConnected = true;
        Serial.println("[OK] 已连接服务器!");
    } else {
        isConnected = false;
        Serial.println("[ERROR] 连接失败");
    }
}

void disconnectServer() {
    if (client.connected()) {
        client.stop();
    }
    isConnected = false;
}

// ==================== 数据收发 ====================

// 接收数据缓冲区
byte packetBuffer[64];
int bufferIndex = 0;

void receiveData() {
    while (client.available()) {
        byte b = client.read();

        // 简单打印接收到的字节
        Serial.print(b, HEX);
        Serial.print(" ");
        
        // 协议解析 - 寻找起始符
        if (b == START_BYTE) {
            bufferIndex = 0;
            packetBuffer[bufferIndex++] = b;
        } else if (bufferIndex > 0 && bufferIndex < 64) {
            packetBuffer[bufferIndex++] = b;
            
            // 检查结束符
            if (b == END_BYTE && bufferIndex >= 4) {
                Serial.print(" | ");
                parsePacket(packetBuffer, bufferIndex);
                bufferIndex = 0;
            }
        }
    }
    Serial.println("");
}

void parsePacket(byte* packet, int length) {
    if (length < 4) return;
    
    byte cmd_type = packet[2];
    
    Serial.print("CMD:0x");
    Serial.print(cmd_type, HEX);
    
    // CMD_SET_FORCE (0x01): 设置力控参数
    if (cmd_type == CMD_SET_FORCE && length >= 5) {
        Serial.print(" CH:");
        Serial.write(packet[3]);
        Serial.print(" VAL:");
        Serial.print(packet[4]);
    }
}

void sendStatusResponse() {
    if (!isConnected) return;
    
    byte payload[1] = {1};
    sendPacket(DATA_STATUS, payload, 1);
    Serial.println("[TX] Status Response");
}

void sendSensorData() {
    if (!isConnected) {
        return;
    }

    // 模拟传感器数据（后续可替换为实际ADC读取）
    for (int i = 0; i < 4; i++) {
        sensorValues[i] = random(0, 101);
    }

    // 构建数据包
    byte payload[8];
    for (int i = 0; i < 4; i++) {
        payload[i * 2] = highByte(sensorValues[i]);
        payload[i * 2 + 1] = lowByte(sensorValues[i]);
    }

    sendPacket(DATA_SENSOR, payload, 8);
}

void sendPacket(byte cmdType, byte* data, int length) {
    if (!isConnected) {
        return;
    }

    // 发送起始符
    client.write(START_BYTE);

    // 发送长度
    client.write(length + 1);

    // 发送类型
    client.write(cmdType);

    // 发送数据
    for (int i = 0; i < length; i++) {
        client.write(data[i]);
    }

    // 计算校验和
    byte checksum = (length + 1) + cmdType;
    for (int i = 0; i < length; i++) {
        checksum += data[i];
    }
    checksum = checksum & 0xFF;

    // 发送校验和和结束符
    client.write(checksum);
    client.write(END_BYTE);
}

// ==================== 串口命令处理 ====================

void handleSerialCommand() {
    while (Serial.available()) {
        char c = Serial.read();

        if (c == '\n') {
            if (serialBuffer.length() > 0) {
                processCommand(serialBuffer);
                serialBuffer = "";
            }
        } else if (c != '\r') {
            serialBuffer += c;
        }
    }
}

void processCommand(String cmd) {
    cmd.trim();
    cmd.toUpperCase();

    if (cmd == "STATUS") {
        Serial.println("\n=== 系统状态 ===");
        Serial.print("[WiFi] ");
        if (WiFi.status() == WL_CONNECTED) {
            Serial.print("已连接: ");
            Serial.println(WiFi.localIP());
        } else {
            Serial.println("未连接");
        }

        Serial.print("[TCP] ");
        Serial.println(isConnected ? "已连接" : "未连接");

        Serial.print("[目标] ");
        Serial.print(SERVER_HOST);
        Serial.print(":");
        Serial.println(SERVER_PORT);
    }
    else if (cmd == "HELP") {
        Serial.println("\n=== 命令帮助 ===");
        Serial.println("STATUS    查看系统状态");
        Serial.println("RESET     重启设备");
        Serial.println("HELP      显示帮助");
    }
    else if (cmd == "RESET") {
        Serial.println("\n[INFO] 正在重启...");
        ESP.restart();
    }
    else if (cmd.length() > 0) {
        Serial.print("[ERROR] 未知命令: ");
        Serial.println(cmd);
    }
}
