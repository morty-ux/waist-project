# coding: utf-8
import collections
from datetime import datetime

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer, QPointF, Signal
from PySide6.QtGui import QDoubleValidator, QColor, QPainter, QBrush
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    ScrollArea,
    SubtitleLabel,
    BodyLabel,
    CaptionLabel,
    CardWidget,
    SimpleCardWidget,
    LineEdit,
    ProgressBar,
    ComboBox,
    PrimaryPushButton,
    PushButton,
)

MOTION_TYPES = [
    '前向弯腰',
    '侧向弯腰',
    '转身',
]

DEFAULT_MOTIONS = [
    (0, 0.2),
    (1, 0.2),
    (2, 0.2),
]

_ELLIPSIS_COLORS = ['#e15b64', '#f47e60', '#f8b26a', '#abbd81', '#e15b64']


class EllipsisSpinner(QWidget):

    def __init__(self, size=18, parent=None):
        super().__init__(parent)
        width = size + (len(_ELLIPSIS_COLORS) - 1) * 8
        self.setFixedSize(width, size)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(60)
        self._timer.start()

    def _tick(self):
        self._phase += 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        count = len(_ELLIPSIS_COLORS)
        spacing = 8
        total_width = (count - 1) * spacing
        start_x = center_x - total_width / 2.0
        period = 18

        for index, color_value in enumerate(_ELLIPSIS_COLORS):
            offset = (self._phase - index * (period // count)) % period
            progress = offset / float(period)
            scale = progress * 2.0 if progress < 0.5 else (1.0 - progress) * 2.0
            radius = 2.0 + scale * 5.0
            x = start_x + index * spacing

            color = QColor(color_value)
            color.setAlpha(int(80 + scale * 175))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x, center_y), radius, radius)

        painter.end()

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()


class AngleInputCard(SimpleCardWidget):

    def __init__(self, motion_type=0, angle=0.2, parent=None):
        super().__init__(parent)
        self._motion_combo = None
        self._angle_input = None
        self.__initUI(motion_type, angle)

    def __initUI(self, motion_type, angle):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self._motion_combo = ComboBox()
        self._motion_combo.addItems(MOTION_TYPES)
        self._motion_combo.setCurrentIndex(motion_type)
        self._motion_combo.setFixedWidth(120)
        layout.addWidget(self._motion_combo)

        validator = QDoubleValidator(-9999.0, 9999.0, 2)

        angle_label = CaptionLabel('角度:')
        layout.addWidget(angle_label)

        self._angle_input = LineEdit()
        self._angle_input.setFixedWidth(80)
        self._angle_input.setValidator(validator)
        self._angle_input.setText(str(angle))
        layout.addWidget(self._angle_input)

        layout.addStretch()

        self._delete_btn = PushButton('删除')
        self._delete_btn.setFixedWidth(70)
        layout.addWidget(self._delete_btn)

    def getName(self):
        return MOTION_TYPES[self._motion_combo.currentIndex()]

    def getAngles(self):
        try:
            value = float(self._angle_input.text())
        except ValueError:
            value = 0.0

        motion_index = self._motion_combo.currentIndex()
        if motion_index == 0:
            return (0.0, 0.0, value)
        if motion_index == 1:
            return (0.0, -value, 0.0)
        return (value, 0.0, 0.0)

    def setDeleteCallback(self, callback):
        self._delete_btn.clicked.connect(lambda checked=False, current=callback: current())


