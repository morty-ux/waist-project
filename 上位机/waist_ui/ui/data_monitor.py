# coding: utf-8
"""
数据监测界面
包含：人体图 + 连接状态 + 训练强度 + sEMG实时折线图
"""

from pathlib import Path
import collections

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout
from PySide6.QtGui import QColor
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, BodyLabel, TitleLabel,
    CardWidget, SimpleCardWidget,
    ProgressBar, CaptionLabel, ImageLabel,
    PrimaryPushButton, PushButton, Slider, DoubleSpinBox,
    SwitchButton
)

# UI-only channel mapping. Keep motor values and packet order unchanged.
CHANNEL_DISPLAY_NAMES = {
    'LF': 'RB',
    'LB': 'RF',
    'RF': 'LB',
    'RB': 'LF',
}
CHANNEL_DISPLAY_ORDER = ['LF', 'LB', 'RF', 'RB']
CHANNEL_UI_ORDER = [
    next(internal for internal, display in CHANNEL_DISPLAY_NAMES.items() if display == display_channel)
    for display_channel in CHANNEL_DISPLAY_ORDER
]
STATUS_CARD_TITLES = {
    'RB': '左前 LF',
    'RF': '左后 LB',
    'LB': '右前 RF',
    'LF': '右后 RB',
}


