# coding: utf-8
"""
TCP客户端模块 - 复刻自C++版本
功能：
1. TCP连接/断开
2. 发送电机控制帧
3. 接收数据
4. 自动重连机制
"""

import socket
import struct
import threading
import time
from PySide6.QtCore import QObject, Signal


class TCPClient(QObject):
    """
    TCP客户端 - 对外接口

    信号：
    - connected: 连接成功
    - disconnected: 断开连接
    - rx_data_changed: 接收数据变化 (str)
    - raw_data_received: 原始数据接收 (bytes)
    - error_occurred: 错误发生 (str)
    - log_message: 日志消息 (level, message)
    """

    connected = Signal()
    disconnected = Signal()
    rx_data_changed = Signal(str)
    raw_data_received = Signal(bytes)
    error_occurred = Signal(str)
    log_message = Signal(str, str)

    def __init__(self, ip="192.168.4.1", port=8080):
        super().__init__()
        self._is_connected = False
        self._server_ip = ip
        self._server_port = port
        self._reconnect_enabled = True
        self._reconnect_interval = 5

        self._socket = None
        self._running = False
        self._receive_thread = None

        self._rcv_state = "ASCII"
        self._device_ip = ""

    def connect_to_server(self):
        """连接到服务器"""
        if self._is_connected:
            return

        self._running = True
        self._connect_to_server()

    def _connect_to_server(self):
        """连接到服务器（内部）"""
        if self._is_connected:
            return

        try:
            self.log_message.emit('INFO', f"正在连接 {self._server_ip}:{self._server_port}...")

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(10)
            self._socket.connect((self._server_ip, self._server_port))

            self._is_connected = True
            self.connected.emit()
            self.log_message.emit('INFO', f"已连接到 {self._server_ip}:{self._server_port}")

            self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._receive_thread.start()

        except Exception as e:
            self._is_connected = False
            error_msg = f"连接失败: {str(e)}"
            self.log_message.emit('ERROR', error_msg)
            self.error_occurred.emit(error_msg)

            if self._reconnect_enabled:
                self.log_message.emit('INFO', f"等待 {self._reconnect_interval} 秒后重连...")
                threading.Timer(self._reconnect_interval, self._connect_to_server).start()

    def _receive_loop(self):
        """接收数据循环"""
        while self._running and self._is_connected and self._socket:
            try:
                self._socket.settimeout(1.0)
                data = self._socket.recv(2048)

                if not data:
                    self._handle_disconnect()
                    break

                self.raw_data_received.emit(data)

                if self._rcv_state == "ASCII":
                    try:
                        data_str = data.decode('utf-8')
                    except:
                        data_str = data.decode('gbk', errors='ignore')
                else:
                    data_str = ' '.join(f'{b:02X}' for b in data).upper()

                self.rx_data_changed.emit(data_str)

            except socket.timeout:
                continue
            except Exception as e:
                self.log_message.emit('ERROR', f"接收错误: {str(e)}")
                self._handle_disconnect()
                break

    def _handle_disconnect(self):
        """处理断开连接"""
        if self._is_connected:
            self._is_connected = False
            self.disconnected.emit()
            self.log_message.emit('WARNING', "连接已断开")

            if self._reconnect_enabled:
                threading.Timer(self._reconnect_interval, self._connect_to_server).start()

    def disconnect(self):
        """断开连接"""
        self._reconnect_enabled = False
        self._running = False

        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None

        self._is_connected = False
        self.disconnected.emit()
        self.log_message.emit('INFO', "已断开连接")

    def send_data(self, data):
        """发送数据
        Args:
            data: bytes类型或str类型
        """
        if not self._is_connected or not self._socket:
            self.log_message.emit('WARNING', "未连接服务器")
            return False

        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            self._socket.sendall(data)
            return True
        except Exception as e:
            self.log_message.emit('ERROR', f"发送失败: {str(e)}")
            self._handle_disconnect()
            return False

    def send_motor_cmd(self, rb: float, rf: float, lb: float, lf: float):
        """发送电机控制帧
        格式: [A5] [CC] [10] [RB] [RF] [LB] [LF] [CS] [5A]
        """
        if not self._is_connected:
            return

        frame = bytearray()

        frame.append(0xA5)
        frame.append(0xCC)
        frame.append(0x10)

        frame.extend(struct.pack('<f', rb))
        frame.extend(struct.pack('<f', rf))
        frame.extend(struct.pack('<f', lb))
        frame.extend(struct.pack('<f', lf))

        checksum = 0
        checksum += frame[0]
        checksum += frame[1]
        for i in range(16):
            checksum += frame[3 + i]

        checksum = (~checksum) & 0xFF
        frame.append(checksum)

        frame.append(0x5A)

        self.send_data(bytes(frame))

    def send_text(self, text: str):
        """发送文本数据"""
        self.send_data(text.encode('utf-8'))

    def get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._device_ip = ip
            return ip
        except:
            return "127.0.0.1"

    @property
    def rcv_state(self):
        """接收数据格式"""
        return self._rcv_state

    @rcv_state.setter
    def rcv_state(self, value: str):
        """设置接收数据格式"""
        self._rcv_state = value

    @property
    def device_ip(self):
        """本地IP地址"""
        return self._device_ip

    @property
    def tcp_server_ip(self):
        """服务端IP"""
        return self._server_ip

    @property
    def tcp_server_port(self):
        """服务端端口"""
        return self._server_port

    def set_server(self, ip: str, port: int):
        """设置服务器地址"""
        self._server_ip = ip
        self._server_port = port

    def set_reconnect(self, enabled: bool, interval: int = 5):
        """设置自动重连"""
        self._reconnect_enabled = enabled
        self._reconnect_interval = interval

    @property
    def is_connected(self):
        return self._is_connected

    @property
    def server_ip(self):
        return self._server_ip

    @property
    def server_port(self):
        return self._server_port