class PresetMotionInterface(ScrollArea):
    training_started = Signal(object)

    MAX_CHART_POINTS = 10000
    SEMG_VALUE_SCALE = 1024.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('rehabTrainingInterface')
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self._cards = []
        self._current_idx = -1
        self._record_counter = 0
        self._current_record_id = None

        self._convert_callback = None
        self._send_motor_callback = None
        self._ai_analyzer = None

        self._exec_timer = QTimer(self)
        self._exec_timer.setSingleShot(False)
        self._exec_timer.timeout.connect(self._executeNext)
        self._interval_ms = 10000

        self._status_label = None
        self._progress_bar = None
        self._current_label = None
        self._user_name_input = None

        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        self.view.setObjectName('rehabTrainingView')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(20)

    def __initLayout(self):
        title = SubtitleLabel('预设动作训练')
        self.vBoxLayout.addWidget(title)

        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        top_row.addWidget(self.__createAngleCard(), 50)
        top_row.addWidget(self.__createUserCard(), 20)
        top_row.addWidget(self.__createStatusCard(), 30)

        self.vBoxLayout.addLayout(top_row)
        self.vBoxLayout.addWidget(self.__createSemgCard())
        self.vBoxLayout.addWidget(self.__createButtons())
        self.vBoxLayout.addStretch()

    def __createAngleCard(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel('动作设定'))

        self._cards_layout = QVBoxLayout()
        self._cards_layout.setSpacing(8)
        layout.addLayout(self._cards_layout)

        for motion_type, angle in DEFAULT_MOTIONS:
            self._addCard(motion_type, angle)

        self._add_btn = PrimaryPushButton('+ 添加动作')
        self._add_btn.clicked.connect(self._onAddCard)
        layout.addWidget(self._add_btn)
        return card

    def __createUserCard(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel('用户信息'))

        layout.addWidget(CaptionLabel('用户名称'))

        self._user_name_input = LineEdit()
        self._user_name_input.setPlaceholderText('请输入用户名称')
        layout.addWidget(self._user_name_input)

        tip_label = CaptionLabel('训练开始后将自动写入康复记录。')
        layout.addWidget(tip_label)
        layout.addStretch()
        return card

    def _addCard(self, motion_type=0, angle=0.2):
        card = AngleInputCard(motion_type, angle)
        card.setDeleteCallback(lambda current_card=card: self._onDeleteCard(current_card))
        self._cards.append(card)
        self._cards_layout.addWidget(card)

    def __createStatusCard(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(SubtitleLabel('执行状态'))

        self._current_label = BodyLabel('等待开始')
        self._current_label.setWordWrap(True)
        layout.addWidget(self._current_label)

        self._progress_bar = ProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(10)
        layout.addWidget(self._progress_bar)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self._exec_spinner = EllipsisSpinner(14)
        self._exec_spinner.hide()
        status_row.addWidget(self._exec_spinner)
        self._status_label = CaptionLabel('就绪')
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        layout.addStretch()
        return card

    def __createSemgCard(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(SubtitleLabel('sEMG 实时监控'))

        self._semg_plot = pg.PlotWidget()
        self._semg_plot.setBackground('w')
        self._semg_plot.showGrid(x=True, y=True, alpha=0.3)
        self._semg_plot.setLabel('left', 'Amplitude')
        self._semg_plot.setLabel('bottom', '样本')
        self._semg_plot.setYRange(-4096, 4096)
        self._semg_plot.setMinimumHeight(320)
        self._semg_plot.getPlotItem().hideButtons()

        pen_wave = pg.mkPen(color='#0078D4', width=1)
        self._semg_waveform_curve = self._semg_plot.plot(pen=pen_wave)
        pen_rectified = pg.mkPen(color='#0078D4', width=2)
        self._semg_rectified_curve = self._semg_plot.plot(pen=pen_rectified)
        pen_envelope = pg.mkPen(color='#E74C3C', width=3)
        self._semg_envelope_curve = self._semg_plot.plot(pen=pen_envelope)

        layout.addWidget(self._semg_plot)

        self._semg_value_label = BodyLabel('当前: ---')
        self._semg_value_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #0078D4;')
        layout.addWidget(self._semg_value_label)

        self._waveform_data = collections.deque(maxlen=self.MAX_CHART_POINTS)
        self._rectified_data = collections.deque(maxlen=self.MAX_CHART_POINTS)
        self._envelope_data = collections.deque(maxlen=self.MAX_CHART_POINTS)
        self._semg_point_count = 0
        self._semg_last_update = 0
        return card

    def append_sEMG_data(self, sample):
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

        import time
        now = time.time()
        if now - self._semg_last_update < 0.016:
            return
        self._semg_last_update = now

        count = len(self._waveform_data)
        if self._semg_point_count <= self.MAX_CHART_POINTS:
            start_index = 0
        else:
            start_index = self._semg_point_count - count

        x = np.arange(start_index, self._semg_point_count)
        self._semg_waveform_curve.setData(x=x, y=np.array(self._waveform_data, dtype=np.float64))
        self._semg_rectified_curve.setData(x=x, y=np.array(self._rectified_data, dtype=np.float64))
        self._semg_envelope_curve.setData(x=x, y=np.array(self._envelope_data, dtype=np.float64))

        if self._semg_point_count <= self.MAX_CHART_POINTS:
            self._semg_plot.setXRange(0, self.MAX_CHART_POINTS)
        else:
            self._semg_plot.setXRange(start_index, start_index + self.MAX_CHART_POINTS)

        value = self._envelope_data[-1] / self.SEMG_VALUE_SCALE if count > 0 else 0
        self._semg_value_label.setText(f'当前: sEMG: {value:.2f}')

    def __createButtons(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._start_btn = PrimaryPushButton('开始')
        self._start_btn.setFixedWidth(100)
        self._start_btn.clicked.connect(self._onStart)
        layout.addWidget(self._start_btn)

        self._stop_btn = PushButton('停止')
        self._stop_btn.setFixedWidth(100)
        self._stop_btn.clicked.connect(self._onStop)
        layout.addWidget(self._stop_btn)

        layout.addStretch()
        return widget

    def _onAddCard(self):
        self._addCard()

    def _onDeleteCard(self, card):
        if len(self._cards) <= 1:
            return
        self._cards_layout.removeWidget(card)
        self._cards.remove(card)
        card.deleteLater()

    def _onStart(self):
        if not self._cards:
            return

        motion_names = [card.getName() for card in self._cards]
        self._record_counter += 1
        self._current_record_id = f'record_{self._record_counter}'
        self._current_idx = 0
        self._start_btn.setEnabled(False)
        self._progress_bar.setValue(0)

        self.training_started.emit(
            {
                'record_id': self._current_record_id,
                'user_name': self.get_user_name(),
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'motions': motion_names,
            }
        )

        if self._ai_analyzer:
            self._ai_analyzer.clear_buffer()
            self._ai_analyzer.set_session_context('动作序列: ' + ', '.join(motion_names))

        self._executeCurrent()

    def _executeCurrent(self):
        if self._current_idx >= len(self._cards):
            self._onComplete()
            return

        total = len(self._cards)
        card = self._cards[self._current_idx]
        current_step = self._current_idx + 1
        progress = int(self._current_idx / total * 100)
        self._progress_bar.setValue(progress)
        self._current_label.setText(f'正在执行动作{current_step}')
        self._status_label.setText('执行中')
        self._exec_spinner.show()

        alpha, beta, gamma = card.getAngles()

        if self._convert_callback:
            motor_values = self._convert_callback(alpha, beta, gamma)
        else:
            motor_values = {'RB': 0.0, 'RF': 0.0, 'LB': 0.0, 'LF': 0.0}

        if self._send_motor_callback:
            self._send_motor_callback(
                motor_values.get('RB', 0.0),
                motor_values.get('RF', 0.0),
                motor_values.get('LB', 0.0),
                motor_values.get('LF', 0.0),
            )

        self._current_idx += 1
        self._exec_timer.start(self._interval_ms)

    def _executeNext(self):
        self._exec_timer.stop()
        self._executeCurrent()

    def _onComplete(self):
        self._exec_timer.stop()
        self._exec_spinner.hide()
        self._progress_bar.setValue(100)
        self._current_label.setText('完成')
        self._status_label.setText('完成')
        self._start_btn.setEnabled(True)
        self._current_idx = -1

        if self._ai_analyzer:
            self._ai_analyzer.trigger_analysis()

    def _onStop(self):
        self._exec_timer.stop()
        self._exec_spinner.hide()
        self._current_idx = -1
        self._progress_bar.setValue(0)
        self._current_label.setText('已停止')
        self._status_label.setText('就绪')
        self._start_btn.setEnabled(True)

    def setConvertCallback(self, callback):
        self._convert_callback = callback

    def setSendMotorCallback(self, callback):
        self._send_motor_callback = callback

    def set_ai_analyzer(self, analyzer):
        self._ai_analyzer = analyzer

    def get_user_name(self):
        name = self._user_name_input.text().strip() if self._user_name_input else ''
        return name or '未命名用户'
