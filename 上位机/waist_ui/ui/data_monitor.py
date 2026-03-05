# coding: utf-8
"""
数据监测界面
包含：电机状态显示（人体图+卡片）+ 连接状态 + 力控调节
"""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
from PySide6.QtGui import QColor
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, BodyLabel, TitleLabel,
    CardWidget, SimpleCardWidget,
    ElevatedCardWidget, ProgressBar, CaptionLabel, ImageLabel,
    PrimaryPushButton, PushButton, Slider, DoubleSpinBox
)


class StatusCard(SimpleCardWidget):
    """电机状态卡片"""

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.value = 0

        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        self.setFixedSize(140, 100)

    def __initLayout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.nameLabel = CaptionLabel(self.name)
        self.nameLabel.setTextColor(QColor(96, 96, 96))

        self.valueLabel = TitleLabel(f'{self.value}')
        self.valueLabel.setStyleSheet('font-size: 24px; font-weight: bold; color: #00A896;')

        self.progressBar = ProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setFixedHeight(6)

        from qfluentwidgets import InfoBadge
        self.badge = InfoBadge.success('正常')

        layout.addWidget(self.nameLabel)
        layout.addWidget(self.valueLabel)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.badge, 0, Qt.AlignRight)

    def updateValue(self, value):
        self.value = value
        self.valueLabel.setText(f'{self.value}')
        self.progressBar.setValue(int(value))


class DataMonitorInterface(ScrollArea):
    """数据监测界面"""

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
        self.view.setObjectName('dataMonitorView')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(20)

    def __initLayout(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)

        left_widget = self.__createLeftWidget()
        right_widget = self.__createRightWidget()

        main_layout.addWidget(left_widget, 6)
        main_layout.addWidget(right_widget, 4)

        self.vBoxLayout.addLayout(main_layout)

    def __createLeftWidget(self):
        """左侧：人体图+电机状态卡片"""
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

        # 卡片: 左前LF 右前RF 左后LB 右后RB
        self.statusCards['LF'] = StatusCard('左前 LF')
        self.statusCards['RF'] = StatusCard('右前 RF')
        self.statusCards['LB'] = StatusCard('左后 LB')
        self.statusCards['RB'] = StatusCard('右后 RB')

        human_layout.addWidget(self.statusCards['LF'], 0, 1, Qt.AlignLeft | Qt.AlignTop)
        human_layout.addWidget(self.statusCards['RF'], 0, 1, Qt.AlignRight | Qt.AlignTop)
        human_layout.addWidget(self.statusCards['LB'], 3, 1, Qt.AlignLeft | Qt.AlignBottom)
        human_layout.addWidget(self.statusCards['RB'], 3, 1, Qt.AlignRight | Qt.AlignBottom)

        layout.addWidget(human_container)

        return card

    def __createRightWidget(self):
        """右侧：连接状态 + 力控调节"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        connection_card = self.__createConnectionCard()
        force_control_card = self.__createForceControlCard()
        quick_actions_card = self.__createQuickActionsCard()

        layout.addWidget(connection_card)
        layout.addWidget(force_control_card)
        layout.addWidget(quick_actions_card)
        layout.addStretch()

        return widget

    def __createConnectionCard(self):
        """连接状态卡片"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = SubtitleLabel('连接状态')
        layout.addWidget(title)

        self.connectionStatusLabel = BodyLabel('未连接')
        self.connectionStatusLabel.setStyleSheet('font-size: 16px; font-weight: bold; color: #E74C3C;')
        layout.addWidget(self.connectionStatusLabel)

        self.ipLabel = CaptionLabel('等待设备连接...')
        self.ipLabel.setTextColor(QColor(128, 128, 128))
        layout.addWidget(self.ipLabel)

        return card

    def __createForceControlCard(self):
        """力控参数调节卡片"""
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
        """快捷指令卡片"""
        card = SimpleCardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = SubtitleLabel('快捷指令')
        layout.addWidget(title)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.identify_btn = PrimaryPushButton('参数自动辨识')
        self.identify_btn.clicked.connect(self.__onIdentify)
        self.identify_btn.setEnabled(False)

        self.reset_btn = PushButton('系统复位')
        self.reset_btn.clicked.connect(self.__onReset)
        self.reset_btn.setEnabled(False)

        button_layout.addWidget(self.identify_btn)
        button_layout.addWidget(self.reset_btn)

        layout.addLayout(button_layout)

        return card

    def setConnectionStatus(self, connected, ip=None):
        """设置连接状态"""
        if connected:
            self.connectionStatusLabel.setText('已连接')
            self.connectionStatusLabel.setStyleSheet('font-size: 16px; font-weight: bold; color: #27AE60;')
            self.ipLabel.setText(f"设备: {ip}" if ip else '已连接')
            self.identify_btn.setEnabled(True)
            self.reset_btn.setEnabled(True)
        else:
            self.connectionStatusLabel.setText('未连接')
            self.connectionStatusLabel.setStyleSheet('font-size: 16px; font-weight: bold; color: #E74C3C;')
            self.ipLabel.setText('等待设备连接...')
            self.identify_btn.setEnabled(False)
            self.reset_btn.setEnabled(False)

    def updateMotorData(self, motor_data):
        """更新电机数据"""
        for channel, value in motor_data.items():
            if channel in self.statusCards:
                self.statusCards[channel].updateValue(value)

    def __onSliderChanged(self, value, spin_box, channel):
        spin_box.setValue(value)
        self.statusCards[channel].updateValue(value)
        if hasattr(self, '_on_force_changed'):
            self._on_force_changed(channel, int(value))

    def __onSpinBoxChanged(self, value, slider, channel):
        slider.setValue(int(value))
        self.statusCards[channel].updateValue(value)
        if hasattr(self, '_on_force_changed'):
            self._on_force_changed(channel, int(value))

    def __onIdentify(self):
        if hasattr(self, '_on_identify'):
            self._on_identify()

    def __onReset(self):
        if hasattr(self, '_on_reset'):
            self._on_reset()
        for channel in self.slider_spin_pairs:
            self.slider_spin_pairs[channel]['slider'].setValue(0)
            self.slider_spin_pairs[channel]['spinbox'].setValue(0)
            self.statusCards[channel].updateValue(0)

    def setForceChangedCallback(self, callback):
        self._on_force_changed = callback

    def setIdentifyCallback(self, callback):
        self._on_identify = callback

    def setResetCallback(self, callback):
        self._on_reset = callback
