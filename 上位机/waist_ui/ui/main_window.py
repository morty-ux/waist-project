# coding: utf-8
"""
主窗口
继承FluentWindow，管理所有子界面
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from qfluentwidgets import FluentWindow, NavigationItemPosition, FluentIcon

from ui.data_monitor import DataMonitorInterface
from ui.rehab_training import RehabTrainingInterface
from ui.fun_game import FunGameInterface
from ui.user_custom import UserCustomInterface


class MainWindow(FluentWindow):
    """主窗口 - 继承自 FluentWindow"""

    def __init__(self):
        super().__init__()
        self.__initWindow()
        self.__initNavigation()

    def __initWindow(self):
        """初始化窗口属性"""
        self.resize(1100, 700)
        self.setMinimumSize(1000, 640)
        self.setWindowTitle('康复医疗仪表盘')

    def __initNavigation(self):
        """初始化导航栏"""
        self.dataMonitorInterface = DataMonitorInterface(self)
        self.rehabTrainingInterface = RehabTrainingInterface(self)
        self.funGameInterface = FunGameInterface(self)
        self.userCustomInterface = UserCustomInterface(self)

        self.addSubInterface(
            self.dataMonitorInterface,
            FluentIcon.SPEED_HIGH,
            '数据监测'
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
