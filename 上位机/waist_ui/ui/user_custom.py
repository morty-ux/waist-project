# coding: utf-8
"""
用户自定义界面
占位界面，待开发
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import ScrollArea, TitleLabel


class UserCustomInterface(ScrollArea):
    """用户自定义界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('userCustomInterface')
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.__initWidget()

    def __initWidget(self):
        """初始化界面组件"""
        self.view.setObjectName('userCustomView')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(20)

        label = TitleLabel('用户自定义')
        label.setAlignment(Qt.AlignCenter)
        self.vBoxLayout.addWidget(label)

        self.vBoxLayout.addStretch()
