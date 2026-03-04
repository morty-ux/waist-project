# coding:utf-8
import socket
import threading
from datetime import datetime
from PySide6.QtCore import Signal, QObject

try:
    import bluetooth
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False
    bluetooth = None


class ESP8266Communicator(QObject):
    """ ESP8266通信管理类 - 只负责WiFi通信 """
    
    msgReceived = Signal(str)
    connStatusChanged = Signal(bool, str)
    
    def __init__(self):
        super().__init__()
        self.socket = None
        self.is_connected = False
        self.receive_thread = None
        self.ip_address = ""
        self.port = 0
        self.device_name = "ESP8266"
    
    def establish_connection(self, ip_address, port):
        """连接到ESP8266设备"""
        try:
            self.ip_address = ip_address
            self.port = port
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            
            self.socket.connect((ip_address, port))
            
            self.is_connected = True
            
            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.msgReceived.emit(f"[{timestamp}] [系统] 已连接到 {ip_address}:{port}\n")
            
            self.connStatusChanged.emit(True, f"ESP8266: {ip_address}")
            
            return True
            
        except Exception as e:
            error_msg = f"无法连接到ESP8266: {str(e)}"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.msgReceived.emit(f"[{timestamp}] [错误] {error_msg}\n")
            self.connStatusChanged.emit(False, "")
            
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            
            return False
    
    def close_connection(self):
        """断开ESP8266连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.is_connected = False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.msgReceived.emit(f"[{timestamp}] [系统] 已断开连接\n")
        self.connStatusChanged.emit(False, "")
    
    def receive_messages(self):
        """接收ESP8266消息的线程函数"""
        buffer = ""
        while self.is_connected and self.socket:
            try:
                data = self.socket.recv(1024).decode('utf-8', errors='ignore')
                if not data:
                    break
                
                buffer += data
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.msgReceived.emit(f"[{timestamp}] [ESP8266] {line.strip()}\n")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_connected:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.msgReceived.emit(f"[{timestamp}] [错误] 接收消息失败: {str(e)}\n")
                break
        
        if self.is_connected:
            self.close_connection()
    
    def send_message(self, message):
        """向ESP8266发送消息"""
        if not self.is_connected:
            return False
        
        try:
            if not message.endswith('\n'):
                message += '\n'
            
            self.socket.send(message.encode('utf-8'))
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.msgReceived.emit(f"[{timestamp}] [发送] {message.strip()}\n")
            
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.msgReceived.emit(f"[{timestamp}] [错误] 发送消息失败: {str(e)}\n")
            self.close_connection()
            return False
    
    def get_connection_info(self):
        """获取当前连接信息"""
        return {
            'connected': self.is_connected,
            'device_name': self.device_name,
            'ip_address': self.ip_address,
            'port': self.port
        }
    
    def cleanup(self):
        """清理资源"""
        self.close_connection()


class BluetoothCommunicator(QObject):
    """ 蓝牙通信管理类 """
    
    msgReceived = Signal(str)
    connStatusChanged = Signal(bool, str)
    devicesFound = Signal(list)
    
    def __init__(self):
        super().__init__()
        self.socket = None
        self.is_connected = False
        self.receive_thread = None
        self.device_address = ""
        self.device_name = ""
        self.scan_thread = None
    
    def is_available(self):
        """检查蓝牙模块是否可用"""
        return BLUETOOTH_AVAILABLE
    
    def scan_devices(self):
        """扫描附近的蓝牙设备"""
        if not BLUETOOTH_AVAILABLE:
            self.devicesFound.emit([])
            self.msgReceived.emit("[提示] 蓝牙功能在Windows上需要安装PyBluez库\n")
            return
        
        self.scan_thread = threading.Thread(target=self._scan_worker, daemon=True)
        self.scan_thread.start()
    
    def _scan_worker(self):
        """扫描蓝牙设备的后台线程"""
        try:
            devices = bluetooth.discover_devices(duration=8, lookup_names=True, lookup_class=True)
            device_list = []
            for addr, name, device_class in devices:
                device_list.append({
                    'address': addr,
                    'name': name,
                    'class': device_class
                })
            self.devicesFound.emit(device_list)
        except Exception as e:
            self.msgReceived.emit(f"[错误] 扫描蓝牙设备失败: {str(e)}\n")
    
    def establish_connection(self, device_address, device_name=""):
        """连接到蓝牙设备"""
        if not BLUETOOTH_AVAILABLE:
            self.msgReceived.emit("[提示] 蓝牙功能在Windows上需要安装PyBluez库\n")
            self.connStatusChanged.emit(False, "蓝牙不可用")
            return False
        
        try:
            self.device_address = device_address
            self.device_name = device_name or device_address
            
            self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.socket.settimeout(10)
            
            self.socket.connect((device_address, 1))
            
            self.is_connected = True
            
            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.msgReceived.emit(f"[{timestamp}] [系统] 已连接到蓝牙设备: {self.device_name}\n")
            
            self.connStatusChanged.emit(True, f"蓝牙: {self.device_name}")
            
            return True
            
        except Exception as e:
            error_msg = f"无法连接到蓝牙设备: {str(e)}"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.msgReceived.emit(f"[{timestamp}] [错误] {error_msg}\n")
            self.connStatusChanged.emit(False, "")
            
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            
            return False
    
    def close_connection(self):
        """断开蓝牙连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.is_connected = False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.msgReceived.emit(f"[{timestamp}] [系统] 已断开蓝牙连接\n")
        self.connStatusChanged.emit(False, "")
    
    def receive_messages(self):
        """接收蓝牙消息的线程函数"""
        if not BLUETOOTH_AVAILABLE:
            return
            
        buffer = ""
        while self.is_connected and self.socket:
            try:
                data = self.socket.recv(1024).decode('utf-8', errors='ignore')
                if not data:
                    break
                
                buffer += data
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.msgReceived.emit(f"[{timestamp}] [蓝牙] {line.strip()}\n")
                
            except Exception as e:
                if self.is_connected:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.msgReceived.emit(f"[{timestamp}] [错误] 接收消息失败: {str(e)}\n")
                break
        
        if self.is_connected:
            self.close_connection()
    
    def send_message(self, message):
        """向蓝牙设备发送消息"""
        if not self.is_connected:
            return False
        
        try:
            if not message.endswith('\n'):
                message += '\n'
            
            self.socket.send(message.encode('utf-8'))
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.msgReceived.emit(f"[{timestamp}] [发送] {message.strip()}\n")
            
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.msgReceived.emit(f"[{timestamp}] [错误] 发送消息失败: {str(e)}\n")
            self.close_connection()
            return False
    
    def get_connection_info(self):
        """获取当前连接信息"""
        return {
            'connected': self.is_connected,
            'device_name': self.device_name,
            'device_address': self.device_address
        }
    
    def cleanup(self):
        """清理资源"""
        self.close_connection()


