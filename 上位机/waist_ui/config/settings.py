# coding: utf-8
"""
配置管理模块
管理ESP8266连接参数等配置
"""


class Settings:
    """配置类"""

    # ESP8266连接配置
    ESP_HOST = '192.168.1.100'
    ESP_PORT = 8080

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
