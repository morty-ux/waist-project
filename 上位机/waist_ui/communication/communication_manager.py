# coding: utf-8
"""
通信管理器
整合TCP服务器与界面，管理连接状态和通信日志
"""

from PySide6.QtCore import QObject, Signal, QTimer
from communication import TCPServer, Protocol


class CommunicationManager(QObject):
    """
    通信管理器

    功能:
    - 管理TCP服务器
    - 处理连接状态
    - 记录通信日志
    - 与UI交互
    """

    # 信号定义
    connection_changed = Signal(bool)           # 连接状态变化 (是否连接)
    sensor_data_received = Signal(dict)         # 收到传感器数据
    log_message = Signal(str, str)              # 日志消息 (级别, 内容)
    error_occurred = Signal(str)                 # 错误发生

    # 日志级别
    LOG_INFO = 'INFO'
    LOG_WARNING = 'WARNING'
    LOG_ERROR = 'ERROR'
    LOG_DEBUG = 'DEBUG'

    def __init__(self, host='0.0.0.0', port=8080):
        """
        初始化通信管理器

        Args:
            host (str): 监听IP地址
            port (int): 监听端口
        """
        super().__init__()
        self.host = host
        self.port = port
        self.tcp_server = None
        self.is_connected = False
        self.client_ip = None
        self.client_port = None
        self.auto_reconnect = True
        self.reconnect_timer = None
        self.reconnect_delay = 3000  # 3秒

        # 传感器数据缓存
        self.sensor_data = {
            'LF': 0,
            'LB': 0,
            'RF': 0,
            'RB': 0
        }

    def start(self):
        """
        启动通信管理器

        Returns:
            bool: 启动是否成功
        """
        try:
            # 创建TCP服务器
            self.tcp_server = TCPServer(self.host, self.port)

            # 连接信号
            self.tcp_server.client_connected.connect(self._on_client_connected)
            self.tcp_server.client_disconnected.connect(self._on_client_disconnected)
            self.tcp_server.data_received.connect(self._on_data_received)
            self.tcp_server.error_occurred.connect(self._on_error)

            # 启动服务器
            if self.tcp_server.start():
                self._log(self.LOG_INFO, f"TCP服务器已启动，监听端口: {self.port}")
                return True
            else:
                return False

        except Exception as e:
            self._log(self.LOG_ERROR, f"启动服务器失败: {str(e)}")
            self.error_occurred.emit(str(e))
            return False

    def stop(self):
        """
        停止通信管理器
        """
        if self.tcp_server:
            self.tcp_server.stop()
            self.tcp_server = None

        self.is_connected = False
        self.client_ip = None
        self.client_port = None
        self._log(self.LOG_INFO, "TCP服务器已停止")

    def _on_client_connected(self, ip, port):
        """
        客户端连接回调
        """
        self.is_connected = True
        self.client_ip = ip
        self.client_port = port
        self.connection_changed.emit(True)
        self._log(self.LOG_INFO, f"ESP8266已连接: {ip}:{port}")

    def _on_client_disconnected(self):
        """
        客户端断开回调
        """
        self.is_connected = False
        self.client_ip = None
        self.client_port = None
        self.connection_changed.emit(False)
        self._log(self.LOG_WARNING, "ESP8266已断开连接")

    def _on_data_received(self, data_type, payload):
        """
        收到数据回调
        """
        # DATA_SENSOR (0x10): 传感器数据
        if data_type == Protocol.DATA_SENSOR:
            sensor_data = Protocol.parse_sensor_data(payload)
            if sensor_data:
                self.sensor_data.update(sensor_data)
                self.sensor_data_received.emit(self.sensor_data)
                self._log(self.LOG_DEBUG, f"收到传感器数据: {sensor_data}")

        # DATA_STATUS (0x11): 状态数据
        elif data_type == Protocol.DATA_STATUS:
            self._log(self.LOG_DEBUG, f"收到状态数据: {payload}")

        # DATA_RESPONSE (0x12): 响应数据
        elif data_type == Protocol.DATA_RESPONSE:
            self._log(self.LOG_DEBUG, f"收到响应: {payload}")

    def _on_error(self, error_msg):
        """
        错误回调
        """
        self._log(self.LOG_ERROR, error_msg)
        self.error_occurred.emit(error_msg)

    def _log(self, level, message):
        """
        记录日志
        """
        self.log_message.emit(level, message)

    def send_command(self, cmd_type, data=None):
        """
        发送命令

        Args:
            cmd_type (int): 命令类型
            data (list): 数据

        Returns:
            bool: 发送是否成功
        """
        if not self.is_connected:
            self._log(self.LOG_WARNING, "未连接到设备")
            return False

        result = self.tcp_server.send_command(cmd_type, data)
        if result:
            self._log(self.LOG_DEBUG, f"发送命令: 0x{cmd_type:02X}")
        else:
            self._log(self.LOG_ERROR, f"发送命令失败: 0x{cmd_type:02X}")

        return result

    def set_force(self, channel, value):
        """
        设置力控参数

        Args:
            channel (str): 通道 ('LF', 'LB', 'RF', 'RB')
            value (int): 值 (0-100)

        Returns:
            bool: 发送是否成功
        """
        data = [ord(channel[0]), value]
        return self.send_command(Protocol.CMD_SET_FORCE, data)

    def get_status(self):
        """
        获取状态

        Returns:
            bool: 发送是否成功
        """
        return self.send_command(Protocol.CMD_GET_STATUS)

    def reset_system(self):
        """
        系统复位

        Returns:
            bool: 发送是否成功
        """
        return self.send_command(Protocol.CMD_RESET)

    def identify_parameters(self):
        """
        参数辨识

        Returns:
            bool: 发送是否成功
        """
        return self.send_command(Protocol.CMD_IDENTIFY)

    def enable_sensor(self, enabled=True):
        """
        开启/关闭传感器上报

        Args:
            enabled (bool): 是否开启

        Returns:
            bool: 发送是否成功
        """
        cmd = Protocol.CMD_SENSOR_ON if enabled else Protocol.CMD_SENSOR_OFF
        return self.send_command(cmd)

    def set_report_freq(self, freq):
        """
        设置上报频率

        Args:
            freq (int): 频率 (1-50 Hz)

        Returns:
            bool: 发送是否成功
        """
        return self.send_command(Protocol.CMD_SET_FREQ, [freq])

    def get_connection_info(self):
        """
        获取连接信息

        Returns:
            dict: 连接信息
        """
        return {
            'connected': self.is_connected,
            'ip': self.client_ip,
            'port': self.client_port,
            'sensor_data': self.sensor_data.copy()
        }
