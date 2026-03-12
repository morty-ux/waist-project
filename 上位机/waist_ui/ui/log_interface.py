# coding: utf-8
"""
通信日志界面
包含：连接控制 + 日志显示 + 命令输入
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QColor, QTextCharFormat, QFont
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, BodyLabel, CaptionLabel,
    CardWidget, SimpleCardWidget,
    TextEdit, LineEdit, PrimaryPushButton, PushButton
)


class LogInterface(ScrollArea):
    """通信日志界面 - 连接控制 + 日志显示 + 命令输入"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('logInterface')
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        self.view.setObjectName('logView')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(20)

    def __initLayout(self):
        connection_card = self.__createConnectionCard()
        log_card = self.__createLogCard()
        command_card = self.__createCommandCard()

        self.vBoxLayout.addWidget(connection_card, 0)
        self.vBoxLayout.addWidget(log_card, 1)
        self.vBoxLayout.addWidget(command_card, 0)

    def __createConnectionCard(self):
        """连接控制卡片"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = SubtitleLabel('连接控制')
        layout.addWidget(title)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        ip_label = BodyLabel('IP:')
        self.ipInput = LineEdit()
        self.ipInput.setPlaceholderText('192.168.4.1')
        self.ipInput.setText('192.168.4.1')
        self.ipInput.setFixedWidth(150)

        port_label = BodyLabel('端口:')
        self.portInput = LineEdit()
        self.portInput.setPlaceholderText('8080')
        self.portInput.setText('8080')
        self.portInput.setFixedWidth(80)

        self.connectBtn = PrimaryPushButton('连接')
        self.connectBtn.setFixedWidth(80)
        self.connectBtn.clicked.connect(self.__onConnectClicked)

        input_layout.addWidget(ip_label)
        input_layout.addWidget(self.ipInput)
        input_layout.addWidget(port_label)
        input_layout.addWidget(self.portInput)
        input_layout.addWidget(self.connectBtn)
        input_layout.addStretch()

        layout.addLayout(input_layout)

        self.statusLabel = CaptionLabel('未连接')
        self.statusLabel.setTextColor(QColor(128, 128, 128))
        layout.addWidget(self.statusLabel)

        return card

    def __createLogCard(self):
        """日志显示卡片"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_layout = QHBoxLayout()
        title = SubtitleLabel('通信日志')
        title_layout.addWidget(title)
        title_layout.addStretch()

        self.clearBtn = PushButton('清空')
        self.clearBtn.setFixedWidth(60)
        self.clearBtn.clicked.connect(self.clearLog)
        title_layout.addWidget(self.clearBtn)

        layout.addLayout(title_layout)

        self.logTextEdit = TextEdit()
        self.logTextEdit.setReadOnly(True)
        self.logTextEdit.setFont(QFont('Consolas', 9))
        layout.addWidget(self.logTextEdit)

        return card

    def __createCommandCard(self):
        """命令输入卡片"""
        card = SimpleCardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = SubtitleLabel('发送命令')
        layout.addWidget(title)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.commandInput = LineEdit()
        self.commandInput.setPlaceholderText('输入命令...')
        self.commandInput.returnPressed.connect(self.__onSendCommand)

        self.sendBtn = PrimaryPushButton('发送')
        self.sendBtn.setFixedWidth(80)
        self.sendBtn.clicked.connect(self.__onSendCommand)

        input_layout.addWidget(self.commandInput, 1)
        input_layout.addWidget(self.sendBtn)

        layout.addLayout(input_layout)

        help_label = CaptionLabel('提示: 电机控制命令格式请参考通信协议')
        help_label.setTextColor(QColor(128, 128, 128))
        layout.addWidget(help_label)

        return card

    def __onConnectClicked(self):
        """连接按钮点击"""
        if hasattr(self, '_on_connect_clicked'):
            ip = self.ipInput.text().strip()
            port = int(self.portInput.text().strip())
            self._on_connect_clicked(ip, port)

    def setConnectionState(self, connected):
        """设置连接状态"""
        if connected:
            self.statusLabel.setText('已连接')
            self.statusLabel.setTextColor(QColor(39, 174, 96))
            self.connectBtn.setText('断开')
            self.ipInput.setEnabled(False)
            self.portInput.setEnabled(False)
        else:
            self.statusLabel.setText('未连接')
            self.statusLabel.setTextColor(QColor(128, 128, 128))
            self.connectBtn.setText('连接')
            self.ipInput.setEnabled(True)
            self.portInput.setEnabled(True)

    def setConnectCallback(self, callback):
        """设置连接按钮回调"""
        self._on_connect_clicked = callback

    def addLog(self, level, message):
        """添加日志"""
        import datetime
        time_str = datetime.datetime.now().strftime('%H:%M:%S')

        format = QTextCharFormat()
        if level == 'INFO':
            format.setForeground(QColor('#3498DB'))
        elif level == 'WARNING':
            format.setForeground(QColor('#F39C12'))
        elif level == 'ERROR':
            format.setForeground(QColor('#E74C3C'))
        elif level == 'DEBUG':
            format.setForeground(QColor('#95A5A6'))
        else:
            format.setForeground(QColor('#000000'))

        cursor = self.logTextEdit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        cursor.insertText(f"[{time_str}] ", QTextCharFormat())
        cursor.insertText(f"[{level}] ", format)
        cursor.insertText(f"{message}\n")

        self.logTextEdit.setTextCursor(cursor)
        self.logTextEdit.ensureCursorVisible()

    def clearLog(self):
        """清空日志"""
        self.logTextEdit.clear()

    def __onSendCommand(self):
        """发送命令"""
        command = self.commandInput.text().strip()
        if command and hasattr(self, '_on_send_command'):
            self._on_send_command(command)
            self.commandInput.clear()

    def setSendCommandCallback(self, callback):
        """设置发送命令回调"""
        self._on_send_command = callback
