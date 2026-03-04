# coding:utf-8
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QRect, QUrl, QDate, QTime, Signal
from PySide6.QtGui import (
    QIcon, QPainter, QImage, QBrush, QColor, QFont, 
    QDesktopServices, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QStackedWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QWidget, QTextEdit, QLineEdit, QListWidgetItem, QListWidget, QComboBox
)

from qfluentwidgets import (
    NavigationInterface, NavigationItemPosition, NavigationWidget, qrouter,
    SubtitleLabel, BodyLabel, TextEdit, CalendarPicker, 
    Slider, ProgressRing, CardWidget, TabWidget,
    PrimaryPushButton, PushButton, FluentIcon as FIF,
    MessageBox, isDarkTheme, InfoBar, SingleDirectionScrollArea
)

from qframelesswindow import FramelessWindow, StandardTitleBar

from comm_config import ESP8266Communicator, BluetoothCommunicator, DeviceManager


class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        self.hBoxLayout.setContentsMargins(0, 16, 0, 0)
        

class ChannelCard(QFrame):
    
    valueChanged = Signal(int)

    def __init__(self, channel_name, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 320)
        
        self.setStyleSheet("""
            ChannelCard {
                background-color: rgba(255, 255, 255, 0.6); 
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.8);
            }
        """)

        self.vLayout = QVBoxLayout(self)
        self.vLayout.setContentsMargins(10, 20, 10, 20)
        self.vLayout.setSpacing(15)

        self.nameLabel = BodyLabel(channel_name, self)
        self.nameLabel.setAlignment(Qt.AlignCenter)
        self.nameLabel.setStyleSheet("color: #555; font-weight: bold;")
        
        self.ring = ProgressRing(self)
        self.ring.setFixedSize(80, 80)
        self.ring.setStrokeWidth(6)
        self.ring.setTextVisible(True)
        self.ring.setValue(0)
        
        self.slider = Slider(Qt.Vertical, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setFixedWidth(30)
        
        self.slider.valueChanged.connect(self.on_value_changed)

        self.vLayout.addWidget(self.nameLabel, 0, Qt.AlignHCenter)
        self.vLayout.addWidget(self.ring, 0, Qt.AlignHCenter)
        self.vLayout.addWidget(self.slider, 1, Qt.AlignHCenter)

    def on_value_changed(self, value):
        self.ring.setValue(value)
        self.valueChanged.emit(value)

    def reset(self):
        self.slider.setValue(0)


class DeviceInterface(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('device-interface')
        
        import os
        bg_path = os.path.join("resource", "tech_bg.png").replace("\\", "/")
        
        self.setStyleSheet(f"""
            #device-interface {{
                background-image: url("{bg_path}");
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
        """)

        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(40, 40, 40, 40)
        
        self.initHeader()
        self.mainLayout.addStretch(1)
        self.initChannelContainer()
        self.mainLayout.addSpacing(30)
        self.initFooter()

    def initHeader(self):
        headerLayout = QHBoxLayout()
        
        title = SubtitleLabel('DEVICE MONITORING', self)
        title.setStyleSheet("font-family: 'Segoe UI Black'; font-size: 24px; color: #0078D4;")
        
        subtitle = BodyLabel(' | 实时参数控制中心', self)
        subtitle.setStyleSheet("font-size: 16px; color: #666; margin-top: 8px;")

        headerLayout.addWidget(title)
        headerLayout.addWidget(subtitle)
        headerLayout.addStretch(1)
        
        self.mainLayout.addLayout(headerLayout)

    def initChannelContainer(self):
        self.channelLayout = QHBoxLayout()
        self.channelLayout.setSpacing(30)
        self.channelLayout.setAlignment(Qt.AlignCenter)

        self.channels = []
        for i in range(4):
            card = ChannelCard(f"CHANNEL 0{i+1}", self)
            self.channelLayout.addWidget(card)
            self.channels.append(card)

        self.mainLayout.addLayout(self.channelLayout)

    def initFooter(self):
        footerLayout = QHBoxLayout()
        
        footerLayout.addStretch(1)
        
        self.resetBtn = PrimaryPushButton('SYSTEM RESET', self)
        self.resetBtn.setFixedWidth(180)
        self.resetBtn.setFixedHeight(45)
        self.resetBtn.setIcon(FIF.SYNC)
        self.resetBtn.clicked.connect(self.reset_all)
        
        self.resetBtn.setStyleSheet("""
            PrimaryPushButton {
                border-radius: 22px;
                font-weight: bold;
                font-size: 14px;
                background-color: #0078D4;
                border: 1px solid #0078D4;
            }
            PrimaryPushButton:hover {
                background-color: #1988e3;
            }
        """)
        
        footerLayout.addWidget(self.resetBtn)
        self.mainLayout.addLayout(footerLayout)

    def reset_all(self):
        for channel in self.channels:
            channel.reset()


class LogPage(CardWidget):
    """ 日志页面 - 显示收发消息和当前连接状态 """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_manager = parent.device_manager if parent else None
        
        self.vLayout = QVBoxLayout(self)
        self.vLayout.setContentsMargins(20, 20, 20, 20)
        self.vLayout.setSpacing(15)
        
        self.setup_ui()
        
        if self.device_manager:
            self.device_manager.esp8266.msgReceived.connect(self.append_message)
            self.device_manager.bluetooth.msgReceived.connect(self.append_message)
            self.update_connection_status()
    
    def setup_ui(self):
        self.statusLabel = SubtitleLabel('当前连接状态', self)
        self.vLayout.addWidget(self.statusLabel)
        
        self.statusCard = CardWidget(self)
        self.statusLayout = QHBoxLayout(self.statusCard)
        
        self.connectionStatusLabel = BodyLabel('未连接', self)
        self.connectionStatusLabel.setStyleSheet("""
            QLabel {
                font-size: 16px;
                padding: 10px;
                border-radius: 8px;
                background-color: #f0f0f0;
            }
        """)
        
        self.statusLayout.addWidget(self.connectionStatusLabel)
        self.statusLayout.addStretch(1)
        
        self.disconnectBtn = PushButton(FIF.CLOSE, '断开连接', self)
        self.disconnectBtn.clicked.connect(self.disconnect_device)
        self.disconnectBtn.setEnabled(False)
        self.statusLayout.addWidget(self.disconnectBtn)
        
        self.vLayout.addWidget(self.statusCard)
        
        self.msgLabel = SubtitleLabel('通信日志', self)
        self.vLayout.addWidget(self.msgLabel)
        
        self.msgDisplay = QTextEdit(self)
        self.msgDisplay.setReadOnly(True)
        self.msgDisplay.setPlaceholderText("设备通信消息将在此显示...")
        self.vLayout.addWidget(self.msgDisplay)
        
        self.buttonLayout = QHBoxLayout()
        
        self.clearBtn = PushButton(FIF.DELETE, '清空日志', self)
        self.clearBtn.clicked.connect(self.msgDisplay.clear)
        self.buttonLayout.addWidget(self.clearBtn)
        
        self.buttonLayout.addStretch(1)
        
        self.vLayout.addLayout(self.buttonLayout)
    
    def append_message(self, message):
        self.msgDisplay.moveCursor(QTextEdit.End)
        self.msgDisplay.insertPlainText(message)
        self.msgDisplay.moveCursor(QTextEdit.End)
    
    def update_connection_status(self):
        if not self.device_manager:
            return
        
        info = self.device_manager.get_current_device_info()
        if info['connected']:
            self.connectionStatusLabel.setText(info['name'])
            self.connectionStatusLabel.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #4CAF50;
                    color: white;
                }
            """)
            self.disconnectBtn.setEnabled(True)
        else:
            self.connectionStatusLabel.setText('未连接')
            self.connectionStatusLabel.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    padding: 10px;
                    border-radius: 8px;
                    background-color: #f0f0f0;
                }
            """)
            self.disconnectBtn.setEnabled(False)
    
    def disconnect_device(self):
        if self.device_manager:
            self.device_manager.disconnect_all()
            self.update_connection_status()


