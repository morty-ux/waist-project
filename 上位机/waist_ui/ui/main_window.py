# coding: utf-8
"""
主窗口，包含数据监测、康复训练、AI分析、康复记录、通信日志和用户自定义界面。
"""

from pathlib import Path

try:
    from app_bootstrap import ensure_qapplication
except ImportError:  # pragma: no cover
    from ..app_bootstrap import ensure_qapplication

ensure_qapplication()

from PySide6.QtCore import Qt
from qfluentwidgets import (
    FluentIcon,
    FluentWindow,
    InfoBar,
    InfoBarPosition,
)

from config.settings import Settings


class MainWindow(FluentWindow):
    """主窗口。"""

    def __init__(self):
        super().__init__()
        self.comm_client = None
        self.tcp_client = None
        self.ai_analyzer = None
        self._active_record_id = None
        self.__initWindow()
        self.__initNavigation()
        self.__initCommunication()

    def __initWindow(self):
        self.resize(1400, 900)
        self.setMinimumSize(1300, 800)
        self.setWindowTitle('康复医疗仪表盘')

    def __initNavigation(self):
        from ui.ai_analysis import AiAnalysisInterface
        from ui.data_monitor import DataMonitorInterface
        from ui.log_interface import LogInterface
        from ui.rehab_record import RehabRecordInterface
        from ui.rehab_training import PresetMotionInterface

        self.dataMonitorInterface = DataMonitorInterface(self)
        self.rehabTrainingInterface = PresetMotionInterface(self)
        self.aiAnalysisInterface = AiAnalysisInterface(self)
        self.rehabRecordInterface = RehabRecordInterface(self)
        self.logInterface = LogInterface(self)

        self.addSubInterface(self.dataMonitorInterface, FluentIcon.SPEED_HIGH, '数据监测')
        self.addSubInterface(self.rehabTrainingInterface, FluentIcon.HEART, '康复训练')
        self.addSubInterface(self.aiAnalysisInterface, FluentIcon.ROBOT, 'AI分析')
        self.addSubInterface(self.rehabRecordInterface, FluentIcon.DOCUMENT, '康复记录')
        self.addSubInterface(self.logInterface, FluentIcon.CHAT, '通信日志')

    def __initCommunication(self):
        from backend.kinematics import Kinematics, angles_to_motor_commands
        from communication import MQTTClient, TCPClient

        self.comm_mode = Settings.get_comm_mode()
        if self.comm_mode == 'mqtt':
            self.comm_client = MQTTClient(Settings.get_mqtt_config())
        else:
            self.comm_client = TCPClient(ip='192.168.4.1', port=8080)

        self.tcp_client = self.comm_client

        self.comm_client.connected.connect(self.__onConnected)
        self.comm_client.disconnected.connect(self.__onDisconnected)
        self.comm_client.raw_data_received.connect(self.__onRawDataReceived)
        self.comm_client.rx_data_changed.connect(self.__onRxDataChanged)
        self.comm_client.error_occurred.connect(self.__onError)
        self.comm_client.log_message.connect(self.__onLogMessage)

        if hasattr(self.comm_client, 'semg_data_received'):
            if hasattr(self.comm_client, 'semg_display_signal'):
                self.comm_client.semg_display_signal.connect(self.dataMonitorInterface.append_sEMG_data)
                self.comm_client.semg_display_signal.connect(self.rehabTrainingInterface.append_sEMG_data)
            else:
                self.comm_client.semg_data_received.connect(self.dataMonitorInterface.append_sEMG_data)
                self.comm_client.semg_data_received.connect(self.rehabTrainingInterface.append_sEMG_data)

        self.dataMonitorInterface.setForceChangedCallback(self.__onForceChanged)
        self.dataMonitorInterface.setResetCallback(self.__onReset)

        self.logInterface.setConnectCallback(self.__onConnectClicked)
        self.logInterface.setSendCommandCallback(self.__onSendCommand)

        self.kinematics = Kinematics()
        self.rehabTrainingInterface.setConvertCallback(
            lambda a, b, g: angles_to_motor_commands(a, b, g, self.kinematics)
        )
        self.rehabTrainingInterface.setSendMotorCallback(
            lambda rb, rf, lb, lf: self.comm_client.send_motor_cmd(rb, rf, lb, lf)
        )
        self.rehabTrainingInterface.training_started.connect(self.__onTrainingStarted)

        self.__initAiAnalyzer()

        self.logInterface.addLog('INFO', f'Communication mode: {self.comm_mode.upper()}')
        if self.comm_mode == 'mqtt':
            self.logInterface.addLog(
                'INFO',
                'MQTT 模式使用 .env 中的 EMQX 配置，连接页的 IP/端口不会覆盖 MQTT 配置。',
            )
        self.logInterface.addLog('INFO', '请在通信日志界面输入 IP 地址和端口，点击连接。')

    def __initAiAnalyzer(self):
        from backend.ai_analyzer import AiAnalyzer

        ai_config = Settings.get_ai_config()
        self.ai_analyzer = AiAnalyzer(
            buffer_size=ai_config['buffer_size'],
            ollama_url=ai_config['ollama_url'],
            model=ai_config['model'],
            parent=self,
        )

        prompt_path = Path(__file__).resolve().parent.parent / 'config' / 'semg_analysis_prompt.md'
        if prompt_path.exists():
            prompt_text = prompt_path.read_text(encoding='utf-8')
            self.ai_analyzer.set_prompt(prompt_text)
            self.logInterface.addLog('INFO', f'已加载 AI 提示词模板: {prompt_path.name}')
        else:
            self.logInterface.addLog('WARNING', f'提示词模板文件未找到: {prompt_path}')

        if hasattr(self.comm_client, 'semg_activation_received'):
            self.comm_client.semg_activation_received.connect(self.ai_analyzer.add_semg_data)
        elif hasattr(self.comm_client, 'semg_data_received'):
            self.comm_client.semg_data_received.connect(self.ai_analyzer.add_semg_data)

        self.ai_analyzer.thinking_changed.connect(self.__onAiThinkingChanged)
        self.ai_analyzer.result_ready.connect(self.__onAiResultReady)
        self.ai_analyzer.error_occurred.connect(self.__onAiErrorOccurred)

        self.rehabTrainingInterface.set_ai_analyzer(self.ai_analyzer)
        self.aiAnalysisInterface.set_ai_analyzer(self.ai_analyzer)

        self.logInterface.addLog(
            'INFO',
            f'AI 分析模块已初始化: 模型={ai_config["model"]}, Ollama={ai_config["ollama_url"]}',
        )

    def __onTrainingStarted(self, info):
        self._active_record_id = info['record_id']
        self.rehabRecordInterface.add_record(info)

    def __onAiThinkingChanged(self, thinking):
        self.aiAnalysisInterface.on_ai_thinking(thinking)

    def __onAiResultReady(self, text):
        self.aiAnalysisInterface.on_ai_result(text)
        if self._active_record_id:
            self.rehabRecordInterface.set_record_report(self._active_record_id, text)
            self._active_record_id = None

    def __onAiErrorOccurred(self, error):
        self.aiAnalysisInterface.on_ai_error(error)
        if self._active_record_id:
            self.rehabRecordInterface.set_record_report(self._active_record_id, f'[错误] {error}')
            self._active_record_id = None

    def __onConnectClicked(self, ip, port):
        if self.comm_mode == 'tcp' and hasattr(self.comm_client, 'set_server'):
            self.comm_client.set_server(ip, port)
        self.comm_client.connect_to_server()

    def __onConnected(self):
        self.dataMonitorInterface.setConnectionStatus(
            True,
            f'{self.comm_client.server_ip}:{self.comm_client.server_port}',
        )
        self.logInterface.setConnectionState(True)
        self.logInterface.addLog(
            'INFO',
            f'已连接到 {self.comm_client.server_ip}:{self.comm_client.server_port}',
        )

        if hasattr(self.comm_client, 'get_local_ip'):
            local_ip = self.comm_client.get_local_ip()
            self.logInterface.addLog('INFO', f'本地 IP: {local_ip}')

        InfoBar.success(
            title='连接成功',
            content=f'已连接到 {self.comm_client.server_ip}',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

    def __onDisconnected(self):
        self.dataMonitorInterface.setConnectionStatus(False)
        self.logInterface.setConnectionState(False)
        self.logInterface.addLog('WARNING', '连接已断开')

    def __onRawDataReceived(self, data):
        hex_str = ' '.join(f'{value:02X}' for value in data)
        self.logInterface.addLog('DEBUG', f'[RX] {hex_str}')

    def __onRxDataChanged(self, data):
        if isinstance(data, dict):
            self.dataMonitorInterface.updateSensorData(data)
        self.logInterface.addLog('DEBUG', f'[RX] {data}')

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
            parent=self,
        )

    def __onForceChanged(self, rb, rf, lb, lf):
        self.logInterface.addLog('DEBUG', f'发送电机: LF={rb}, LB={rf}, RF={lb}, RB={lf}')
        self.comm_client.send_motor_cmd(rb, rf, lb, lf)

    def __onReset(self):
        self.dataMonitorInterface.reset_values()
        self.logInterface.addLog('INFO', '系统已复位')
        self.comm_client.send_motor_cmd(0, 0, 0, 0)

    def __onSendCommand(self, command):
        self.logInterface.addLog('INFO', f'发送命令: {command}')
        self.comm_client.send_text(command)
