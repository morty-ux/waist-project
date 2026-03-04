# coding: utf-8
"""
ESP8266通信客户端
负责与ESP8266建立TCP连接和收发数据
"""

import socket
import threading
from PySide6.QtCore import QObject, Signal
from .protocol import Protocol


class ESP8266Client(QObject):
    """ESP8266通信客户端"""

    # 信号定义
    connected = Signal()                    # 连接成功
    disconnected = Signal()                 # 断开连接
    data_received = Signal(int, list)       # 接收到数据 (类型, 数据)
    error_occurred = Signal(str)            # 发生错误

    def __init__(self, host='192.168.1.100', port=8080):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = None
        self.is_connected = False
        self.receive_thread = None

    def connect(self):
        """连接到ESP8266"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            self.connected.emit()

            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._receive_data, daemon=True)
            self.receive_thread.start()

            return True
        except Exception as e:
            self.error_occurred.emit(f"连接失败: {str(e)}")
            return False

    def disconnect(self):
        """断开连接"""
        self.is_connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.disconnected.emit()

    def send_command(self, cmd_type, data=None):
        """发送命令"""
        if not self.is_connected:
            self.error_occurred.emit("未连接到设备")
            return False

        try:
            packet = Protocol.build_packet(cmd_type, data)
            self.socket.sendall(packet)
            return True
        except Exception as e:
            self.error_occurred.emit(f"发送失败: {str(e)}")
            self.disconnect()
            return False

    def set_force(self, channel, value):
        """设置力控参数"""
        data = [ord(channel[0]), value]  # 通道字母, 值
        return self.send_command(Protocol.CMD_SET_FORCE, data)

    def reset_system(self):
        """系统复位"""
        return self.send_command(Protocol.CMD_RESET)

    def identify_parameters(self):
        """参数自动辨识"""
        return self.send_command(Protocol.CMD_IDENTIFY)

    def _receive_data(self):
        """接收数据线程"""
        while self.is_connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break

                # 解析数据包
                data_type, payload, checksum = Protocol.parse_packet(data)
                if data_type is not None:
                    self.data_received.emit(data_type, payload)

            except socket.timeout:
                continue
            except Exception as e:
                self.error_occurred.emit(f"接收数据错误: {str(e)}")
                break

        self.disconnect()
