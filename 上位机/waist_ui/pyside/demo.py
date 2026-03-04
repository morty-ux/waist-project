# coding:utf-8
import sys
import socket
import threading
import time
from datetime import datetime

# 1. PySide6 核心模块
from PySide6.QtCore import Qt, QRect, QUrl, QDate, QTime, Signal, QTimer
from PySide6.QtGui import (
    QIcon, QPainter, QImage, QBrush, QColor, QFont, 
    QDesktopServices, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QStackedWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QFileDialog, QWidget, QComboBox, QSplitter, QTextEdit, QLineEdit
)

# 2. QFluentWidgets 组件库
from qfluentwidgets import (
    # 导航相关
    NavigationInterface, NavigationItemPosition, NavigationWidget, qrouter,
    # 基础控件
    SubtitleLabel, BodyLabel, TextEdit, CalendarPicker, 
    Slider, ProgressRing, CardWidget, TabBar,
    # 按钮与图标
    PrimaryPushButton, PushButton, ToolButton, FluentIcon as FIF,
    # 弹窗与主题
    MessageBox, isDarkTheme, setTheme, Theme, themeColor, InfoBar
)

# 3. QFramelessWindow 无边框窗口库
from qframelesswindow import FramelessWindow, TitleBar

class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)

        # leave some space for title bar
        self.hBoxLayout.setContentsMargins(0, 16, 0, 0)
        