class StatusCard(SimpleCardWidget):
    """电机状态卡片 - 紧凑版"""

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.value = 0

        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        self.setFixedHeight(56)

    def __initLayout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        self.nameLabel = CaptionLabel(self.name)
        self.nameLabel.setTextColor(QColor(96, 96, 96))
        self.nameLabel.setStyleSheet('font-size: 10px;')

        self.valueLabel = BodyLabel(f'{self.value}')
        self.valueLabel.setStyleSheet('font-size: 16px; font-weight: bold; color: #00A896;')

        self.progressBar = ProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setFixedHeight(4)

        layout.addWidget(self.nameLabel)
        layout.addWidget(self.valueLabel)
        layout.addWidget(self.progressBar)

    def updateValue(self, value):
        self.value = value
        self.valueLabel.setText(f'{self.value}')
        self.progressBar.setValue(int(value))


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

        channels = CHANNEL_UI_ORDER
        for channel in channels:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            label = BodyLabel(CHANNEL_DISPLAY_NAMES[channel])
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

    MAX_CHART_POINTS = 10000
    SEMG_VALUE_SCALE = 1024.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('dataMonitorInterface')
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.statusCards = {}
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

        main_layout.addWidget(left_widget, 5)
        main_layout.addWidget(right_widget, 5)

        self.vBoxLayout.addLayout(main_layout)

    def __createLeftWidget(self):
        """左侧：人体图 + 4个电机状态卡片"""
        card = QWidget()
        card.setObjectName('leftMonitorCard')
        card.setStyleSheet("""
            #leftMonitorCard {
                background-color: #FFFFFF;
                border: 1px solid #B2DFDB;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 0, 15, 15)
        layout.setSpacing(50)

        title = SubtitleLabel('康复设备监控')
        layout.addWidget(title)

        # 人体图居中显示，放大尺寸
        image_path = Path(__file__).parent.parent / 'resource' / 'body.png'
        human_label = ImageLabel(str(image_path))
        human_label.setFixedSize(360, 560)
        human_label.setBorderRadius(8, 8, 8, 8)
        layout.addWidget(human_label, 0, Qt.AlignHCenter)

        # LF/LB/RF/RB 四个卡片 1×4 横排在人体图下方
        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)

        for key in CHANNEL_UI_ORDER:
            self.statusCards[key] = StatusCard(STATUS_CARD_TITLES[key])
            cards_row.addWidget(self.statusCards[key])

        layout.addLayout(cards_row)

        return card

    def __createRightWidget(self):
        """右侧：连接状态 + 训练强度 + sEMG实时折线图"""
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

        channels = CHANNEL_UI_ORDER

        for channel in channels:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            label = BodyLabel(CHANNEL_DISPLAY_NAMES[channel])
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
        """实时反馈卡片 - sEMG折线图（pyqtgraph）"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = SubtitleLabel('sEMG 实时监控')
        layout.addWidget(title)

        # pyqtgraph 折线图
        self._semg_plot = pg.PlotWidget()
        self._semg_plot.setBackground('w')
        self._semg_plot.showGrid(x=True, y=True, alpha=0.3)
        self._semg_plot.setLabel('left', 'Amplitude')
        self._semg_plot.setLabel('bottom', '样本')
        self._semg_plot.setYRange(-4096, 4096)
        self._semg_plot.setMinimumHeight(250)
        self._semg_plot.getPlotItem().hideButtons()

        pen_wave = pg.mkPen(color='#0078D4', width=1)
        self._semg_waveform_curve = self._semg_plot.plot(pen=pen_wave)
        pen_rect = pg.mkPen(color='#0078D4', width=2)
        self._semg_rectified_curve = self._semg_plot.plot(pen=pen_rect)
        pen_env = pg.mkPen(color='#E74C3C', width=3)
        self._semg_envelope_curve = self._semg_plot.plot(pen=pen_env)

        layout.addWidget(self._semg_plot)

        self._semg_value_label = BodyLabel('当前: ---')
        self._semg_value_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #0078D4;')
        layout.addWidget(self._semg_value_label)

        # 数据缓冲
        self._waveform_data = collections.deque(maxlen=self.MAX_CHART_POINTS)
        self._rectified_data = collections.deque(maxlen=self.MAX_CHART_POINTS)
        self._envelope_data = collections.deque(maxlen=self.MAX_CHART_POINTS)
        self._semg_point_count = 0
        self._semg_last_update = 0

        return card

    def __createBatchControlCard(self):
        """批量调节卡片"""
        return BatchControlCard()

    def append_sEMG_data(self, sample):
        """添加sEMG数据点并更新折线图（pyqtgraph 批量 setData）"""
        if isinstance(sample, (tuple, list)) and len(sample) >= 3:
            waveform, rectified, envelope = sample[:3]
        else:
            waveform = sample
            rectified = abs(sample)
            envelope = abs(sample)

        self._waveform_data.append(waveform)
        self._rectified_data.append(rectified)
        self._envelope_data.append(envelope)
        self._semg_point_count += 1

        # 降频 ~60fps
        import time
        now = time.time()
        if now - self._semg_last_update < 0.016:
            return
        self._semg_last_update = now

        n = len(self._waveform_data)
        if self._semg_point_count <= self.MAX_CHART_POINTS:
            start_idx = 0
        else:
            start_idx = self._semg_point_count - n

        x = np.arange(start_idx, self._semg_point_count)
        self._semg_waveform_curve.setData(x=x, y=np.array(self._waveform_data, dtype=np.float64))
        self._semg_rectified_curve.setData(x=x, y=np.array(self._rectified_data, dtype=np.float64))
        self._semg_envelope_curve.setData(x=x, y=np.array(self._envelope_data, dtype=np.float64))

        if self._semg_point_count <= self.MAX_CHART_POINTS:
            self._semg_plot.setXRange(0, self.MAX_CHART_POINTS)
        else:
            self._semg_plot.setXRange(start_idx, start_idx + self.MAX_CHART_POINTS)

        val = self._envelope_data[-1] / self.SEMG_VALUE_SCALE if n > 0 else 0
        self._semg_value_label.setText(f'当前: sEMG: {val:.2f}')

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

    def updateSensorData(self, sensor_data):
        """更新传感器数据（保留兼容）"""
        pass

    def updateMotorData(self, motor_data):
        """更新电机数据"""
        for channel, value in motor_data.items():
            if channel in self.statusCards:
                self.statusCards[channel].updateValue(value)

    def __onSliderChanged(self, value, spin_box, channel):
        spin_box.blockSignals(True)
        spin_box.setValue(value)
        spin_box.blockSignals(False)
        if channel in self.statusCards:
            self.statusCards[channel].updateValue(value)
        if self._is_realtime_mode:
            self._triggerSend(channel)

    def __onSpinBoxChanged(self, value, slider, channel):
        slider.blockSignals(True)
        slider.setValue(int(value))
        slider.blockSignals(False)
        if channel in self.statusCards:
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
            if channel in self.statusCards:
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
            if channel in self.statusCards:
                self.statusCards[channel].updateValue(0)