class ESP8266Page(CardWidget):
    """ ESP8266连接页面 - 简化的连接操作 """
    
    connection_succeeded = Signal(str)
    connection_failed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_manager = parent.device_manager if parent else None
        self.esp8266 = ESP8266Communicator()
        
        self.vLayout = QVBoxLayout(self)
        self.vLayout.setContentsMargins(20, 20, 20, 20)
        self.vLayout.setSpacing(15)
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        self.titleLabel = SubtitleLabel('ESP8266 WiFi模块连接', self)
        self.vLayout.addWidget(self.titleLabel)
        
        self.tipLabel = BodyLabel('确保ESP8266与电脑在同一局域网内', self)
        self.tipLabel.setStyleSheet("color: #666;")
        self.vLayout.addWidget(self.tipLabel)
        
        self.card = CardWidget(self)
        self.cardLayout = QVBoxLayout(self.card)
        self.cardLayout.setSpacing(10)
        
        self.ipLabel = QLabel('ESP8266 IP地址:', self)
        self.cardLayout.addWidget(self.ipLabel)
        
        self.ipEdit = QLineEdit(self)
        self.ipEdit.setPlaceholderText("例如: 192.168.1.100")
        self.ipEdit.setText("192.168.1.100")
        self.cardLayout.addWidget(self.ipEdit)
        
        self.portLabel = QLabel('端口号:', self)
        self.cardLayout.addWidget(self.portLabel)
        
        self.portEdit = QLineEdit(self)
        self.portEdit.setPlaceholderText("例如: 8080")
        self.portEdit.setText("8080")
        self.cardLayout.addWidget(self.portEdit)
        
        self.quickConnectLabel = SubtitleLabel('快速连接', self)
        self.quickConnectLabel.setStyleSheet("color: #0078D4;")
        self.cardLayout.addWidget(self.quickConnectLabel)
        
        self.quickTipLabel = BodyLabel('如果不知道IP，可以在ESP8266的串口调试助手中查看', self)
        self.quickTipLabel.setStyleSheet("color: #888; font-size: 12px;")
        self.cardLayout.addWidget(self.quickTipLabel)
        
        self.buttonLayout = QHBoxLayout()
        
        self.connectBtn = PrimaryPushButton(FIF.WIFI, '连接', self)
        self.connectBtn.setFixedWidth(120)
        self.connectBtn.setFixedHeight(40)
        self.connectBtn.clicked.connect(self.connect_to_esp8266)
        
        self.disconnectBtn = PushButton(FIF.CLOSE, '断开', self)
        self.disconnectBtn.setFixedWidth(100)
        self.disconnectBtn.setFixedHeight(40)
        self.disconnectBtn.clicked.connect(self.disconnect)
        self.disconnectBtn.setEnabled(False)
        
        self.buttonLayout.addWidget(self.connectBtn)
        self.buttonLayout.addWidget(self.disconnectBtn)
        self.buttonLayout.addStretch(1)
        
        self.cardLayout.addLayout(self.buttonLayout)
        
        self.statusLabel = BodyLabel('未连接', self)
        self.statusLabel.setStyleSheet("""
            QLabel {
                padding: 10px;
                border-radius: 5px;
                background-color: #f5f5f5;
            }
        """)
        self.cardLayout.addWidget(self.statusLabel)
        
        self.vLayout.addWidget(self.card)
        self.vLayout.addStretch(1)
    
    def connect_signals(self):
        self.esp8266.msgReceived.connect(self.on_message_received)
        self.esp8266.connStatusChanged.connect(self.on_status_changed)
    
    def connect_to_esp8266(self):
        ip_address = self.ipEdit.text().strip()
        port = self.portEdit.text().strip()
        
        if not ip_address:
            InfoBar.warning(
                title="提示",
                content="请输入ESP8266的IP地址",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                parent=self
            )
            return
        
        try:
            port = int(port) if port else 8080
        except ValueError:
            InfoBar.warning(
                title="提示",
                content="端口号必须是数字",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                parent=self
            )
            return
        
        self.connectBtn.setEnabled(False)
        self.statusLabel.setText("正在连接...")
        self.statusLabel.setStyleSheet("""
            QLabel {
                padding: 10px;
                border-radius: 5px;
                background-color: #FFF3E0;
                color: #E65100;
            }
        """)
        
        self.esp8266.establish_connection(ip_address, port)
    
    def disconnect(self):
        self.esp8266.close_connection()
    
    def on_status_changed(self, connected, info):
        if connected:
            self.connectBtn.setEnabled(False)
            self.disconnectBtn.setEnabled(True)
            self.ipEdit.setEnabled(False)
            self.portEdit.setEnabled(False)
            self.statusLabel.setText(f"已连接: {info}")
            self.statusLabel.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #E8F5E9;
                    color: #2E7D32;
                }
            """)
            self.connection_succeeded.emit(info)
        else:
            self.connectBtn.setEnabled(True)
            self.disconnectBtn.setEnabled(False)
            self.ipEdit.setEnabled(True)
            self.portEdit.setEnabled(True)
            self.statusLabel.setText("未连接")
            self.statusLabel.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #f5f5f5;
                }
            """)
            if info:
                self.connection_failed.emit(info)
    
    def on_message_received(self, message):
        pass


