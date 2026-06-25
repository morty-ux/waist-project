# coding: utf-8

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QDoubleValidator, QColor, QPainter, QBrush, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, BodyLabel, CaptionLabel,
    CardWidget, SimpleCardWidget,
    LineEdit, ProgressBar, ComboBox,
    PrimaryPushButton, PushButton, InfoBadge, InfoBadgePosition,
)

MOTION_TYPES = [
    '\u524d\u5411\u5f2f\u8170',
    '\u4fa7\u5411\u5f2f\u8170',
    '\u8f6c\u8eab',
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
        w = size + (len(_ELLIPSIS_COLORS) - 1) * 8
        self.setFixedSize(w, size)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(60)
        self._timer.start()

    def _tick(self):
        self._phase += 1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx = w / 2.0
        cy = h / 2.0
        n = len(_ELLIPSIS_COLORS)
        spacing = 8
        total_w = (n - 1) * spacing
        start_x = cx - total_w / 2.0
        period = 18

        for i in range(n):
            offset = (self._phase - i * (period // n)) % period
            t = offset / float(period)
            if t < 0.5:
                scale = t * 2.0
            else:
                scale = (1.0 - t) * 2.0
            r = 2.0 + scale * 5.0
            x = start_x + i * spacing

            color = QColor(_ELLIPSIS_COLORS[i])
            alpha = int(80 + scale * 175)
            color.setAlpha(alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(x, cy), r, r)

        p.end()

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()


class ThinkingWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._onAnimTick)
        self._anim_timer.setInterval(80)
        self.__initUI()

    def __initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._spinner = EllipsisSpinner(20)
        layout.addWidget(self._spinner)

        self._text = BodyLabel('Thinking')
        layout.addWidget(self._text)

        layout.addStretch()

    def _onAnimTick(self):
        self._tick += 1
        word = 'Thinking'
        n = len(word)
        pos = self._tick % (n + 3)
        if pos < n:
            self._text.setText(word[:pos + 1] + '|')
        else:
            self._text.setText(word)

    def start(self):
        self._spinner.start()
        self._anim_timer.start()
        self._tick = 0
        self._text.setText('Thinking')

    def stop(self):
        self._spinner.stop()
        self._anim_timer.stop()


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

        angle_label = CaptionLabel('\u89d2\u5ea6:')
        layout.addWidget(angle_label)

        self._angle_input = LineEdit()
        self._angle_input.setFixedWidth(80)
        self._angle_input.setValidator(validator)
        self._angle_input.setText(str(angle))
        layout.addWidget(self._angle_input)

        layout.addStretch()

        self._delete_btn = PushButton('\u5220\u9664')
        self._delete_btn.setFixedWidth(70)
        layout.addWidget(self._delete_btn)

    def getName(self):
        return MOTION_TYPES[self._motion_combo.currentIndex()]

    def getAngles(self):
        try:
            val = float(self._angle_input.text())
        except ValueError:
            val = 0.0

        motion_idx = self._motion_combo.currentIndex()
        if motion_idx == 0:
            return (0.0, 0.0, -val)
        elif motion_idx == 1:
            return (0.0, -val, 0.0)
        else:
            return (val, 0.0, 0.0)

    def setDeleteCallback(self, callback):
        self._delete_btn.clicked.connect(lambda checked=False, cb=callback: cb())


class PresetMotionInterface(ScrollArea):

    MAX_CHART_POINTS = 10000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('rehabTrainingInterface')
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self._cards = []
        self._current_idx = -1

        self._convert_callback = None
        self._send_motor_callback = None

        self._exec_timer = QTimer(self)
        self._exec_timer.setSingleShot(False)
        self._exec_timer.timeout.connect(self._executeNext)
        self._interval_ms = 2000

        self._status_label = None
        self._progress_bar = None
        self._current_label = None

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
        title = SubtitleLabel('\u9884\u8bbe\u52a8\u4f5c\u8bad\u7ec3')
        self.vBoxLayout.addWidget(title)

        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        angle_card = self.__createAngleCard()
        top_row.addWidget(angle_card, 60)

        status_card = self.__createStatusCard()
        top_row.addWidget(status_card, 40)

        self.vBoxLayout.addLayout(top_row)

        semg_card = self.__createSemgCard()
        self.vBoxLayout.addWidget(semg_card)

        ai_card = self.__createThinkingCard()
        self.vBoxLayout.addWidget(ai_card)

        btn_widget = self.__createButtons()
        self.vBoxLayout.addWidget(btn_widget)

        self.vBoxLayout.addStretch()

    def __createAngleCard(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header = SubtitleLabel('动作设定')
        layout.addWidget(header)

        self._cards_layout = QVBoxLayout()
        self._cards_layout.setSpacing(8)
        layout.addLayout(self._cards_layout)

        for mt, ang in DEFAULT_MOTIONS:
            self._addCard(mt, ang)

        self._add_btn = PrimaryPushButton('+ \u6dfb\u52a0\u52a8\u4f5c')
        self._add_btn.clicked.connect(self._onAddCard)
        layout.addWidget(self._add_btn)

        return card

    def _addCard(self, motion_type=0, angle=0.2):
        card = AngleInputCard(motion_type, angle)
        card.setDeleteCallback(lambda c=card: self._onDeleteCard(c))
        self._cards.append(card)
        self._cards_layout.addWidget(card)

    def __createStatusCard(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = SubtitleLabel('\u6267\u884c\u72b6\u6001')
        layout.addWidget(header)

        self._current_label = BodyLabel('\u7b49\u5f85\u5f00\u59cb')
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
        self._status_label = CaptionLabel('\u5c31\u7eea')
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        layout.addStretch()
        return card

    def __createSemgCard(self):
        """sEMG 实时监控卡片 - 全屏宽度"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header = SubtitleLabel('sEMG 实时监控')
        layout.addWidget(header)

        # 创建折线图
        self._semg_series = QLineSeries()
        self._semg_series.setName('sEMG')
        pen = QPen(QColor('#0078D4'))
        pen.setWidth(2)
        self._semg_series.setPen(pen)

        self._semg_chart = QChart()
        self._semg_chart.addSeries(self._semg_series)
        self._semg_chart.setTitle('')
        self._semg_chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        self._semg_chart.legend().hide()
        self._semg_chart.setBackgroundRoundness(8)

        # X轴（样本序号）
        self._semg_axisX = QValueAxis()
        self._semg_axisX.setRange(0, self.MAX_CHART_POINTS)
        self._semg_axisX.setLabelFormat('%d')
        self._semg_axisX.setTitleText('\u6837\u672c')
        self._semg_chart.addAxis(self._semg_axisX, Qt.AlignBottom)
        self._semg_series.attachAxis(self._semg_axisX)

        # Y轴（ADC值 0-4096）
        self._semg_axisY = QValueAxis()
        self._semg_axisY.setRange(-256, 256)
        self._semg_axisY.setLabelFormat('%d')
        self._semg_axisY.setTitleText('Filtered')
        self._semg_chart.addAxis(self._semg_axisY, Qt.AlignLeft)
        self._semg_series.attachAxis(self._semg_axisY)

        self._semg_chart_view = QChartView(self._semg_chart)
        self._semg_chart_view.setRenderHint(self._semg_chart_view.renderHints())
        self._semg_chart_view.setMinimumHeight(320)

        layout.addWidget(self._semg_chart_view)

        self._semg_value_label = BodyLabel('\u5f53\u524d: ---')
        self._semg_value_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #0078D4;')
        layout.addWidget(self._semg_value_label)

        self._semg_point_count = 0
        self._semg_last_update = 0
        self._semg_peak_abs = 256

        return card

    def append_sEMG_data(self, value: int):
        """添加sEMG数据点并更新折线图（定时器降频~20Hz防卡死）"""
        self._semg_point_count += 1
        self._semg_series.append(self._semg_point_count, value)

        # 定时器降频：至少间隔50ms才刷新一次图表UI，避免Qt Charts重绘卡死
        import time
        now = time.time()
        if now - self._semg_last_update < 0.016:  # ~60fps
            return
        self._semg_last_update = now

        # 超过上限1.5倍时，批量裁剪到 MAX_CHART_POINTS 个点
        limit = self.MAX_CHART_POINTS * 1.5
        if self._semg_point_count > limit:
            keep_count = int(self.MAX_CHART_POINTS)
            remove_count = self._semg_series.count() - keep_count
            if remove_count > 0:
                self._semg_series.removePoints(0, remove_count)
            self._semg_axisX.setRange(
                self._semg_point_count - keep_count,
                self._semg_point_count
            )
        elif self._semg_point_count <= self.MAX_CHART_POINTS:
            self._semg_axisX.setRange(0, self.MAX_CHART_POINTS)
        else:
            self._semg_axisX.setRange(
                self._semg_point_count - self.MAX_CHART_POINTS,
                self._semg_point_count
            )

        peak_abs = max(32, abs(value))
        if peak_abs > self._semg_peak_abs:
            self._semg_peak_abs = peak_abs
        axis_limit = int(self._semg_peak_abs * 1.2)
        self._semg_axisY.setRange(-axis_limit, axis_limit)
        self._semg_value_label.setText(f'当前: {value}')

    def __createThinkingCard(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        self._think_widget = ThinkingWidget()
        header_row.addWidget(self._think_widget)

        header_row.addStretch()

        self._ai_trigger_btn = PrimaryPushButton('\u89e6\u53d1AI\u5206\u6790')
        self._ai_trigger_btn.setFixedWidth(120)
        self._ai_trigger_btn.clicked.connect(self._onAiTrigger)
        header_row.addWidget(self._ai_trigger_btn)

        layout.addLayout(header_row)

        # AI结果文本显示区域（只读，支持滚动）
        self._ai_result_edit = QTextEdit()
        self._ai_result_edit.setReadOnly(True)
        self._ai_result_edit.setMaximumHeight(180)
        self._ai_result_edit.setPlaceholderText('\u70b9\u51fb\u201c\u89e6\u53d1AI\u5206\u6790\u201d\u5f00\u59cb\u5206\u6790sEMG\u6570\u636e...')
        self._ai_result_edit.setStyleSheet(
            'QTextEdit { border: 1px solid #E0E0E0; border-radius: 6px; '
            'padding: 8px; font-size: 13px; color: #323130; background: #FAFAFA; }'
        )
        layout.addWidget(self._ai_result_edit)

        return card

    def _onAiTrigger(self):
        """点击触发AI分析按钮"""
        if hasattr(self, '_ai_analyzer') and self._ai_analyzer:
            self._ai_analyzer.trigger_analysis()
        else:
            self._ai_result_edit.setPlainText(
                '[错误] AI分析模块未连接，请检查配置。'
            )

    def set_ai_analyzer(self, analyzer):
        """连接AiAnalyzer实例"""
        self._ai_analyzer = analyzer

    def on_ai_thinking(self, thinking: bool):
        """AI思考状态变化"""
        if thinking:
            self._think_widget.start()
            self._ai_trigger_btn.setEnabled(False)
            self._ai_result_edit.setPlainText('AI\u5206\u6790\u4e2d\uff0c\u8bf7\u7a0d\u5019...')
        else:
            self._think_widget.stop()
            self._ai_trigger_btn.setEnabled(True)

    def on_ai_result(self, text: str):
        """AI分析结果就绪"""
        self._ai_result_edit.setPlainText(text)

    def on_ai_error(self, error: str):
        """AI分析出错"""
        self._ai_result_edit.setPlainText(f'[错误] {error}')

    def __createButtons(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._start_btn = PrimaryPushButton('\u5f00\u59cb')
        self._start_btn.setFixedWidth(100)
        self._start_btn.clicked.connect(self._onStart)
        layout.addWidget(self._start_btn)

        self._stop_btn = PushButton('\u505c\u6b62')
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
        if len(self._cards) == 0:
            return

        self._current_idx = 0
        self._start_btn.setEnabled(False)
        self._progress_bar.setValue(0)
        self._think_widget.stop()

        # 清空AI分析器的缓存，开始全新采集
        if hasattr(self, '_ai_analyzer') and self._ai_analyzer:
            self._ai_analyzer.clear_buffer()
            # 构建动作序列上下文
            motion_names = [card.getName() for card in self._cards]
            context = "动作序列: " + ", ".join(motion_names)
            self._ai_analyzer.set_session_context(context)

        self._executeCurrent()

    def _executeCurrent(self):
        if self._current_idx >= len(self._cards):
            self._onComplete()
            return

        total = len(self._cards)
        card = self._cards[self._current_idx]
        name = card.getName()
        progress = int(self._current_idx / total * 100)
        self._progress_bar.setValue(progress)
        self._current_label.setText(
            f'{name} ({self._current_idx + 1}/{total})'
        )
        self._status_label.setText('\u6267\u884c\u4e2d')
        self._exec_spinner.show()

        alpha, beta, gamma = card.getAngles()

        if self._convert_callback:
            motor_values = self._convert_callback(alpha, beta, gamma)
        else:
            motor_values = {'LF': 0.0, 'LB': 0.0, 'RB': 0.0, 'RF': 0.0}

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
        self._current_label.setText('\u5df2\u5b8c\u6210')
        self._status_label.setText('\u2714 \u5df2\u5b8c\u6210')
        self._start_btn.setEnabled(True)
        self._current_idx = -1

        # 动作执行完成，自动触发AI分析
        if hasattr(self, '_ai_analyzer') and self._ai_analyzer:
            self._onAiTrigger()

    def _onStop(self):
        self._exec_timer.stop()
        self._exec_spinner.hide()
        self._current_idx = -1
        self._progress_bar.setValue(0)
        self._current_label.setText('\u5df2\u505c\u6b62')
        self._status_label.setText('\u5c31\u7eea')
        self._start_btn.setEnabled(True)
        self._think_widget.stop()

    def setConvertCallback(self, callback):
        self._convert_callback = callback

    def setSendMotorCallback(self, callback):
        self._send_motor_callback = callback
