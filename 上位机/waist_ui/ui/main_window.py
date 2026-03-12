# coding: utf-8
"""
主窗口
5个Tab：数据监测、通信日志、康复训练、趣味游戏、用户自定义
"""

from PySide6.QtCore import Qt
from qfluentwidgets import FluentWindow, NavigationItemPosition, FluentIcon, InfoBar, InfoBarPosition

from ui.data_monitor import DataMonitorInterface
from ui.log_interface import LogInterface
from ui.rehab_training import RehabTrainingInterface
from ui.fun_game import FunGameInterface
from ui.user_custom import UserCustomInterface


class MainWindow(FluentWindow):
    """主窗口 - 5个Tab"""

    def __init__(self):
        super().__init__()
        self.tcp_client = None
        self.__initWindow()
        self.__initNavigation()
        self.__initCommunication()

    def __initWindow(self):
        self.resize(1200, 750)
        self.setMinimumSize(1100, 700)
        self.setWindowTitle('康复医疗仪表盘')

    def __initNavigation(self):
        self.dataMonitorInterface = DataMonitorInterface(self)
        self.logInterface = LogInterface(self)
        self.rehabTrainingInterface = RehabTrainingInterface(self)
        self.funGameInterface = FunGameInterface(self)
        self.userCustomInterface = UserCustomInterface(self)

        self.addSubInterface(
            self.dataMonitorInterface,
            FluentIcon.SPEED_HIGH,
            '数据监测'
        )
        self.addSubInterface(
            self.logInterface,
            FluentIcon.CHAT,
            '通信日志'
        )
        self.addSubInterface(
            self.rehabTrainingInterface,
            FluentIcon.GAME,
            '康复训练'
        )
        self.addSubInterface(
            self.funGameInterface,
            FluentIcon.EMOJI_TAB_SYMBOLS,
            '趣味游戏'
        )
        self.addSubInterface(
            self.userCustomInterface,
            FluentIcon.SETTING,
            '用户自定义',
            NavigationItemPosition.BOTTOM
        )

    def __initCommunication(self):
        from communication import TCPClient

        self.tcp_client = TCPClient(ip="192.168.4.1", port=8080)

        self.tcp_client.connected.connect(self.__onConnected)
        self.tcp_client.disconnected.connect(self.__onDisconnected)
        self.tcp_client.raw_data_received.connect(self.__onRawDataReceived)
        self.tcp_client.rx_data_changed.connect(self.__onRxDataChanged)
        self.tcp_client.error_occurred.connect(self.__onError)
        self.tcp_client.log_message.connect(self.__onLogMessage)

        self.dataMonitorInterface.setForceChangedCallback(self.__onForceChanged)
        self.dataMonitorInterface.setResetCallback(self.__onReset)

        self.logInterface.setConnectCallback(self.__onConnectClicked)
        self.logInterface.setSendCommandCallback(self.__onSendCommand)

        self.logInterface.addLog('INFO', '请在通信日志界面输入IP地址和端口，点击连接')

    def __onConnectClicked(self, ip, port):
        """连接按钮点击"""
        self.tcp_client.set_server(ip, port)
        self.tcp_client.connect_to_server()

    def __onConnected(self):
        self.dataMonitorInterface.setConnectionStatus(True, f"{self.tcp_client.tcp_server_ip}:{self.tcp_client.tcp_server_port}")
        self.logInterface.setConnectionState(True)
        self.logInterface.addLog('INFO', f"已连接到 {self.tcp_client.tcp_server_ip}:{self.tcp_client.tcp_server_port}")

        local_ip = self.tcp_client.get_local_ip()
        self.logInterface.addLog('INFO', f"本地IP: {local_ip}")

        InfoBar.success(
            title='连接成功',
            content=f"已连接到 {self.tcp_client.tcp_server_ip}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def __onDisconnected(self):
        self.dataMonitorInterface.setConnectionStatus(False)
        self.logInterface.setConnectionState(False)
        self.logInterface.addLog('WARNING', '连接已断开')

    def __onRawDataReceived(self, data):
        hex_str = ' '.join(f'{b:02X}' for b in data)
        self.logInterface.addLog('DEBUG', f"[RX] {hex_str}")

    def __onRxDataChanged(self, data):
        self.logInterface.addLog('DEBUG', f"[RX] {data}")

    def __onLogMessage(self, level, message):
        self.logInterface.addLog(level, message)

    def __onError(self, error_msg):
        self.logInterface.addLog('ERROR', error_msg)

        InfoBar.error(
            title='通信错误',
            content=error_msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    def __onForceChanged(self, rb, rf, lb, lf):
        self.tcp_client.send_motor_cmd(rb, rf, lb, lf)

    def __onReset(self):
        self.dataMonitorInterface.reset_values()
        self.logInterface.addLog('INFO', '系统已复位')

        self.tcp_client.send_motor_cmd(0, 0, 0, 0)

    def __onSendCommand(self, command):
        self.logInterface.addLog('INFO', f"发送命令: {command}")
        self.tcp_client.send_text(command)
