# coding: utf-8
"""
主窗口
5个Tab：数据监测、通信日志、康复训练、趣味游戏、用户自定义
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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
        self.comm_manager = None
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
        from communication import CommunicationManager

        self.comm_manager = CommunicationManager(host='0.0.0.0', port=8080)

        self.comm_manager.connection_changed.connect(self.__onConnectionChanged)
        self.comm_manager.sensor_data_received.connect(self.__onSensorDataReceived)
        self.comm_manager.log_message.connect(self.__onLogMessage)
        self.comm_manager.error_occurred.connect(self.__onError)

        self.dataMonitorInterface.setForceChangedCallback(self.__onForceChanged)
        self.dataMonitorInterface.setIdentifyCallback(self.__onIdentify)
        self.dataMonitorInterface.setResetCallback(self.__onReset)

        self.logInterface.setSendCommandCallback(self.__onSendCommand)

        self.comm_manager.start()

    def __onConnectionChanged(self, connected):
        if connected:
            info = self.comm_manager.get_connection_info()
            self.dataMonitorInterface.setConnectionStatus(True, f"{info['ip']}:{info['port']}")
            self.logInterface.addLog('INFO', f"已连接到设备: {info['ip']}:{info['port']}")

            InfoBar.success(
                title='连接成功',
                content='已连接到ESP8266设备',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            self.dataMonitorInterface.setConnectionStatus(False)
            self.logInterface.addLog('WARNING', '设备已断开连接')

    def __onSensorDataReceived(self, sensor_data):
        self.dataMonitorInterface.updateMotorData(sensor_data)

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

    def __onForceChanged(self, channel, value):
        self.comm_manager.set_force(channel, value)

    def __onIdentify(self):
        self.comm_manager.identify_parameters()
        self.logInterface.addLog('INFO', '发送参数辨识命令')

    def __onReset(self):
        self.comm_manager.reset_system()
        self.logInterface.addLog('INFO', '发送系统复位命令')

    def __onSendCommand(self, command):
        self.logInterface.addLog('INFO', f"发送命令: {command}")
