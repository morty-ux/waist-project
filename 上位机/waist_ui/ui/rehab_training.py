# coding: utf-8
"""
康复训练界面
占位界面，待开发
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import ScrollArea, TitleLabel


class RehabTrainingInterface(ScrollArea):
    """康复训练界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('rehabTrainingInterface')
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.__initWidget()

    def __initWidget(self):
        """初始化界面组件"""
        self.view.setObjectName('rehabTrainingView')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(20)

        label = TitleLabel('康复训练')
        label.setAlignment(Qt.AlignCenter)
        self.vBoxLayout.addWidget(label)

        self.vBoxLayout.addStretch()
