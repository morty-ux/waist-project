# coding: utf-8
"""
数据监测界面
显示传感器数据和控制面板
"""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
from PySide6.QtGui import QColor
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, BodyLabel, TitleLabel,
    CardWidget, SimpleCardWidget,
    ElevatedCardWidget, PushButton, PrimaryPushButton, Slider,
    DoubleSpinBox, InfoBar, InfoBarPosition, InfoBadge,
    ProgressBar, CaptionLabel, ImageLabel
)


class StatusCard(SimpleCardWidget):
    """悬浮状态卡片 - 显示传感器数据"""

    def __init__(self, name, channel, parent=None):
        super().__init__(parent)
        self.name = name
        self.channel = channel
        self.value = 0.0

        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        """初始化组件"""
        self.setFixedSize(140, 100)

    def __initLayout(self):
        """初始化布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.nameLabel = CaptionLabel(self.name)
        self.nameLabel.setTextColor(QColor(96, 96, 96))

        self.valueLabel = TitleLabel(f'{self.value:.1f} N')
        self.valueLabel.setStyleSheet('font-size: 24px; font-weight: bold; color: #00A896;')

        self.progressBar = ProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setFixedHeight(6)

        self.badge = InfoBadge.success('正常')

        layout.addWidget(self.nameLabel)
        layout.addWidget(self.valueLabel)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.badge, 0, Qt.AlignRight)

    def updateValue(self, value):
        """更新数值"""
        self.value = value
        self.valueLabel.setText(f'{self.value:.1f} N')
        self.progressBar.setValue(int(value))

        if value > 80:
            self.badge = InfoBadge.warning('过载')
        elif value > 50:
            self.badge = InfoBadge.attension('警告')
        else:
            self.badge = InfoBadge.success('正常')


class DataMonitorInterface(ScrollArea):
    """数据监测界面 - 主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('dataMonitorInterface')
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.statusCards = {}
        self.slider_spin_pairs = {}

        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        """初始化界面组件"""
        self.view.setObjectName('dataMonitorView')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(20)

    def __initLayout(self):
        """初始化布局"""
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)

        left_widget = self.__createLeftWidget()
        right_widget = self.__createRightWidget()

        main_layout.addWidget(left_widget, 7)
        main_layout.addWidget(right_widget, 3)

        self.vBoxLayout.addLayout(main_layout)

    def __createLeftWidget(self):
        """创建左侧患者数字孪生区"""
        card = ElevatedCardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = SubtitleLabel('康复设备监控')
        layout.addWidget(title)

        human_container = QWidget()
        human_layout = QGridLayout(human_container)
        human_layout.setContentsMargins(0, 0, 0, 0)
        human_layout.setSpacing(0)

        image_path = Path(__file__).parent.parent / 'resource' / 'body.png'
        human_label = ImageLabel(str(image_path))
        human_label.setFixedSize(300, 500)
        human_label.setBorderRadius(8, 8, 8, 8)
        human_label.scaledToHeight(500)

        human_layout.addWidget(human_label, 0, 0, 4, 1, Qt.AlignCenter)

        self.statusCards['LF'] = StatusCard('左肩 LF', 'LF')
        self.statusCards['RF'] = StatusCard('右肩 RF', 'RF')
        self.statusCards['LB'] = StatusCard('左膝 LB', 'LB')
        self.statusCards['RB'] = StatusCard('右膝 RB', 'RB')

        human_layout.addWidget(self.statusCards['LF'], 0, 1, Qt.AlignLeft | Qt.AlignTop)
        human_layout.addWidget(self.statusCards['RF'], 0, 1, Qt.AlignRight | Qt.AlignTop)
        human_layout.addWidget(self.statusCards['LB'], 3, 1, Qt.AlignLeft | Qt.AlignBottom)
        human_layout.addWidget(self.statusCards['RB'], 3, 1, Qt.AlignRight | Qt.AlignBottom)

        layout.addWidget(human_container)

        return card

    def __createRightWidget(self):
        """创建右侧指挥控制中心"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        force_control_card = self.__createForceControlCard()
        quick_actions_card = self.__createQuickActionsCard()
        system_status_card = self.__createSystemStatusCard()

        layout.addWidget(force_control_card)
        layout.addWidget(quick_actions_card)
        layout.addWidget(system_status_card)
        layout.addStretch()

        return widget

    def __createForceControlCard(self):
        """创建力控参数调节卡片"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = SubtitleLabel('力控参数调节')
        layout.addWidget(title)

        channels = ['LF', 'LB', 'RF', 'RB']

        for channel in channels:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            label = BodyLabel(channel)
            label.setFixedWidth(30)

            slider = Slider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(0)

            spin_box = DoubleSpinBox()
            spin_box.setRange(0, 100)
            spin_box.setValue(0)
            spin_box.setDecimals(2)
            spin_box.setFixedWidth(80)

            slider.valueChanged.connect(lambda v, sb=spin_box, ch=channel: self.__onSliderChanged(v, sb, ch))
            spin_box.valueChanged.connect(lambda v, s=slider, ch=channel: self.__onSpinBoxChanged(v, s, ch))

            self.slider_spin_pairs[channel] = {
                'slider': slider,
                'spinbox': spin_box
            }

            row_layout.addWidget(label)
            row_layout.addWidget(slider)
            row_layout.addWidget(spin_box)

            layout.addWidget(row)

        return card

    def __createQuickActionsCard(self):
        """创建快捷指令卡片"""
        card = SimpleCardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = SubtitleLabel('快捷指令')
        layout.addWidget(title)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        identify_btn = PrimaryPushButton('参数自动辨识')
        identify_btn.clicked.connect(self.__onIdentify)

        reset_btn = PushButton('系统复位')
        reset_btn.clicked.connect(self.__onReset)

        button_layout.addWidget(identify_btn)
        button_layout.addWidget(reset_btn)

        layout.addLayout(button_layout)

        return card

    def __createSystemStatusCard(self):
        """创建系统状态卡片"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = SubtitleLabel('系统状态')
        layout.addWidget(title)

        self.statusLabel = BodyLabel('系统就绪，通讯正常')
        self.statusLabel.setStyleSheet('color: #00A896; font-weight: bold;')

        layout.addWidget(self.statusLabel)

        self.retry_btn = PrimaryPushButton('点击重试')
        self.retry_btn.setObjectName('retry_btn')
        self.retry_btn.setFixedHeight(40)
        self.retry_btn.clicked.connect(self.__onRetry)
        self.retry_btn.hide()

        layout.addWidget(self.retry_btn)

        return card

    def __onSliderChanged(self, value, spin_box, channel):
        """滑动条数值改变"""
        spin_box.setValue(value)
        self.statusCards[channel].updateValue(value)

    def __onSpinBoxChanged(self, value, slider, channel):
        """数字框数值改变"""
        slider.setValue(int(value))
        self.statusCards[channel].updateValue(value)

    def __onIdentify(self):
        """参数自动辨识"""
        InfoBar.info(
            title='提示',
            content='参数自动辨识中...',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def __onReset(self):
        """系统复位"""
        for channel in self.slider_spin_pairs:
            self.slider_spin_pairs[channel]['slider'].setValue(0)
            self.slider_spin_pairs[channel]['spinbox'].setValue(0)
            self.statusCards[channel].updateValue(0)

        InfoBar.success(
            title='成功',
            content='系统已复位',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def __onRetry(self):
        """点击重试"""
        InfoBar.warning(
            title='警告',
            content='正在重试...',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