class DeviceManager(QObject):
    """ 设备管理器 - 统一管理所有通信模块 """
    
    currentDeviceChanged = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.esp8266 = ESP8266Communicator()
        self.bluetooth = BluetoothCommunicator()
        self._current_device_type = ""
        self._current_device_name = ""
        
        self.esp8266.msgReceived.connect(self.on_message_received)
        self.esp8266.connStatusChanged.connect(self.on_esp8266_status_changed)
        self.bluetooth.msgReceived.connect(self.on_message_received)
        self.bluetooth.connStatusChanged.connect(self.on_bluetooth_status_changed)
    
    def on_message_received(self, message):
        """转发所有消息"""
        pass
    
    def on_esp8266_status_changed(self, connected, info):
        """ESP8266连接状态变化"""
        if connected:
            self._current_device_type = "ESP8266"
            self._current_device_name = info
        elif not self.bluetooth.is_connected:
            self._current_device_type = ""
            self._current_device_name = ""
        self.currentDeviceChanged.emit(self.get_current_device_info())
    
    def on_bluetooth_status_changed(self, connected, info):
        """蓝牙连接状态变化"""
        if connected:
            self._current_device_type = "Bluetooth"
            self._current_device_name = info
        elif not self.esp8266.is_connected:
            self._current_device_type = ""
            self._current_device_name = ""
        self.currentDeviceChanged.emit(self.get_current_device_info())
    
    def get_current_device_info(self):
        """获取当前连接的设备信息"""
        if self.esp8266.is_connected:
            return {
                'type': 'ESP8266',
                'name': f"ESP8266: {self.esp8266.ip_address}",
                'connected': True
            }
        elif self.bluetooth.is_connected:
            return {
                'type': 'Bluetooth',
                'name': f"蓝牙: {self.bluetooth.device_name}",
                'connected': True
            }
        else:
            return {
                'type': '',
                'name': '未连接',
                'connected': False
            }
    
    def disconnect_all(self):
        """断开所有连接"""
        self.esp8266.close_connection()
        self.bluetooth.close_connection()
    
    def send_message(self, message):
        """向当前设备发送消息"""
        if self.esp8266.is_connected:
            return self.esp8266.send_message(message)
        elif self.bluetooth.is_connected:
            return self.bluetooth.send_message(message)
        return False
    
    @property
    def is_connected(self):
        return self.esp8266.is_connected or self.bluetooth.is_connected
    
    @property
    def device_type(self):
        return self._current_device_type
    
    @property
    def device_name(self):
        return self._current_device_name