class BluetoothPage(CardWidget):
    """ 蓝牙连接页面 - 扫描和连接蓝牙设备 """
    
    connection_succeeded = Signal(str)
    connection_failed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_manager = parent.device_manager if parent else None
        self.bluetooth = BluetoothCommunicator()
        
        self.vLayout = QVBoxLayout(self)
        self.vLayout.setContentsMargins(20, 20, 20, 20)
        self.vLayout.setSpacing(15)
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        self.titleLabel = SubtitleLabel('蓝牙设备连接', self)
        self.vLayout.addWidget(self.titleLabel)
        
        self.tipLabel = BodyLabel('确保蓝牙模块已开启并处于可发现状态', self)
        self.tipLabel.setStyleSheet("color: #666;")
        self.vLayout.addWidget(self.tipLabel)
        
        self.scanCard = CardWidget(self)
        self.scanLayout = QVBoxLayout(self.scanCard)
        self.scanLayout.setSpacing(10)
        
        self.scanBtn = PrimaryPushButton(FIF.SEARCH, '扫描附近设备', self)
        self.scanBtn.setFixedHeight(40)
        self.scanBtn.clicked.connect(self.scan_bluetooth)
        self.scanLayout.addWidget(self.scanBtn)
        
        self.deviceListLabel = BodyLabel('找到的设备:', self)
        self.scanLayout.addWidget(self.deviceListLabel)
        
        self.deviceList = QListWidget(self)
        self.deviceList.setMaximumHeight(200)
        self.deviceList.itemClicked.connect(self.on_device_selected)
        self.scanLayout.addWidget(self.deviceList)
        
        self.selectedLabel = BodyLabel('未选择设备', self)
        self.selectedLabel.setStyleSheet("""
            QLabel {
                padding: 8px;
                border-radius: 5px;
                background-color: #f5f5f5;
            }
        """)
        self.scanLayout.addWidget(self.selectedLabel)
        
        self.buttonLayout = QHBoxLayout()
        
        self.connectBtn = PrimaryPushButton(FIF.BLUETOOTH, '连接', self)
        self.connectBtn.setFixedWidth(120)
        self.connectBtn.setFixedHeight(40)
        self.connectBtn.clicked.connect(self.connect_to_bluetooth)
        self.connectBtn.setEnabled(False)
        
        self.disconnectBtn = PushButton(FIF.CLOSE, '断开', self)
        self.disconnectBtn.setFixedWidth(100)
        self.disconnectBtn.setFixedHeight(40)
        self.disconnectBtn.clicked.connect(self.disconnect)
        self.disconnectBtn.setEnabled(False)
        
        self.buttonLayout.addWidget(self.connectBtn)
        self.buttonLayout.addWidget(self.disconnectBtn)
        self.buttonLayout.addStretch(1)
        
        self.scanLayout.addLayout(self.buttonLayout)
        
        self.statusLabel = BodyLabel('未连接', self)
        self.statusLabel.setStyleSheet("""
            QLabel {
                padding: 10px;
                border-radius: 5px;
                background-color: #f5f5f5;
            }
        """)
        self.scanLayout.addWidget(self.statusLabel)
        
        self.vLayout.addWidget(self.scanCard)
        self.vLayout.addStretch(1)
    
    def connect_signals(self):
        self.bluetooth.msgReceived.connect(self.on_message_received)
        self.bluetooth.connStatusChanged.connect(self.on_status_changed)
        self.bluetooth.devicesFound.connect(self.on_devices_found)
    
    def scan_bluetooth(self):
        self.deviceList.clear()
        self.deviceList.addItem("正在扫描...")
        self.scanBtn.setEnabled(False)
        self.bluetooth.scan_devices()
    
    def on_devices_found(self, devices):
        self.deviceList.clear()
        self.scanBtn.setEnabled(True)
        
        if not devices:
            self.deviceList.addItem("未找到蓝牙设备")
            return
        
        for device in devices:
            item = QListWidgetItem(f"{device['name']} ({device['address']})")
            item.setData(Qt.UserRole, device)
            self.deviceList.addItem(item)
    
    def on_device_selected(self, item):
        device_data = item.data(Qt.UserRole)
        if device_data:
            self.selectedDevice = device_data
            self.selectedLabel.setText(f"已选择: {device_data['name']}")
            self.selectedLabel.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    border-radius: 5px;
                    background-color: #E3F2FD;
                    color: #1976D2;
                }
            """)
            self.connectBtn.setEnabled(True)
    
    def connect_to_bluetooth(self):
        if not hasattr(self, 'selectedDevice'):
            InfoBar.warning(
                title="提示",
                content="请先选择要连接的蓝牙设备",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                parent=self
            )
            return
        
        device_address = self.selectedDevice['address']
        device_name = self.selectedDevice['name']
        
        self.connectBtn.setEnabled(False)
        self.statusLabel.setText("正在连接...")
        self.statusLabel.setStyleSheet("""
            QLabel {
                padding: 10px;
                border-radius: 5px;
                background-color: #FFF3E0;
                color: #E65100;
            }
        """)
        
        self.bluetooth.establish_connection(device_address, device_name)
    
    def disconnect(self):
        self.bluetooth.close_connection()
    
    def on_status_changed(self, connected, info):
        if connected:
            self.connectBtn.setEnabled(False)
            self.disconnectBtn.setEnabled(True)
            self.deviceList.setEnabled(False)
            self.scanBtn.setEnabled(False)
            self.statusLabel.setText(f"已连接: {info}")
            self.statusLabel.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #E8F5E9;
                    color: #2E7D32;
                }
            """)
            self.connection_succeeded.emit(info)
        else:
            self.connectBtn.setEnabled(True)
            self.disconnectBtn.setEnabled(False)
            self.deviceList.setEnabled(True)
            self.scanBtn.setEnabled(True)
            self.statusLabel.setText("未连接")
            self.statusLabel.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #f5f5f5;
                }
            """)
            if info:
                self.connection_failed.emit(info)
    
    def on_message_received(self, message):
        pass


class DeviceConnectionInterface(QFrame):
    """ 设备连接容器页面 - 包含3个子页面 """
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('device-connection')
        self.setStyleSheet(f"#{self.objectName()} {{ background-color: white; }}")
        
        self.device_manager = DeviceManager()
        
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(20, 20, 20, 20)
        self.mainLayout.setSpacing(15)
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        # 添加标题
        self.titleLabel = SubtitleLabel('设备连接', self)
        self.mainLayout.addWidget(self.titleLabel)
        
        # 添加页面容器
        self.stackedWidget = QStackedWidget(self)
        
        self.logPage = LogPage(self)
        self.esp8266Page = ESP8266Page(self)
        self.bluetoothPage = BluetoothPage(self)
        
        self.stackedWidget.addWidget(self.logPage)
        self.stackedWidget.addWidget(self.esp8266Page)
        self.stackedWidget.addWidget(self.bluetoothPage)
        
        self.mainLayout.addWidget(self.stackedWidget)
    
    def setup_connections(self):
        # 连接其他信号
        self.esp8266Page.connection_succeeded.connect(self.on_esp8266_connected)
        self.esp8266Page.connection_failed.connect(self.on_connection_failed)
        self.bluetoothPage.connection_succeeded.connect(self.on_bluetooth_connected)
        self.bluetoothPage.connection_failed.connect(self.on_connection_failed)
        
        self.device_manager.esp8266.msgReceived.connect(self.logPage.append_message)
        self.device_manager.bluetooth.msgReceived.connect(self.logPage.append_message)
        self.device_manager.esp8266.connStatusChanged.connect(self.on_device_status_changed)
        self.device_manager.bluetooth.connStatusChanged.connect(self.on_device_status_changed)
    
    def on_esp8266_connected(self, info):
        self.device_manager.esp8266.ip_address = self.esp8266Page.ipEdit.text().strip()
        self.device_manager.esp8266.port = int(self.esp8266Page.portEdit.text().strip())
        InfoBar.success(
            title="连接成功",
            content=f"已连接到 {info}",
            orient=Qt.Horizontal,
            isClosable=True,
            duration=3000,
            parent=self
        )
        self.logPage.update_connection_status()
    
    def on_bluetooth_connected(self, info):
        InfoBar.success(
            title="连接成功",
            content=f"已连接到 {info}",
            orient=Qt.Horizontal,
            isClosable=True,
            duration=3000,
            parent=self
        )
        self.logPage.update_connection_status()
    
    def on_connection_failed(self, error):
        InfoBar.error(
            title="连接失败",
            content=error,
            orient=Qt.Horizontal,
            isClosable=True,
            duration=3000,
            parent=self
        )
    
    def on_device_status_changed(self, connected, info):
        self.logPage.update_connection_status()
    
    def switch_to_mode(self, mode_index):
        """从侧边栏切换到指定模式"""
        self.stackedWidget.setCurrentIndex(mode_index)


class AvatarWidget(NavigationWidget):

    def __init__(self, parent=None):
        super().__init__(isSelectable=False, parent=parent)
        self.avatar = QImage('resource/shoko.png').scaled(
            24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.SmoothPixmapTransform | QPainter.Antialiasing)

        painter.setPen(Qt.NoPen)

        if self.isPressed:
            painter.setOpacity(0.7)

        if self.isEnter:
            c = 255 if isDarkTheme() else 0
            painter.setBrush(QColor(c, c, c, 10))
            painter.drawRoundedRect(self.rect(), 5, 5)

        painter.setBrush(QBrush(self.avatar))
        painter.translate(8, 6)
        painter.drawEllipse(0, 0, 24, 24)
        painter.translate(-8, -6)

        if not self.isCompacted:
            painter.setPen(Qt.white if isDarkTheme() else Qt.black)
            font = QFont('Segoe UI')
            font.setPixelSize(14)
            painter.setFont(font)
            painter.drawText(QRect(44, 0, 255, 36), Qt.AlignVCenter, 'zhiyiYo')





class Window(FramelessWindow):

    def __init__(self):
        super().__init__()
        self.setTitleBar(StandardTitleBar(self))

        self.hBoxLayout = QHBoxLayout(self)
        self.navigationInterface = NavigationInterface(
            self, showMenuButton=True, showReturnButton=False)
        self.stackWidget = QStackedWidget(self)

        self.searchInterface = Widget('Search Interface', self)
        self.deviceInterface = DeviceInterface(self)
        self.videoInterface = Widget('Video Interface', self)
        self.folderInterface = Widget('Folder Interface', self)
        self.settingInterface = Widget('Setting Interface', self)
        self.deviceConnectionInterface = DeviceConnectionInterface(self)
        
        self.initLayout()
        self.initNavigation()
        self.initWindow()

    def initLayout(self):
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, self.titleBar.height(), 0, 0)  # 为标题栏留出空间
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addWidget(self.stackWidget)
        self.hBoxLayout.setStretchFactor(self.stackWidget, 1)

        self.titleBar.raise_()
        self.navigationInterface.displayModeChanged.connect(self.titleBar.raise_)

    def initNavigation(self):
        # 启用亚克力效果
        # self.navigationInterface.setAcrylicEnabled(True)

        self.addSubInterface(self.searchInterface, FIF.SEARCH, '主页')
        self.addSubInterface(self.deviceInterface, FIF.TILES, '查看设备')
        self.addSubInterface(self.videoInterface, FIF.VIDEO, 'Video library')

        self.navigationInterface.addSeparator()

        # 添加设备连接主菜单项
        self.addSubInterface(self.deviceConnectionInterface, FIF.CONNECT, '设备连接', NavigationItemPosition.SCROLL)
        
        # 直接使用 navigationInterface.addItem 添加子菜单项，并设置正确的回调
        self.navigationInterface.addItem(
            routeKey='device-connection-log',
            icon=FIF.INFO,
            text='日志',
            onClick=lambda: [self.switchTo(self.deviceConnectionInterface), self.deviceConnectionInterface.switch_to_mode(0)],
            position=NavigationItemPosition.SCROLL,
            parentRouteKey=self.deviceConnectionInterface.objectName()
        )
        
        self.navigationInterface.addItem(
            routeKey='device-connection-esp8266',
            icon=FIF.WIFI,
            text='ESP8266',
            onClick=lambda: [self.switchTo(self.deviceConnectionInterface), self.deviceConnectionInterface.switch_to_mode(1)],
            position=NavigationItemPosition.SCROLL,
            parentRouteKey=self.deviceConnectionInterface.objectName()
        )
        
        self.navigationInterface.addItem(
            routeKey='device-connection-bluetooth',
            icon=FIF.BLUETOOTH,
            text='蓝牙',
            onClick=lambda: [self.switchTo(self.deviceConnectionInterface), self.deviceConnectionInterface.switch_to_mode(2)],
            position=NavigationItemPosition.SCROLL,
            parentRouteKey=self.deviceConnectionInterface.objectName()
        )

        # 启用展开状态记忆
        self.navigationInterface.widget('device-connection').setRememberExpandState(True)

        self.addSubInterface(self.folderInterface, FIF.FOLDER, 'Folder library', NavigationItemPosition.SCROLL)

        self.navigationInterface.addWidget(
            routeKey='avatar',
            widget=AvatarWidget(),
            onClick=self.showMessageBox,
            position=NavigationItemPosition.BOTTOM
        )

        self.addSubInterface(self.settingInterface, FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)

        qrouter.setDefaultRouteKey(self.stackWidget, self.searchInterface.objectName())

        self.stackWidget.currentChanged.connect(self.onCurrentInterfaceChanged)
        self.stackWidget.setCurrentIndex(0)

    def initWindow(self):
        self.resize(900, 700)
        self.setWindowIcon(QIcon('resource/logo.png'))
        # 确保窗口标题设置正确
        window_title = 'PyQt-Fluent-Widgets'
        print(f"设置窗口标题: {window_title}")
        self.setWindowTitle(window_title)
        # 确保标题栏属性
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

        self.setQss()

    def addSubInterface(self, interface, icon, text: str, position=NavigationItemPosition.TOP, parent=None):
        """ add sub interface """
        self.stackWidget.addWidget(interface)
        self.navigationInterface.addItem(
            routeKey=interface.objectName(),
            icon=icon,
            text=text,
            onClick=lambda: self.switchTo(interface),
            position=position,
            tooltip=text,
            parentRouteKey=parent.objectName() if parent else None
        )

    def setQss(self):
        # 暂时注释掉QSS设置，避免文件不存在的错误
        # color = 'dark' if isDarkTheme() else 'light'
        # try:
        #     with open(f'resource/{color}/demo.qss', encoding='utf-8') as f:
        #         self.setStyleSheet(f.read())
        # except FileNotFoundError:
        #     print(f"QSS文件不存在: resource/{color}/demo.qss")
        #     # 使用默认样式
        pass

    def switchTo(self, widget):
        self.stackWidget.setCurrentWidget(widget)

    def onCurrentInterfaceChanged(self, index):
        widget = self.stackWidget.widget(index)
        self.navigationInterface.setCurrentItem(widget.objectName())
        qrouter.push(self.stackWidget, widget.objectName())

    def showMessageBox(self):
        w = MessageBox(
            '支持作者🥰',
            '个人开发不易，如果这个项目帮助到了您，可以考虑请作者喝一瓶快乐水🥤。您的支持就是作者开发和维护项目的动力🚀',
            self
        )
        w.yesButton.setText('来啦老弟')
        w.cancelButton.setText('下次一定')

        if w.exec():
            QDesktopServices.openUrl(QUrl("https://afdian.net/a/zhiyiYo"))

    


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec()
