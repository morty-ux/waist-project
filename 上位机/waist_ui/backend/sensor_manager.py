# coding: utf-8
"""
后端模块
处理传感器数据和管理
"""

from PySide6.QtCore import QObject, Signal


class SensorManager(QObject):
    """
    传感器数据管理器

    功能：
    - 管理4个通道的压力传感器数据
    - 提供数据更新信号
    - 数据预留扩展
    """

    data_updated = Signal(dict)  # 数据更新信号

    def __init__(self):
        super().__init__()
        self._sensor_data = {
            'LF': 0.0,  # 左前
            'LB': 0.0,  # 左后
            'RF': 0.0,  # 右前
            'RB': 0.0   # 右后
        }

        self._motor_positions = {
            'LF': 0.0,
            'LB': 0.0,
            'RF': 0.0,
            'RB': 0.0
        }

    def update_pressure_data(self, data: dict):
        """
        更新压力传感器数据

        Args:
            data (dict): 压力数据 {'LF': float, 'LB': float, 'RF': float, 'RB': float}
        """
        self._sensor_data.update(data)
        self.data_updated.emit(self._sensor_data)

    def update_motor_position(self, data: dict):
        """
        更新电机位置数据

        Args:
            data (dict): 电机位置数据
        """
        self._motor_positions.update(data)

    def get_pressure_data(self) -> dict:
        """获取压力数据"""
        return self._sensor_data.copy()

    def get_motor_position(self) -> dict:
        """获取电机位置数据"""
        return self._motor_positions.copy()

    def get_channel_value(self, channel: str) -> float:
        """
        获取指定通道的压力值

        Args:
            channel (str): 通道名称 'LF', 'LB', 'RF', 'RB'

        Returns:
            float: 压力值
        """
        return self._sensor_data.get(channel, 0.0)

    def reset(self):
        """重置所有数据"""
        for key in self._sensor_data:
            self._sensor_data[key] = 0.0
        for key in self._motor_positions:
            self._motor_positions[key] = 0.0
        self.data_updated.emit(self._sensor_data)
