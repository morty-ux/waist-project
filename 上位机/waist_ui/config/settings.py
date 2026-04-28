# coding: utf-8
"""
配置管理模块
管理ESP8266连接参数、MQTT连接参数等配置
"""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Load .env when python-dotenv is installed; otherwise keep env-only mode."""
    env_path = BASE_DIR / '.env'
    try:
        from dotenv import load_dotenv
    except ImportError:
        if env_path.exists():
            print('[CONFIG] python-dotenv is not installed; .env was not loaded.')
        return

    load_dotenv(env_path)


def _env(name, default=None):
    value = os.getenv(name)
    if value is None or value == '':
        return default
    return value


def _env_int(name, default):
    try:
        return int(_env(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name, default=False):
    value = str(_env(name, str(default))).strip().lower()
    return value in ('1', 'true', 'yes', 'on')


_load_dotenv()


class Settings:
    """配置类"""

    # ESP8266连接配置
    ESP_HOST = '192.168.1.100'
    ESP_PORT = 8080

    # Communication mode: tcp or mqtt
    COMM_MODE = _env('COMM_MODE', 'tcp').strip().lower()

    # MQTT / EMQX configuration
    MQTT_BROKER_HOST = _env('MQTT_BROKER_HOST', 'm4673563.ala.cn-hangzhou.emqxsl.cn')
    MQTT_BROKER_PORT = _env_int('MQTT_BROKER_PORT', 8883)
    MQTT_USERNAME = _env('MQTT_USERNAME', '')
    MQTT_PASSWORD = _env('MQTT_PASSWORD', '')
    MQTT_CLIENT_ID = _env('MQTT_CLIENT_ID', 'waist-ui-device001')
    MQTT_DEVICE_ID = _env('MQTT_DEVICE_ID', 'device001')
    MQTT_TOPIC_PREFIX = _env('MQTT_TOPIC_PREFIX', 'waist')
    MQTT_TLS_ENABLE = _env_bool('MQTT_TLS_ENABLE', True)
    MQTT_CA_CERT_PATH = _env('MQTT_CA_CERT_PATH', 'certs/emqxsl-ca.crt')
    MQTT_VERSION = _env('MQTT_VERSION', '3.1.1')

    # 应用配置
    APP_NAME = '康复医疗仪表盘'
    WINDOW_WIDTH = 1100
    WINDOW_HEIGHT = 700
    MIN_WIDTH = 1000
    MIN_HEIGHT = 640

    # 传感器通道
    CHANNELS = ['LF', 'LB', 'RF', 'RB']
    CHANNEL_NAMES = {
        'LF': '左肩',
        'LB': '左膝',
        'RF': '右肩',
        'RB': '右膝'
    }

    # 力控参数范围
    FORCE_MIN = 0
    FORCE_MAX = 100
    FORCE_DEFAULT = 0

    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'

    @staticmethod
    def set_esp_config(host, port):
        """设置ESP8266配置"""
        Settings.ESP_HOST = host
        Settings.ESP_PORT = port

    @staticmethod
    def get_esp_config():
        """获取ESP8266配置"""
        return Settings.ESP_HOST, Settings.ESP_PORT

    @staticmethod
    def get_comm_mode():
        """获取通信模式: tcp or mqtt"""
        return Settings.COMM_MODE if Settings.COMM_MODE in ('tcp', 'mqtt') else 'tcp'

    @staticmethod
    def get_mqtt_config():
        """获取MQTT配置"""
        ca_path = Path(Settings.MQTT_CA_CERT_PATH)
        if not ca_path.is_absolute():
            ca_path = BASE_DIR / ca_path

        return {
            'host': Settings.MQTT_BROKER_HOST,
            'port': Settings.MQTT_BROKER_PORT,
            'username': Settings.MQTT_USERNAME,
            'password': Settings.MQTT_PASSWORD,
            'client_id': Settings.MQTT_CLIENT_ID,
            'device_id': Settings.MQTT_DEVICE_ID,
            'topic_prefix': Settings.MQTT_TOPIC_PREFIX,
            'tls_enable': Settings.MQTT_TLS_ENABLE,
            'ca_cert_path': str(ca_path),
            'mqtt_version': Settings.MQTT_VERSION,
        }
