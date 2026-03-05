# coding: utf-8
"""
TCP服务器模块
作为TCP服务器接收ESP8266连接，与ESP8266进行通信
"""

import socket
import threading
from PySide6.QtCore import QObject, Signal


class TCPServer(QObject):
    """
    TCP服务器

    功能:
    - 监听指定端口,接收ESP8266连接
    - 与ESP8266收发数据
    - 管理连接状态
    """

    # 信号定义
    client_connected = Signal(str, int)      # 客户端连接 (IP地址, 端口)
    client_disconnected = Signal()          # 客户端断开
    data_received = Signal(int, list)        # 接收到数据 (类型, 数据)
    error_occurred = Signal(str)             # 发生错误

    def __init__(self, host='0.0.0.0', port=8080):
        """
        初始化TCP服务器

        Args:
            host (str): 监听IP地址, '0.0.0.0'表示监听所有网卡
            port (int): 监听端口
        """
        super().__init__()
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.is_listening = False
        self.is_connected = False
        self.accept_thread = None
        self.receive_thread = None

    def start(self):
        """
        启动TCP服务器

        开始监听连接请求

        Returns:
            bool: 启动是否成功
        """
        if self.is_listening:
            return True

        try:
            # 创建TCP服务器socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 允许地址重用 (避免端口占用)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # 绑定地址和端口
            self.server_socket.bind((self.host, self.port))
            # 开始监听,最大连接数1
            self.server_socket.listen(1)
            # 设置超时,便于退出
            self.server_socket.settimeout(1.0)

            self.is_listening = True

            # 启动接受连接的线程
            self.accept_thread = threading.Thread(target=self._accept_client, daemon=True)
            self.accept_thread.start()

            return True

        except Exception as e:
            self.error_occurred.emit(f"启动服务器失败: {str(e)}")
            return False

    def stop(self):
        """
        停止TCP服务器

        关闭所有连接和socket
        """
        self.is_listening = False

        # 关闭客户端连接
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None

        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None

        self.is_connected = False

    def _accept_client(self):
        """
        接受客户端连接 (线程函数)

        持续监听并接受ESP8266连接
        """
        while self.is_listening:
            try:
                # 接受连接 (会阻塞)
                client_socket, client_address = self.server_socket.accept()
                self.client_socket = client_socket
                self.client_address = client_address
                self.is_connected = True

                # 发送连接成功信号
                ip, port = client_address
                self.client_connected.emit(ip, port)

                # 设置客户端socket超时
                client_socket.settimeout(0.5)

                # 启动接收数据线程
                self.receive_thread = threading.Thread(
                    target=self._receive_data,
                    daemon=True
                )
                self.receive_thread.start()

            except socket.timeout:
                # 超时继续循环
                continue
            except Exception as e:
                if self.is_listening:
                    self.error_occurred.emit(f"接受连接错误: {str(e)}")
                break

        # 监听停止,断开客户端
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        self.is_connected = False

    def _receive_data(self):
        """
        接收客户端数据 (线程函数)

        持续接收ESP8266发送的数据
        """
        while self.is_connected and self.client_socket:
            try:
                # 接收数据
                data = self.client_socket.recv(1024)

                if not data:
                    # 客户端断开
                    break

                # 解析数据包
                from .protocol import Protocol
                data_type, payload, checksum = Protocol.parse_packet(data)
                if data_type is not None:
                    self.data_received.emit(data_type, payload)

            except socket.timeout:
                continue
            except Exception as e:
                if self.is_connected:
                    self.error_occurred.emit(f"接收数据错误: {str(e)}")
                break

        # 连接断开
        self.is_connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None

        self.client_disconnected.emit()

    def send_data(self, data_type, data=None):
        """
        发送数据到客户端

        Args:
            data_type (int): 数据类型
            data (list): 数据载荷

        Returns:
            bool: 发送是否成功
        """
        if not self.is_connected or not self.client_socket:
            return False

        try:
            from .protocol import Protocol
            packet = Protocol.build_packet(data_type, data)
            self.client_socket.sendall(packet)
            return True

        except Exception as e:
            self.error_occurred.emit(f"发送失败: {str(e)}")
            self.is_connected = False
            self.client_disconnected.emit()
            return False

    def send_command(self, cmd_type, data=None):
        """
        发送命令到客户端 (send_data的别名)

        Args:
            cmd_type (int): 命令类型
            data (list): 命令数据

        Returns:
            bool: 发送是否成功
        """
        return self.send_data(cmd_type, data)

    def get_status(self):
        """
        获取连接状态

        Returns:
            dict: 状态信息
        """
        return {
            'is_listening': self.is_listening,
            'is_connected': self.is_connected,
            'client_address': self.client_address,
            'host': self.host,
            'port': self.port
        }
