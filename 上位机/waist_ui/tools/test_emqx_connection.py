# coding: utf-8
"""
Standalone EMQX Serverless smoke test.

Run from 上位机/waist_ui:
    python tools/test_emqx_connection.py
"""

import json
import signal
import ssl
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print('paho-mqtt is not installed. Run: pip install paho-mqtt python-dotenv')
    raise SystemExit(1)

from config.settings import Settings


running = True

CONNACK_MESSAGES = {
    0: 'Connection accepted',
    1: 'Unsupported protocol version',
    2: 'Invalid client identifier',
    3: 'Server unavailable',
    4: 'Bad username or password',
    5: 'Not authorized',
}


def stop_handler(signum, frame):
    global running
    running = False


def create_client(config):
    protocol = mqtt.MQTTv311
    if str(config.get('mqtt_version', '')).lower() in ('5', '5.0', 'mqttv5'):
        protocol = mqtt.MQTTv5

    try:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id=config['client_id'] + '-test',
            protocol=protocol,
        )
    except (AttributeError, TypeError):
        client = mqtt.Client(
            client_id=config['client_id'] + '-test',
            protocol=protocol,
        )

    if config.get('username'):
        client.username_pw_set(config['username'], config.get('password'))

    if config.get('tls_enable', True):
        ca_cert = Path(config['ca_cert_path'])
        if not ca_cert.exists():
            raise FileNotFoundError(f'CA certificate not found: {ca_cert}')
        client.tls_set(
            ca_certs=str(ca_cert),
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        client.tls_insecure_set(False)

    return client


def main():
    signal.signal(signal.SIGINT, stop_handler)
    config = Settings.get_mqtt_config()
    if not config.get('username') or not config.get('password'):
        print('MQTT username/password is empty. Copy .env.example to .env and fill MQTT_USERNAME/MQTT_PASSWORD.')
        return 1

    prefix = config['topic_prefix'].strip('/')
    device_id = config['device_id'].strip('/')
    base = f'{prefix}/{device_id}'
    topics = [
        f'{base}/telemetry',
        f'{base}/status',
        f'{base}/ack',
        f'{base}/cmd',
    ]

    client = create_client(config)
    connected = threading.Event()

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print('MQTT connected')
            for topic in topics:
                client.subscribe(topic, qos=1)
                print(f'subscribed {topic}')
            connected.set()
        else:
            print(f'MQTT connect failed, rc={rc} ({CONNACK_MESSAGES.get(rc, "Unknown error")})')
            connected.clear()

    def on_disconnect(client, userdata, rc, properties=None):
        connected.clear()
        print(f'MQTT disconnected, rc={rc}')

    def on_message(client, userdata, msg):
        payload = msg.payload.decode('utf-8', errors='replace')
        print(f'RX {msg.topic}: {payload}')

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        print(f'Connecting {config["host"]}:{config["port"]} ...')
        client.connect(config['host'], int(config['port']), keepalive=60)
        client.loop_start()

        if not connected.wait(timeout=10):
            print('MQTT did not connect within 10 seconds; telemetry will not be published.')
            return 1

        telemetry_topic = f'{base}/telemetry'
        payload = {
            'device_id': device_id,
            'LF': 12.3,
            'RF': 11.8,
            'LB': 13.1,
            'RB': 12.9,
        }
        while running:
            if connected.is_set():
                result = client.publish(telemetry_topic, json.dumps(payload), qos=1)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    print(f'TX {telemetry_topic}: {payload}')
                else:
                    print(f'Publish failed, rc={result.rc}')
            time.sleep(2)
    except Exception as exc:
        print(f'MQTT test failed: {exc}')
        return 1
    finally:
        client.loop_stop()
        client.disconnect()
        print('Stopped')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
