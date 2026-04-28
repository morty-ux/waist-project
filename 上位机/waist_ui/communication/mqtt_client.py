# coding: utf-8
"""
MQTT client for EMQX Serverless.

The public surface intentionally mirrors TCPClient so MainWindow can switch
between TCP and MQTT with minimal UI changes.
"""

import json
import ssl
from pathlib import Path

from PySide6.QtCore import QObject, Signal

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover - handled at runtime for clear UI logs
    mqtt = None

from config.settings import Settings


class MQTTClient(QObject):
    connected = Signal()
    disconnected = Signal()
    rx_data_changed = Signal(object)
    raw_data_received = Signal(bytes)
    error_occurred = Signal(str)
    log_message = Signal(str, str)

    def __init__(self, config=None):
        super().__init__()
        self.config = config or Settings.get_mqtt_config()
        self._is_connected = False
        self._client = None
        self._topics = self._build_topics()

    def _build_topics(self):
        prefix = self.config['topic_prefix'].strip('/')
        device_id = self.config['device_id'].strip('/')
        base = f'{prefix}/{device_id}'
        return {
            'telemetry': f'{base}/telemetry',
            'status': f'{base}/status',
            'cmd': f'{base}/cmd',
            'ack': f'{base}/ack',
        }

    def connect_to_server(self):
        if mqtt is None:
            self._emit_error('paho-mqtt is not installed. Run: pip install paho-mqtt python-dotenv')
            return

        if self._is_connected:
            return

        try:
            protocol = mqtt.MQTTv311
            if str(self.config.get('mqtt_version', '')).lower() in ('5', '5.0', 'mqttv5'):
                protocol = mqtt.MQTTv5

            try:
                self._client = mqtt.Client(
                    mqtt.CallbackAPIVersion.VERSION1,
                    client_id=self.config['client_id'],
                    protocol=protocol,
                )
            except (AttributeError, TypeError):
                self._client = mqtt.Client(
                    client_id=self.config['client_id'],
                    protocol=protocol,
                )
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
            self._client.reconnect_delay_set(min_delay=1, max_delay=30)

            username = self.config.get('username')
            password = self.config.get('password')
            if username:
                self._client.username_pw_set(username, password)

            if self.config.get('tls_enable', True):
                ca_cert_path = Path(self.config.get('ca_cert_path', ''))
                if not ca_cert_path.exists():
                    self._emit_error(f'MQTT CA certificate not found: {ca_cert_path}')
                    return
                self._client.tls_set(
                    ca_certs=str(ca_cert_path),
                    certfile=None,
                    keyfile=None,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS_CLIENT,
                )
                self._client.tls_insecure_set(False)

            host = self.config['host']
            port = int(self.config['port'])
            self.log_message.emit('INFO', f'Connecting MQTT {host}:{port}...')
            self._client.connect_async(host, port, keepalive=60)
            self._client.loop_start()
        except Exception as exc:
            self._emit_error(f'MQTT connect failed: {exc}')

    def disconnect(self):
        try:
            if self._client:
                self._client.loop_stop()
                self._client.disconnect()
        finally:
            if self._is_connected:
                self._is_connected = False
                self.disconnected.emit()
            self.log_message.emit('INFO', 'MQTT disconnected')

    def send_data(self, data):
        if not self._is_connected or not self._client:
            self.log_message.emit('WARNING', 'MQTT is not connected')
            return False

        if isinstance(data, str):
            payload = data.encode('utf-8')
        elif isinstance(data, bytes):
            payload = data
        else:
            payload = json.dumps(data, ensure_ascii=False).encode('utf-8')

        result = self._client.publish(self._topics['cmd'], payload, qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            self._emit_error(f'MQTT publish failed, rc={result.rc}')
            return False

        self.log_message.emit('DEBUG', f'[MQTT TX] {self._topics["cmd"]}: {payload!r}')
        return True

    def send_text(self, text: str):
        payload = {
            'cmd': 'text',
            'value': text,
            'device_id': self.config['device_id'],
        }
        return self.send_data(payload)

    def send_motor_cmd(self, rb: float, rf: float, lb: float, lf: float):
        payload = {
            'cmd': 'set_force',
            'device_id': self.config['device_id'],
            'RB': float(rb),
            'RF': float(rf),
            'LB': float(lb),
            'LF': float(lf),
        }
        return self.send_data(payload)

    def set_server(self, host: str, port: int):
        """Compatibility with TCPClient; useful when the old connect UI is reused."""
        self.config['host'] = host
        self.config['port'] = int(port)

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._is_connected = True
            self.connected.emit()
            self.log_message.emit('INFO', 'MQTT connected')

            for name, topic in self._topics.items():
                client.subscribe(topic, qos=1)
                self.log_message.emit('INFO', f'Subscribed {name}: {topic}')
        else:
            self._emit_error(f'MQTT connect refused, rc={rc}')

    def _on_disconnect(self, client, userdata, rc, properties=None):
        was_connected = self._is_connected
        self._is_connected = False
        if was_connected:
            self.disconnected.emit()
        level = 'WARNING' if rc else 'INFO'
        self.log_message.emit(level, f'MQTT disconnected, rc={rc}')

    def _on_message(self, client, userdata, msg):
        payload = msg.payload or b''
        self.raw_data_received.emit(payload)
        self.log_message.emit('DEBUG', f'[MQTT RX] {msg.topic}: {payload.decode("utf-8", errors="replace")}')

        if msg.topic == self._topics['telemetry']:
            telemetry = self._parse_telemetry(payload)
            if telemetry is not None:
                self.rx_data_changed.emit(telemetry)
            return

        text = payload.decode('utf-8', errors='replace')
        self.rx_data_changed.emit(text)

    def _parse_telemetry(self, payload):
        try:
            data = json.loads(payload.decode('utf-8'))
        except Exception as exc:
            self.log_message.emit('WARNING', f'Invalid telemetry JSON: {exc}')
            return None

        required = ('LF', 'RF', 'LB', 'RB')
        missing = [key for key in required if key not in data]
        if missing:
            self.log_message.emit('WARNING', f'Telemetry missing fields: {", ".join(missing)}')
            return None

        try:
            return {key: float(data[key]) for key in required}
        except (TypeError, ValueError) as exc:
            self.log_message.emit('WARNING', f'Invalid telemetry value: {exc}')
            return None

    def _emit_error(self, message):
        self.log_message.emit('ERROR', message)
        self.error_occurred.emit(message)

    @property
    def is_connected(self):
        return self._is_connected

    @property
    def server_ip(self):
        return self.config['host']

    @property
    def server_port(self):
        return self.config['port']

    @property
    def tcp_server_ip(self):
        return self.server_ip

    @property
    def tcp_server_port(self):
        return self.server_port
