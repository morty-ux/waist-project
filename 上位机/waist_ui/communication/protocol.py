# coding: utf-8
"""
ESP8266通信协议定义
定义数据包格式和命令类型，与ESP8266端保持一致
"""


class Protocol:
    """通信协议"""

    # 数据包格式: [起始符][长度][类型][数据][校验和][结束符]
    START_BYTE = 0xAA
    END_BYTE = 0x55

    # 命令类型 (上位机 -> ESP8266)
    CMD_SET_FORCE = 0x01      # 设置力控参数
    CMD_GET_STATUS = 0x02     # 获取状态
    CMD_RESET = 0x03          # 系统复位
    CMD_IDENTIFY = 0x04       # 参数自动辨识
    CMD_SENSOR_ON = 0x05      # 开启传感器上报
    CMD_SENSOR_OFF = 0x06     # 关闭传感器上报
    CMD_SET_FREQ = 0x07       # 设置上报频率

    # 数据类型 (ESP8266 -> 上位机)
    DATA_SENSOR = 0x10        # 传感器数据
    DATA_STATUS = 0x11        # 状态数据
    DATA_RESPONSE = 0x12       # 响应数据

    @staticmethod
    def build_packet(cmd_type, data=None):
        """
        构建数据包

        数据包格式:
        +--------+--------+------+--------+------+--------+
        | 起始符 | 长度   | 类型 | 数据   | 校验 | 结束符 |
        | 0xAA   | Length | Type | Data   | CS   | 0x55   |
        +--------+--------+------+--------+------+--------+

        Args:
            cmd_type (int): 命令/数据类型
            data (list): 数据载荷

        Returns:
            bytes: 完整数据包
        """
        if data is None:
            data = []

        length = len(data) + 1
        packet = [Protocol.START_BYTE, length, cmd_type] + data

        checksum = sum(packet[1:]) & 0xFF
        packet.append(checksum)
        packet.append(Protocol.END_BYTE)

        return bytes(packet)

    @staticmethod
    def parse_packet(packet):
        """
        解析数据包

        Args:
            packet (bytes/bytearray): 原始数据包

        Returns:
            tuple: (数据类型, 数据载荷, 校验和) ,失败返回(None, None, None)
        """
        if len(packet) < 5:
            return None, None, None

        if packet[0] != Protocol.START_BYTE or packet[-1] != Protocol.END_BYTE:
            return None, None, None

        length = packet[1]
        data_type = packet[2]
        data = list(packet[3:-2])
        checksum = packet[-2]

        calc_checksum = sum(packet[1:-1]) & 0xFF
        if checksum != calc_checksum:
            return None, None, None

        return data_type, data, checksum

    @staticmethod
    def parse_sensor_data(payload):
        """
        解析传感器数据

        数据格式: [LF高位, LF低位, LB高位, LB低位, RF高位, RF低位, RB高位, RB低位]

        Args:
            payload (list): 传感器数据载荷

        Returns:
            dict: 解析后的传感器值 {'LF': 值, 'LB': 值, 'RF': 值, 'RB': 值}
        """
        if len(payload) < 8:
            return {}

        channels = ['LF', 'LB', 'RF', 'RB']
        sensor_data = {}

        for i, channel in enumerate(channels):
            high_byte = payload[i * 2]
            low_byte = payload[i * 2 + 1]
            value = (high_byte << 8) | low_byte
            sensor_data[channel] = value

        return sensor_data

    @staticmethod
    def build_force_command(channel, value):
        """
        构建力控参数命令

        Args:
            channel (str): 通道名称 ('LF', 'LB', 'RF', 'RB')
            value (int): 力控值 (0-100)

        Returns:
            bytes: 命令数据包
        """
        data = [ord(channel[0]), value]
        return Protocol.build_packet(Protocol.CMD_SET_FORCE, data)