class ChannelCard(QFrame):
    """ 单个通道的控制卡片（包含环形进度条和垂直滑杆） """
    
    valueChanged = Signal(int) # 信号：数值改变时发出

    def __init__(self, channel_name, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 320) # 卡片固定大小，修长型
        
        # 卡片样式：半透明磨砂白，圆角，阴影
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

        # 1. 顶部：通道名称
        self.nameLabel = BodyLabel(channel_name, self)
        self.nameLabel.setAlignment(Qt.AlignCenter)
        self.nameLabel.setStyleSheet("color: #555; font-weight: bold;")
        
        # 2. 上部：环形进度条 (可视化数值)
        self.ring = ProgressRing(self)
        self.ring.setFixedSize(80, 80)
        self.ring.setStrokeWidth(6)
        self.ring.setTextVisible(True) # 显示中心百分比
        self.ring.setValue(0)
        
        # 3. 中下部：垂直滑杆
        self.slider = Slider(Qt.Vertical, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        # 滑杆样式微调，使其更具科技感
        self.slider.setFixedWidth(30) 
        
        # 联动逻辑
        self.slider.valueChanged.connect(self.on_value_changed)

        # 添加到布局
        self.vLayout.addWidget(self.nameLabel, 0, Qt.AlignHCenter)
        self.vLayout.addWidget(self.ring, 0, Qt.AlignHCenter)
        self.vLayout.addWidget(self.slider, 1, Qt.AlignHCenter) # 1 表示占用剩余空间

    def on_value_changed(self, value):
        self.ring.setValue(value)
        self.valueChanged.emit(value)

    def reset(self):
        """ 复位带动画 """
        self.slider.setValue(0)

class DeviceInterface(QFrame):
    """ 设备查看与控制界面 - 科技感重构版 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('device-interface')
        
        # 加载背景图片
        # 请确保你已经运行了上面的脚本生成了 resource/tech_bg.png
        import os
        bg_path = os.path.join("resource", "tech_bg.png").replace("\\", "/")
        
        # 设置背景图样式，居中覆盖
        self.setStyleSheet(f"""
            #device-interface {{
                background-image: url("{bg_path}");
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
        """)

        # 主布局
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(40, 40, 40, 40)
        
        # 1. 顶部标题区域
        self.initHeader()
        
        self.mainLayout.addStretch(1) # 弹性空间，把内容挤到下面

        # 2. 中间：4个并排的通道卡片
        self.initChannelContainer()
        
        self.mainLayout.addSpacing(30)

        # 3. 底部：复位按钮 (右下角)
        self.initFooter()

    def initHeader(self):
        """ 初始化头部标题 """
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
        """ 初始化通道卡片容器 """
        self.channelLayout = QHBoxLayout()
        self.channelLayout.setSpacing(30) # 卡片之间的间距
        self.channelLayout.setAlignment(Qt.AlignCenter) # 整体居中

        self.channels = []
        for i in range(4):
            card = ChannelCard(f"CHANNEL 0{i+1}", self)
            self.channelLayout.addWidget(card)
            self.channels.append(card)

        self.mainLayout.addLayout(self.channelLayout)

    def initFooter(self):
        """ 初始化底部按钮区域 """
        footerLayout = QHBoxLayout()
        
        # 左侧占位
        footerLayout.addStretch(1)
        
        # 右侧按钮
        self.resetBtn = PrimaryPushButton('SYSTEM RESET', self)
        self.resetBtn.setFixedWidth(180)
        self.resetBtn.setFixedHeight(45)
        self.resetBtn.setIcon(FIF.SYNC)
        self.resetBtn.clicked.connect(self.reset_all)
        
        # 按钮样式微调：加一点阴影和圆角
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
        
        # 将底部布局加入主布局
        self.mainLayout.addLayout(footerLayout)

    def reset_all(self):
        """ 一键复位所有通道 """
        for channel in self.channels:
            channel.reset()

class WiFiSettingsInterface(QFrame):
    """ WiFi设置界面 """
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('wifi_settings_interface')
        self.setStyleSheet(f"#{self.objectName()} {{ background-color: white; }}")
        
        # 布局初始化
        self.vBoxLayout = QVBoxLayout(self)
        # 减少顶部边距，因为导航栏已经提供了顶部空间
        self.vBoxLayout.setContentsMargins(36, 16, 36, 36)
        self.vBoxLayout.setSpacing(20)

        # 标题
        self.titleLabel = SubtitleLabel('WiFi设置', self)
        self.vBoxLayout.addWidget(self.titleLabel)
        
        # WiFi连接设置卡片
        self.wifiCard = CardWidget(self)
        self.wifiLayout = QVBoxLayout(self.wifiCard)
        
        # WiFi网络列表
        self.networkListLabel = SubtitleLabel('可用网络:', self)
        self.wifiLayout.addWidget(self.networkListLabel)
        
        self.networkList = QTextEdit(self)
        self.networkList.setReadOnly(True)
        self.networkList.setMaximumHeight(150)
        self.networkList.setPlaceholderText('点击扫描按钮获取WiFi网络列表...')
        self.wifiLayout.addWidget(self.networkList)
        
        # 扫描按钮
        self.scanWifiBtn = PrimaryPushButton(FIF.SEARCH, '扫描WiFi网络', self)
        self.scanWifiBtn.clicked.connect(self.scan_wifi_networks)
        self.wifiLayout.addWidget(self.scanWifiBtn)
        
        # 连接设置区域
        self.connectionLayout = QHBoxLayout()
        
        # SSID输入
        self.ssidLabel = QLabel('网络名称(SSID):', self)
        self.ssidEdit = QLineEdit(self)
        self.ssidEdit.setPlaceholderText('输入WiFi网络名称')
        
        # 密码输入
        self.passwordLabel = QLabel('密码:', self)
        self.passwordEdit = QLineEdit(self)
        self.passwordEdit.setEchoMode(QLineEdit.Password)
        self.passwordEdit.setPlaceholderText('输入WiFi密码')
        
        self.connectionLayout.addWidget(self.ssidLabel)
        self.connectionLayout.addWidget(self.ssidEdit)
        self.connectionLayout.addWidget(self.passwordLabel)
        self.connectionLayout.addWidget(self.passwordEdit)
        
        self.wifiLayout.addLayout(self.connectionLayout)
        
        # 连接按钮
        self.connectWifiBtn = PrimaryPushButton(FIF.WIFI, '连接WiFi', self)
        self.connectWifiBtn.clicked.connect(self.connect_to_wifi)
        self.wifiLayout.addWidget(self.connectWifiBtn)
        
        self.vBoxLayout.addWidget(self.wifiCard)
        
        # 日志显示
        self.logLabel = SubtitleLabel('操作日志:', self)
        self.vBoxLayout.addWidget(self.logLabel)
        
        self.wifiLog = QTextEdit(self)
        self.wifiLog.setReadOnly(True)
        self.wifiLog.setMaximumHeight(100)
        self.wifiLog.setPlaceholderText('WiFi操作日志将在此显示...')
        self.vBoxLayout.addWidget(self.wifiLog)

    def scan_wifi_networks(self):
        # 模拟扫描WiFi网络
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.wifiLog.append(f"[{timestamp}] 正在扫描WiFi网络...")
        
        # 模拟一些WiFi网络
        networks = [
            "HomeNetwork (信号强度: 强)",
            "GuestWiFi (信号强度: 中)",
            "OfficeWiFi (信号强度: 弱)",
            "PublicHotspot (信号强度: 中)",
        ]
        
        self.networkList.clear()
        for network in networks:
            self.networkList.append(network)
        
        self.wifiLog.append(f"[{timestamp}] 扫描完成，找到{len(networks)}个网络")
    
    def connect_to_wifi(self):
        ssid = self.ssidEdit.text().strip()
        password = self.passwordEdit.text().strip()
        
        if not ssid:
            InfoBar.warning(
                title="输入错误",
                content="请输入WiFi网络名称",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                parent=self
            )
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.wifiLog.append(f"[{timestamp}] 正在连接到网络: {ssid}...")
        
        # 模拟连接过程
        time.sleep(1)  # 模拟连接时间
        
        InfoBar.success(
            title="连接成功",
            content=f"已连接到WiFi网络: {ssid}",
            orient=Qt.Horizontal,
            isClosable=True,
            duration=3000,
            parent=self
        )
        
        self.wifiLog.append(f"[{timestamp}] 已成功连接到网络: {ssid}")


class BluetoothInterface(QFrame):
    """ 蓝牙设置界面 """
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('bluetooth_interface')
        self.setStyleSheet(f"#{self.objectName()} {{ background-color: white; }}")
        
        # 布局初始化
        self.vBoxLayout = QVBoxLayout(self)
        # 减少顶部边距，因为导航栏已经提供了顶部空间
        self.vBoxLayout.setContentsMargins(36, 16, 36, 36)
        self.vBoxLayout.setSpacing(20)

        # 标题
        self.titleLabel = SubtitleLabel('蓝牙设置', self)
        self.vBoxLayout.addWidget(self.titleLabel)
        
        # 蓝牙状态显示
        self.bluetoothStatusLayout = QHBoxLayout()
        self.bluetoothStatusLabel = BodyLabel('蓝牙状态: 已开启', self)
        self.bluetoothStatusLayout.addWidget(self.bluetoothStatusLabel)
        
        self.bluetoothToggle = ToolButton(FIF.CLOSE, self)
        self.bluetoothToggle.clicked.connect(self.toggle_bluetooth)
        self.bluetoothToggle.setToolTip('关闭蓝牙')
        self.bluetoothStatusLayout.addWidget(self.bluetoothToggle)
        
        self.bluetoothStatusLayout.addStretch(1)
        self.vBoxLayout.addLayout(self.bluetoothStatusLayout)
        
        # 蓝牙设备列表
        self.deviceListLabel = SubtitleLabel('可用设备:', self)
        self.vBoxLayout.addWidget(self.deviceListLabel)
        
        self.deviceList = QTextEdit(self)
        self.deviceList.setReadOnly(True)
        self.deviceList.setMaximumHeight(150)
        self.deviceList.setPlaceholderText('点击扫描按钮搜索附近的蓝牙设备...')
        self.vBoxLayout.addWidget(self.deviceList)
        
        # 控制按钮
        self.controlLayout = QHBoxLayout()
        
        self.scanBluetoothBtn = PrimaryPushButton(FIF.SEARCH, '扫描蓝牙设备', self)
        self.scanBluetoothBtn.clicked.connect(self.scan_bluetooth_devices)
        
        self.pairDeviceBtn = PushButton(FIF.ADD, '配对设备', self)
        self.pairDeviceBtn.clicked.connect(self.pair_selected_device)
        
        self.controlLayout.addWidget(self.scanBluetoothBtn)
        self.controlLayout.addWidget(self.pairDeviceBtn)
        self.controlLayout.addStretch(1)
        
        self.vBoxLayout.addLayout(self.controlLayout)
        
        # 连接的设备
        self.connectedDevicesLabel = SubtitleLabel('已连接设备:', self)
        self.vBoxLayout.addWidget(self.connectedDevicesLabel)
        
        self.connectedDevicesList = QTextEdit(self)
        self.connectedDevicesList.setReadOnly(True)
        self.connectedDevicesList.setMaximumHeight(100)
        self.connectedDevicesList.setPlaceholderText('已连接的蓝牙设备将在此显示...')
        self.vBoxLayout.addWidget(self.connectedDevicesList)

    def toggle_bluetooth(self):
        # 切换蓝牙状态
        if self.bluetoothToggle.icon() == FIF.CLOSE:
            # 当前是开启状态，要关闭
            self.bluetoothToggle.setIcon(FIF.PLAY)
            self.bluetoothStatusLabel.setText('蓝牙状态: 已关闭')
            self.bluetoothToggle.setToolTip('开启蓝牙')
            
            # 清空设备列表
            self.deviceList.clear()
            self.connectedDevicesList.clear()
        else:
            # 当前是关闭状态，要开启
            self.bluetoothToggle.setIcon(FIF.CLOSE)
            self.bluetoothStatusLabel.setText('蓝牙状态: 已开启')
            self.bluetoothToggle.setToolTip('关闭蓝牙')
    
    def scan_bluetooth_devices(self):
        # 模拟扫描蓝牙设备
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 模拟一些蓝牙设备
        devices = [
            "MyPhone (手机, 信号强度: 强)",
            "WirelessHeadphones (耳机, 信号强度: 中)",
            "SmartWatch (手表, 信号强度: 弱)",
            "Speaker (音箱, 信号强度: 中)",
        ]
        
        self.deviceList.clear()
        for device in devices:
            self.deviceList.append(device)
        
        InfoBar.info(
            title="扫描完成",
            content=f"找到{len(devices)}个蓝牙设备",
            orient=Qt.Horizontal,
            isClosable=True,
            duration=3000,
            parent=self
        )
    
    def pair_selected_device(self):
        # 获取选中的设备（简单模拟）
        selected_text = self.deviceList.toPlainText().split('\n')[0] if self.deviceList.toPlainText() else "Unknown Device"
        if selected_text.strip():
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 添加到已连接设备列表
            self.connectedDevicesList.append(f"{selected_text} - 已连接")
            
            InfoBar.success(
                title="配对成功",
                content=f"已配对设备: {selected_text}",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                parent=self
            )


class LogInterface(QFrame):
    """ 工作日志界面 """
    
    # 定义信号用于更新UI
    message_received = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.setStyleSheet(f"#{self.objectName()} {{ background-color: white; }}")
        
        # 创建标签页
        self.tabBar = TabBar(self)
        self.tabBar.addTab('work_log', '工作日志', FIF.DOCUMENT)
        self.tabBar.addTab('wifi_settings', 'WiFi设置', FIF.WIFI)
        self.tabBar.addTab('bluetooth_settings', '蓝牙', FIF.BLUETOOTH)
        
        # 连接标签页切换事件
        self.tabBar.currentChanged.connect(self.onTabChanged)
        
        # 堆叠窗口管理不同界面
        self.stackedWidget = QStackedWidget(self)
        
        # 创建各个界面
        self.workLogInterface = self.createWorkLogInterface()
        self.wifiSettingsInterface = WiFiSettingsInterface()
        self.bluetoothInterface = BluetoothInterface()
        
        # 添加界面到堆叠窗口
        self.stackedWidget.addWidget(self.workLogInterface)  # 0: 工作日志
        self.stackedWidget.addWidget(self.wifiSettingsInterface)  # 1: WiFi设置
        self.stackedWidget.addWidget(self.bluetoothInterface)   # 2: 蓝牙设置
        
        # 主布局
        self.vBoxLayout = QVBoxLayout(self)
        # 设置顶部边距，避免与标题栏重合
        self.vBoxLayout.setContentsMargins(0, 48, 0, 0)  # 顶部32px边距
        self.vBoxLayout.addWidget(self.tabBar)
        self.vBoxLayout.addWidget(self.stackedWidget)
        
        # 默认显示工作日志界面
        self.stackedWidget.setCurrentIndex(0)
        
        # 连接信号
        self.message_received.connect(self.update_message_display)

    def createWorkLogInterface(self):
        # 创建工作日志界面内容
        workLogWidget = QWidget()
        layout = QVBoxLayout(workLogWidget)
        # 减少顶部边距，因为导航栏已经提供了顶部空间
        layout.setContentsMargins(36, 16, 36, 36)
        layout.setSpacing(20)

        # 标题
        titleLabel = SubtitleLabel('工作日志', workLogWidget)
        layout.addWidget(titleLabel)

        # ESP8266通信区域
        commCard = CardWidget(workLogWidget)
        commLayout = QVBoxLayout(commCard)
        
        # 通信控制区
        commControlLayout = QHBoxLayout()
        
        # IP地址输入
        ipLabel = QLabel("ESP8266 IP:", workLogWidget)
        self.ipEdit = QLineEdit(workLogWidget)
        self.ipEdit.setPlaceholderText("192.168.1.100")
        self.ipEdit.setText("192.168.1.100")
        
        # 端口输入
        portLabel = QLabel("端口:", workLogWidget)
        self.portEdit = QLineEdit(workLogWidget)
        self.portEdit.setPlaceholderText("8080")
        self.portEdit.setText("8080")
        
        # 连接按钮
        self.connectBtn = PrimaryPushButton(FIF.PLAY, "连接", workLogWidget)
        self.connectBtn.clicked.connect(self.toggle_connection)
        
        # 扫描网络按钮
        scanBtn = PushButton(FIF.SEARCH, "扫描", workLogWidget)
        scanBtn.clicked.connect(self.scan_network)
        
        commControlLayout.addWidget(ipLabel)
        commControlLayout.addWidget(self.ipEdit)
        commControlLayout.addWidget(portLabel)
        commControlLayout.addWidget(self.portEdit)
        commControlLayout.addWidget(self.connectBtn)
        commControlLayout.addWidget(scanBtn)
        commControlLayout.addStretch(1)
        
        commLayout.addLayout(commControlLayout)
        
        # 消息显示区域
        messageLabel = SubtitleLabel("ESP8266通信日志", workLogWidget)
        commLayout.addWidget(messageLabel)
        
        self.messageDisplay = QTextEdit(workLogWidget)
        self.messageDisplay.setReadOnly(True)
        self.messageDisplay.setPlaceholderText("ESP8266消息将在此显示...")
        commLayout.addWidget(self.messageDisplay)
        
        # 消息发送区域
        sendLayout = QHBoxLayout()
        self.sendEdit = TextEdit(workLogWidget)
        self.sendEdit.setPlaceholderText("输入要发送给ESP8266的消息...")
        self.sendEdit.setMaximumHeight(80)
        
        sendBtn = PrimaryPushButton(FIF.SEND, "发送", workLogWidget)
        sendBtn.clicked.connect(self.send_message)
        
        clearCommBtn = PushButton(FIF.DELETE, "清空日志", workLogWidget)
        clearCommBtn.clicked.connect(self.messageDisplay.clear)
        
        sendLayout.addWidget(self.sendEdit)
        sendLayout.addWidget(sendBtn)
        sendLayout.addWidget(clearCommBtn)
        
        commLayout.addLayout(sendLayout)
        layout.addWidget(commCard)

        # 操作栏（日期选择 + 插入时间戳）
        toolLayout = QHBoxLayout()
        
        # 日期选择器
        self.datePicker = CalendarPicker(workLogWidget)
        self.datePicker.setDate(QDate.currentDate())
        
        # 插入时间按钮
        timeBtn = PushButton(FIF.DATE_TIME, '插入当前时间', workLogWidget)
        timeBtn.clicked.connect(self.insert_timestamp)
        
        toolLayout.addWidget(self.datePicker)
        toolLayout.addWidget(timeBtn)
        toolLayout.addStretch(1)
        
        layout.addLayout(toolLayout)

        # 文本编辑区域
        self.textEdit = TextEdit(workLogWidget)
        self.textEdit.setPlaceholderText("在此记录今天的调试数据、实验结果或开发心得...")
        self.textEdit.setMarkdown("### 今日任务\n- [ ] 完成上位机界面\n- [ ] 调试ESP8266通信\n\n### 实验记录\n") 
        layout.addWidget(self.textEdit)

        # 底部按钮
        buttonLayout = QHBoxLayout()
        saveBtn = PrimaryPushButton(FIF.SAVE, '保存日志', workLogWidget)
        saveBtn.clicked.connect(self.save_log)
        
        clearBtn = PushButton(FIF.DELETE, '清空', workLogWidget)
        clearBtn.clicked.connect(self.textEdit.clear)

        buttonLayout.addStretch(1)
        buttonLayout.addWidget(clearBtn)
        buttonLayout.addWidget(saveBtn)
        
        layout.addLayout(buttonLayout)
        
        return workLogWidget

    def onTabChanged(self, index):
        # 切换堆叠窗口显示的页面
        self.stackedWidget.setCurrentIndex(index)

    def scan_network(self):
        """扫描网络中的ESP8266设备"""
        # 这里可以实现简单的网络扫描功能
        # 由于ESP8266可能使用不同的端口和协议，这里提供一个基础实现
        InfoBar.info(
            title="网络扫描",
            content="正在扫描网络中的ESP8266设备...",
            orient=Qt.Horizontal,
            isClosable=True,
            duration=3000,
            parent=self
        )
        
        # 添加扫描结果消息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.message_received.emit(f"[{timestamp}] [系统] 开始扫描网络中的ESP8266设备\n")
        
        # 这里可以添加实际的扫描逻辑
        # 例如扫描常见的ESP8266端口或使用mDNS发现
        self.message_received.emit(f"[{timestamp}] [系统] 扫描完成，请手动输入ESP8266的IP地址和端口\n")
    
    def toggle_connection(self):
        """切换ESP8266连接状态"""
        # ESP8266网络通信相关变量
        if not hasattr(self, 'socket'):
            self.socket = None
        if not hasattr(self, 'is_connected'):
            self.is_connected = False
        
        if not self.is_connected:
            # 尝试连接
            try:
                ip_address = self.ipEdit.text().strip()
                port = int(self.portEdit.text().strip())
                
                if not ip_address:
                    InfoBar.error(
                        title="连接失败",
                        content="请输入有效的IP地址",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        duration=3000,
                        parent=self
                    )
                    return
                
                # 创建TCP套接字
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5)  # 设置连接超时
                
                # 尝试连接
                self.socket.connect((ip_address, port))
                
                self.is_connected = True
                self.connectBtn.setText("断开")
                self.connectBtn.setIcon(FIF.PAUSE)
                self.ipEdit.setEnabled(False)
                self.portEdit.setEnabled(False)
                
                # 启动接收线程
                if not hasattr(self, 'receive_thread'):
                    self.receive_thread = None
                self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
                self.receive_thread.start()
                
                # 添加连接成功消息
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.message_received.emit(f"[{timestamp}] [系统] 已连接到 {ip_address}:{port}\n")
                
                InfoBar.success(
                    title="连接成功",
                    content=f"已连接到 {ip_address}:{port}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    duration=3000,
                    parent=self
                )
                
            except Exception as e:
                InfoBar.error(
                    title="连接失败",
                    content=f"无法连接到ESP8266: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    duration=3000,
                    parent=self
                )
                if self.socket:
                    self.socket.close()
                    self.socket = None
        else:
            # 断开连接
            self.disconnect_esp8266()
    
    def disconnect_esp8266(self):
        """断开ESP8266连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.is_connected = False
        self.connectBtn.setText("连接")
        self.connectBtn.setIcon(FIF.PLAY)
        self.ipEdit.setEnabled(True)
        self.portEdit.setEnabled(True)
        
        # 添加断开连接消息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.message_received.emit(f"[{timestamp}] [系统] 已断开连接\n")
    
    def receive_messages(self):
        """接收ESP8266消息的线程函数"""
        buffer = ""
        while self.is_connected and self.socket:
            try:
                # 接收数据
                data = self.socket.recv(1024).decode('utf-8', errors='ignore')
                if not data:
                    # 连接已关闭
                    break
                
                buffer += data
                
                # 检查是否有完整的消息行
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.message_received.emit(f"[{timestamp}] [ESP8266] {line.strip()}\n")
                
            except socket.timeout:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                if self.is_connected:  # 只有在仍然连接时才显示错误
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.message_received.emit(f"[{timestamp}] [错误] 接收消息失败: {str(e)}\n")
                break
        
        # 如果循环结束，说明连接已断开
        if self.is_connected:
            self.disconnect_esp8266()
    
    def send_message(self):
        """向ESP8266发送消息"""
        if not self.is_connected:
            InfoBar.warning(
                title="未连接",
                content="请先连接到ESP8266",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                parent=self
            )
            return
        
        message = self.sendEdit.toPlainText().strip()
        if not message:
            return
        
        try:
            # 确保消息以换行符结尾
            if not message.endswith('\n'):
                message += '\n'
            
            self.socket.send(message.encode('utf-8'))
            
            # 显示发送的消息
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.message_received.emit(f"[{timestamp}] [发送] {message.strip()}\n")
            
            # 清空输入框
            self.sendEdit.clear()
            
        except Exception as e:
            InfoBar.error(
                title="发送失败",
                content=f"无法发送消息: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                parent=self
            )
            # 发送失败可能意味着连接已断开
            self.disconnect_esp8266()
    
    def update_message_display(self, message):
        """更新消息显示区域（在主线程中执行）"""
        self.messageDisplay.moveCursor(QTextEdit.End)
        self.messageDisplay.insertPlainText(message)
        self.messageDisplay.moveCursor(QTextEdit.End)
    
    def insert_timestamp(self):
        """ 在光标处插入当前时间 """
        current_time = QTime.currentTime().toString("HH:mm:ss")
        self.textEdit.insertPlainText(f"[{current_time}] ")
        self.textEdit.setFocus()

    def save_log(self):
        """ 模拟保存功能 """
        # 这里你可以扩展为保存到txt或数据库
        print(f"日志已保存，日期: {self.datePicker.date.toString()}")
        print(f"内容: \n{self.textEdit.toPlainText()}")
        
        # 同时保存ESP8266通信日志
        if self.messageDisplay.toPlainText():
            print(f"ESP8266通信日志: \n{self.messageDisplay.toPlainText()}")

    def scan_network(self):
        """扫描网络中的ESP8266设备"""
        # 这里可以实现简单的网络扫描功能
        # 由于ESP8266可能使用不同的端口和协议，这里提供一个基础实现
        InfoBar.info(
            title="网络扫描",
            content="正在扫描网络中的ESP8266设备...",
            orient=Qt.Horizontal,
            isClosable=True,
            duration=3000,
            parent=self
        )
        
        # 添加扫描结果消息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.message_received.emit(f"[{timestamp}] [系统] 开始扫描网络中的ESP8266设备\n")
        
        # 这里可以添加实际的扫描逻辑
        # 例如扫描常见的ESP8266端口或使用mDNS发现
        self.message_received.emit(f"[{timestamp}] [系统] 扫描完成，请手动输入ESP8266的IP地址和端口\n")
    
    def toggle_connection(self):
        """切换ESP8266连接状态"""
        if not self.is_connected:
            # 尝试连接
            try:
                ip_address = self.ipEdit.text().strip()
                port = int(self.portEdit.text().strip())
                
                if not ip_address:
                    InfoBar.error(
                        title="连接失败",
                        content="请输入有效的IP地址",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        duration=3000,
                        parent=self
                    )
                    return
                
                # 创建TCP套接字
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5)  # 设置连接超时
                
                # 尝试连接
                self.socket.connect((ip_address, port))
                
                self.is_connected = True
                self.connectBtn.setText("断开")
                self.connectBtn.setIcon(FIF.PAUSE)
                self.ipEdit.setEnabled(False)
                self.portEdit.setEnabled(False)
                
                # 启动接收线程
                self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
                self.receive_thread.start()
                
                # 添加连接成功消息
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.message_received.emit(f"[{timestamp}] [系统] 已连接到 {ip_address}:{port}\n")
                
                InfoBar.success(
                    title="连接成功",
                    content=f"已连接到 {ip_address}:{port}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    duration=3000,
                    parent=self
                )
                
            except Exception as e:
                InfoBar.error(
                    title="连接失败",
                    content=f"无法连接到ESP8266: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    duration=3000,
                    parent=self
                )
                if self.socket:
                    self.socket.close()
                    self.socket = None
        else:
            # 断开连接
            self.disconnect_esp8266()
    
    def disconnect_esp8266(self):
        """断开ESP8266连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.is_connected = False
        self.connectBtn.setText("连接")
        self.connectBtn.setIcon(FIF.PLAY)
        self.ipEdit.setEnabled(True)
        self.portEdit.setEnabled(True)
        
        # 添加断开连接消息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.message_received.emit(f"[{timestamp}] [系统] 已断开连接\n")
    
    def receive_messages(self):
        """接收ESP8266消息的线程函数"""
        buffer = ""
        while self.is_connected and self.socket:
            try:
                # 接收数据
                data = self.socket.recv(1024).decode('utf-8', errors='ignore')
                if not data:
                    # 连接已关闭
                    break
                
                buffer += data
                
                # 检查是否有完整的消息行
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.message_received.emit(f"[{timestamp}] [ESP8266] {line.strip()}\n")
                
            except socket.timeout:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                if self.is_connected:  # 只有在仍然连接时才显示错误
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.message_received.emit(f"[{timestamp}] [错误] 接收消息失败: {str(e)}\n")
                break
        
        # 如果循环结束，说明连接已断开
        if self.is_connected:
            self.disconnect_esp8266()
    
    def send_message(self):
        """向ESP8266发送消息"""
        if not self.is_connected:
            InfoBar.warning(
                title="未连接",
                content="请先连接到ESP8266",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                parent=self
            )
            return
        
        message = self.sendEdit.toPlainText().strip()
        if not message:
            return
        
        try:
            # 确保消息以换行符结尾
            if not message.endswith('\n'):
                message += '\n'
            
            self.socket.send(message.encode('utf-8'))
            
            # 显示发送的消息
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.message_received.emit(f"[{timestamp}] [发送] {message.strip()}\n")
            
            # 清空输入框
            self.sendEdit.clear()
            
        except Exception as e:
            InfoBar.error(
                title="发送失败",
                content=f"无法发送消息: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                parent=self
            )
            # 发送失败可能意味着连接已断开
            self.disconnect_esp8266()
    
    def update_message_display(self, message):
        """更新消息显示区域（在主线程中执行）"""
        self.messageDisplay.moveCursor(QTextEdit.End)
        self.messageDisplay.insertPlainText(message)
        self.messageDisplay.moveCursor(QTextEdit.End)
    
    def insert_timestamp(self):
        """ 在光标处插入当前时间 """
        current_time = QTime.currentTime().toString("HH:mm:ss")
        self.textEdit.insertPlainText(f"[{current_time}] ")
        self.textEdit.setFocus()

    def save_log(self):
        """ 模拟保存功能 """
        # 这里你可以扩展为保存到txt或数据库
        print(f"日志已保存，日期: {self.datePicker.date.toString()}")
        print(f"内容: \n{self.textEdit.toPlainText()}")
        
        # 同时保存ESP8266通信日志
        if self.messageDisplay.toPlainText():
            print(f"ESP8266通信日志: \n{self.messageDisplay.toPlainText()}")

class AvatarWidget(NavigationWidget):
    """ Avatar widget """

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

        # draw background
        if self.isEnter:
            c = 255 if isDarkTheme() else 0
            painter.setBrush(QColor(c, c, c, 10))
            painter.drawRoundedRect(self.rect(), 5, 5)

        # draw avatar
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


class CustomTitleBar(TitleBar):
    """ Title bar with icon and title """

    def __init__(self, parent):
        super().__init__(parent)
        # add window icon
        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(18, 18)
        self.hBoxLayout.insertSpacing(0, 10)
        self.hBoxLayout.insertWidget(1, self.iconLabel, 0, Qt.AlignLeft | Qt.AlignCenter)
        self.window().windowIconChanged.connect(self.setIcon)

        # add title label
        self.titleLabel = QLabel(self)
        self.hBoxLayout.insertWidget(2, self.titleLabel, 0, Qt.AlignLeft | Qt.AlignCenter)
        self.titleLabel.setObjectName('titleLabel')
        self.window().windowTitleChanged.connect(self.setTitle)
    def paintEvent(self, event):
        # 1. 必须先调用父类的绘制方法，否则可能会丢失背景或交互
        super().paintEvent(event)
        
        # 2. 初始化画笔
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False) # 关掉抗锯齿，让线条更锐利
        
        # 3. 根据主题设置线条颜色
        if isDarkTheme():
            # 深色主题：深灰色线
            painter.setPen(QColor(55, 55, 55)) 
        else:
            # 浅色主题：浅灰色线 (类似 #E0E0E0)
            painter.setPen(QColor(224, 224, 224)) 

        # 4. 在最底部画一条横线
        # drawLine(起点x, 起点y, 终点x, 终点y)
        # y = self.height() - 1 表示最底下一行像素
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

    def setTitle(self, title):
        self.titleLabel.setText(title)
        self.titleLabel.adjustSize()

    def setIcon(self, icon):
        self.iconLabel.setPixmap(QIcon(icon).pixmap(18, 18))


class Window(FramelessWindow):

    def __init__(self):
        super().__init__()
        self.setTitleBar(CustomTitleBar(self))
        self.titleBar.setFixedHeight(48)
        # use dark theme mode
        # setTheme(Theme.DARK)

        self.hBoxLayout = QHBoxLayout(self)
        self.navigationInterface = NavigationInterface(
        self, showMenuButton=True, showReturnButton=True)
        self.stackWidget = QStackedWidget(self)

        # create sub interface
        self.searchInterface = Widget('Search Interface', self)
        self.deviceInterface = DeviceInterface(self)
       # self.musicInterface = Widget('Music Interface', self)
        self.videoInterface = Widget('Video Interface', self)
        self.folderInterface = Widget('Folder Interface', self)
        self.settingInterface = Widget('Setting Interface', self)
        self.logInterface = LogInterface('Work Log', self)
        # initialize layout
        self.initLayout()

        # add items to navigation interface
        self.initNavigation()

        self.initWindow()

    def initLayout(self):
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addWidget(self.stackWidget)
        self.hBoxLayout.setStretchFactor(self.stackWidget, 1)

        self.titleBar.raise_()
        self.navigationInterface.displayModeChanged.connect(self.titleBar.raise_)

    def initNavigation(self):
        # enable acrylic effect
        # self.navigationInterface.setAcrylicEnabled(True)

        self.addSubInterface(self.searchInterface, FIF.SEARCH, '主页')
        self.addSubInterface(self.deviceInterface, FIF.TILES, '查看设备')
        self.addSubInterface(self.videoInterface, FIF.VIDEO, 'Video library')

        self.navigationInterface.addSeparator()
        # 将工作日志添加到导航栏 (使用编辑图标
        self.addSubInterface(self.logInterface, FIF.EDIT, '工作日志', NavigationItemPosition.SCROLL)
        self.addSubInterface(self.folderInterface, FIF.FOLDER, 'Folder library', NavigationItemPosition.SCROLL)
        # add navigation items to scroll area
        self.addSubInterface(self.folderInterface, FIF.FOLDER, 'Folder library', NavigationItemPosition.SCROLL)
        # for i in range(1, 21):
        #     self.navigationInterface.addItem(
        #         f'folder{i}',
        #         FIF.FOLDER,
        #         f'Folder {i}',
        #         lambda: print('Folder clicked'),
        #         position=NavigationItemPosition.SCROLL
        #     )

        # add custom widget to bottom
        self.navigationInterface.addWidget(
            routeKey='avatar',
            widget=AvatarWidget(),
            onClick=self.showMessageBox,
            position=NavigationItemPosition.BOTTOM
        )

        self.addSubInterface(self.settingInterface, FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)

        #!IMPORTANT: don't forget to set the default route key
        qrouter.setDefaultRouteKey(self.stackWidget, self.searchInterface.objectName())

        # set the maximum width
        # self.navigationInterface.setExpandWidth(300)

        self.stackWidget.currentChanged.connect(self.onCurrentInterfaceChanged)
        self.stackWidget.setCurrentIndex(0)

    def initWindow(self):
        self.resize(900, 700)
        self.setWindowIcon(QIcon('resource/logo.png'))
        self.setWindowTitle('PyQt-Fluent-Widgets')
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

        self.setQss()

    def addSubInterface(self, interface, icon, text: str, position=NavigationItemPosition.TOP):
        """ add sub interface """
        self.stackWidget.addWidget(interface)
        self.navigationInterface.addItem(
            routeKey=interface.objectName(),
            icon=icon,
            text=text,
            onClick=lambda: self.switchTo(interface),
            position=position,
            tooltip=text
        )

    def setQss(self):
        color = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/{color}/demo.qss', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

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

    def resizeEvent(self, e):
        self.titleBar.move(46, 0)
        self.titleBar.resize(self.width()-46, self.titleBar.height())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec()