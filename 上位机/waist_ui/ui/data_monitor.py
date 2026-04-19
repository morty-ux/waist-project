# coding: utf-8
"""
数据监测界面
包含：电机状态显示（人体图+卡片）+ 连接状态 + 训练强度 + 实时反馈
"""

from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSlider
from PySide6.QtGui import QColor
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, BodyLabel, TitleLabel,
    CardWidget, SimpleCardWidget,
    ElevatedCardWidget, ProgressBar, CaptionLabel, ImageLabel,
    PrimaryPushButton, PushButton, Slider, DoubleSpinBox,
    SwitchButton
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


class SensorSlotCard(SimpleCardWidget):
    """传感器信号槽卡片"""

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.value = 0.0

        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        self.setFixedSize(120, 80)

    def __initLayout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        self.nameLabel = CaptionLabel(self.name)
        self.nameLabel.setTextColor(QColor(128, 128, 128))

        self.valueLabel = TitleLabel('0.00')
        self.valueLabel.setStyleSheet('font-size: 18px; font-weight: bold; color: #0078D4;')

        self.progressBar = ProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setFixedHeight(4)

        layout.addWidget(self.nameLabel)
        layout.addWidget(self.valueLabel)
        layout.addWidget(self.progressBar)

    def updateValue(self, value):
        """更新传感器值"""
        self.value = value
        self.valueLabel.setText(f'{self.value:.2f}')
        self.progressBar.setValue(int(min(value, 100)))


