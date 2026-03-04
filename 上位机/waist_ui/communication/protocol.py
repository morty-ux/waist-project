# coding: utf-8
"""
ESP8266通信协议定义
定义数据包格式和命令类型
"""


class Protocol:
    """通信协议"""

    # 数据包格式: [起始符][长度][类型][数据][校验和][结束符]
    START_BYTE = 0xAA
    END_BYTE = 0x55

    # 命令类型
    CMD_SET_FORCE = 0x01      # 设置力控参数
    CMD_GET_STATUS = 0x02      # 获取状态
    CMD_RESET = 0x03            # 系统复位
    CMD_IDENTIFY = 0x04         # 参数自动辨识

    # 数据类型
    DATA_SENSOR = 0x10          # 传感器数据
    DATA_STATUS = 0x11           # 状态数据
    DATA_RESPONSE = 0x12          # 响应数据

    @staticmethod
    def build_packet(cmd_type, data=None):
        """构建数据包"""
        if data is None:
            data = []

        length = len(data) + 1  # 命令类型 + 数据
        packet = [Protocol.START_BYTE, length, cmd_type] + data

        # 计算校验和
        checksum = sum(packet[1:]) & 0xFF
        packet.append(checksum)
        packet.append(Protocol.END_BYTE)

        return bytes(packet)

    @staticmethod
    def parse_packet(packet):
        """解析数据包"""
        if len(packet) < 5:
            return None, None, None

        if packet[0] != Protocol.START_BYTE or packet[-1] != Protocol.END_BYTE:
            return None, None, None

        length = packet[1]
        data_type = packet[2]
        data = list(packet[3:-2])
        checksum = packet[-2]

        # 验证校验和
        calc_checksum = sum(packet[1:-1]) & 0xFF
        if checksum != calc_checksum:
            return None, None, None

        return data_type, data, checksum
