# coding: utf-8
"""
传感器数据类
封装传感器数据结构
"""


class SensorData:
    """传感器数据"""

    def __init__(self):
        self.lf = 0.0  # 左肩
        self.lb = 0.0  # 左膝
        self.rf = 0.0  # 右肩
        self.rb = 0.0  # 右膝
        self.timestamp = 0

    def update(self, channel, value):
        """更新指定通道的数据"""
        channel = channel.lower()
        if channel == 'lf':
            self.lf = value
        elif channel == 'lb':
            self.lb = value
        elif channel == 'rf':
            self.rf = value
        elif channel == 'rb':
            self.rb = value

    def get_value(self, channel):
        """获取指定通道的值"""
        channel = channel.lower()
        if channel == 'lf':
            return self.lf
        elif channel == 'lb':
            return self.lb
        elif channel == 'rf':
            return self.rf
        elif channel == 'rb':
            return self.rb
        return 0.0

    def reset(self):
        """重置所有数据"""
        self.lf = 0.0
        self.lb = 0.0
        self.rf = 0.0
        self.rb = 0.0

    def to_dict(self):
        """转换为字典"""
        return {
            'lf': self.lf,
            'lb': self.lb,
            'rf': self.rf,
            'rb': self.rb,
            'timestamp': self.timestamp
        }