class BatchControlCard(CardWidget):
    """批量力控参数调节卡片 - 先调整后发送"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = {'LF': 0, 'LB': 0, 'RF': 0, 'RB': 0}
        self.sliders = {}
        self._batch_send_callback = None
        self.__initUI()

    def __initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = SubtitleLabel('批量调节')
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
            slider.valueChanged.connect(lambda v, ch=channel: self._onSliderChanged(ch, v))

            self.sliders[channel] = slider

            row_layout.addWidget(label)
            row_layout.addWidget(slider)

            layout.addWidget(row)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.send_btn = PrimaryPushButton('批量发送')
        self.send_btn.setFixedWidth(120)
        self.send_btn.clicked.connect(self._onBatchSend)

        btn_layout.addWidget(self.send_btn)
        layout.addLayout(btn_layout)

    def _onSliderChanged(self, channel, value):
        self.values[channel] = value

    def _onBatchSend(self):
        if self._batch_send_callback:
            self._batch_send_callback(
                self.values.get('RB', 0),
                self.values.get('RF', 0),
                self.values.get('LB', 0),
                self.values.get('LF', 0)
            )

    def setBatchSendCallback(self, callback):
        self._batch_send_callback = callback

    def get_values(self) -> dict:
        return self.values.copy()

    def set_values(self, values: dict):
        for ch, v in values.items():
            if ch in self.sliders:
                self.sliders[ch].blockSignals(True)
                self.sliders[ch].setValue(int(v))
                self.sliders[ch].blockSignals(False)
                self.values[ch] = v


class DataMonitorInterface(ScrollArea):
    """数据监测界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('dataMonitorInterface')
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.statusCards = {}
        self.sensorSlots = {}
        self.slider_spin_pairs = {}
        self._is_realtime_mode = True

        self._send_timer = QTimer(self)
        self._send_timer.setSingleShot(True)
        self._send_timer.timeout.connect(self._doSend)

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

        main_layout.addWidget(left_widget, 7)
        main_layout.addWidget(right_widget, 3)

        self.vBoxLayout.addLayout(main_layout)

    def __createLeftWidget(self):
        """左侧：人体图+电机状态卡片（4个卡片分布在人体图四周）"""
        card = ElevatedCardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(10)

        title = SubtitleLabel('康复设备监控')
        title.setStyleSheet("margin-bottom: 5px;")
        layout.addWidget(title)

        human_container = QWidget()
        human_layout = QGridLayout(human_container)
        human_layout.setContentsMargins(0, 0, 0, 0)
        human_layout.setSpacing(15)

        image_path = Path(__file__).parent.parent / 'resource' / 'body.png'
        human_label = ImageLabel(str(image_path))
        human_label.setFixedSize(300, 480)
        human_label.setBorderRadius(8, 8, 8, 8)

        self.statusCards['LF'] = StatusCard('左前 LF')
        self.statusCards['RF'] = StatusCard('右前 RF')
        self.statusCards['LB'] = StatusCard('左后 LB')
        self.statusCards['RB'] = StatusCard('右后 RB')

        human_layout.addWidget(self.statusCards['LF'], 0, 0, Qt.AlignRight | Qt.AlignVCenter)
        human_layout.addWidget(self.statusCards['RF'], 0, 2, Qt.AlignLeft | Qt.AlignVCenter)
        human_layout.addWidget(human_label, 0, 1, 3, 1, Qt.AlignCenter)
        human_layout.addWidget(self.statusCards['LB'], 2, 0, Qt.AlignRight | Qt.AlignVCenter)
        human_layout.addWidget(self.statusCards['RB'], 2, 2, Qt.AlignLeft | Qt.AlignVCenter)

        human_layout.setColumnStretch(0, 1)
        human_layout.setColumnStretch(1, 4)
        human_layout.setColumnStretch(2, 1)
        human_layout.setRowStretch(0, 1)
        human_layout.setRowStretch(1, 3)
        human_layout.setRowStretch(2, 1)

        layout.addWidget(human_container)

        return card

    def __createRightWidget(self):
        """右侧：连接状态 + 训练强度 + 实时反馈"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        connection_card = self.__createConnectionCard()
        force_control_card = self.__createForceControlCard()
        feedback_card = self.__createFeedbackCard()

        layout.addWidget(connection_card)
        layout.addWidget(force_control_card)
        layout.addWidget(feedback_card)
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
        """训练强度卡片（支持即时/统一模式切换）"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)

        title = SubtitleLabel('训练强度')
        title_layout.addWidget(title)

        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(8)

        self.mode_switch = SwitchButton()
        self.mode_switch.setOnText('即时')
        self.mode_switch.setOffText('统一')
        self.mode_switch.setChecked(True)
        self.mode_switch.checkedChanged.connect(self._onModeChanged)

        mode_layout.addWidget(self.mode_switch)
        mode_layout.addStretch()

        title_layout.addLayout(mode_layout)

        self.sendAllBtn = PrimaryPushButton('应用')
        self.sendAllBtn.setFixedWidth(70)
        self.sendAllBtn.hide()
        self.sendAllBtn.clicked.connect(self._onSendAllClicked)
        title_layout.addWidget(self.sendAllBtn)

        self.reset_btn = PushButton('恢复')
        self.reset_btn.clicked.connect(self.__onReset)
        self.reset_btn.setEnabled(False)
        self.reset_btn.setFixedWidth(60)
        title_layout.addWidget(self.reset_btn)

        layout.addLayout(title_layout)

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

    def __createFeedbackCard(self):
        """实时反馈卡片"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = SubtitleLabel('实时反馈')
        layout.addWidget(title)

        slots_layout = QHBoxLayout()
        slots_layout.setSpacing(10)

        self.sensorSlots['LF'] = SensorSlotCard('LF')
        self.sensorSlots['LB'] = SensorSlotCard('LB')
        self.sensorSlots['RF'] = SensorSlotCard('RF')
        self.sensorSlots['RB'] = SensorSlotCard('RB')

        slots_layout.addWidget(self.sensorSlots['LF'])
        slots_layout.addWidget(self.sensorSlots['LB'])
        slots_layout.addWidget(self.sensorSlots['RF'])
        slots_layout.addWidget(self.sensorSlots['RB'])

        layout.addLayout(slots_layout)

        return card

    def __createBatchControlCard(self):
        """批量调节卡片"""
        return BatchControlCard()

    def __createQuickActionsCard(self):
        """快捷操作卡片"""
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
            if hasattr(self, 'reset_btn'):
                self.reset_btn.setEnabled(True)
        else:
            self.connectionStatusLabel.setText('未连接')
            self.connectionStatusLabel.setStyleSheet('font-size: 16px; font-weight: bold; color: #E74C3C;')
            self.ipLabel.setText('等待设备连接...')
            if hasattr(self, 'reset_btn'):
                self.reset_btn.setEnabled(False)

    def updateMotorData(self, motor_data):
        """更新电机数据"""
        for channel, value in motor_data.items():
            if channel in self.statusCards:
                self.statusCards[channel].updateValue(value)

    def updateSensorData(self, sensor_data):
        """更新传感器数据（压力值）"""
        for channel, value in sensor_data.items():
            if channel in self.sensorSlots:
                self.sensorSlots[channel].updateValue(float(value))

    def __onSliderChanged(self, value, spin_box, channel):
        spin_box.blockSignals(True)
        spin_box.setValue(value)
        spin_box.blockSignals(False)
        self.statusCards[channel].updateValue(value)
        if self._is_realtime_mode:
            self._triggerSend(channel)

    def __onSpinBoxChanged(self, value, slider, channel):
        slider.blockSignals(True)
        slider.setValue(int(value))
        slider.blockSignals(False)
        self.statusCards[channel].updateValue(value)
        if self._is_realtime_mode:
            self._triggerSend(channel)

    def _onModeChanged(self, is_on):
        self._is_realtime_mode = is_on
        if is_on:
            self.sendAllBtn.hide()
        else:
            self.sendAllBtn.show()

    def _onSendAllClicked(self):
        if hasattr(self, '_on_force_changed'):
            current_values = self.get_motor_values()
            self._on_force_changed(
                current_values.get('RB', 0),
                current_values.get('RF', 0),
                current_values.get('LB', 0),
                current_values.get('LF', 0)
            )

    def _triggerSend(self, channel):
        if not hasattr(self, '_on_force_changed'):
            return
        self._send_timer.stop()
        self._send_timer.start(100)

    def _doSend(self):
        if hasattr(self, '_on_force_changed'):
            current_values = self.get_motor_values()
            self._on_force_changed(
                current_values.get('RB', 0),
                current_values.get('RF', 0),
                current_values.get('LB', 0),
                current_values.get('LF', 0)
            )

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

    def get_motor_values(self) -> dict:
        """获取所有电机值"""
        values = {}
        for channel, widgets in self.slider_spin_pairs.items():
            values[channel.upper()] = float(widgets['spinbox'].value())
        return values

    def reset_values(self):
        """重置所有值为0"""
        for channel in self.slider_spin_pairs:
            self.slider_spin_pairs[channel]['slider'].setValue(0)
            self.slider_spin_pairs[channel]['spinbox'].setValue(0)
            self.statusCards[channel].updateValue(0)
