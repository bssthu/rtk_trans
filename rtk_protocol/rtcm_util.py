#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtcm_util.py
# Author        : bssthu
# Project       : rtk_checker
# Description   :
#

try:
    import crcmod
    crc24q_func = crcmod.mkCrcFun(0b1100001100100110011111011, initCrc=0, rev=False)
except ImportError:
    print('Warning: failed to import crcmod.')
    crc24q_func = None


def try_parse(data):
    """从头开始，逐字节尝试解析

    Args:
        data: 要解析的数据

    Returns:
        index: 尝试到的位置
        len_message: 报文总长度，-1表示没有报文，-2表示报文未完
        msg_type: 报文类型
    """
    for i in range(0, len(data) - 1):
        len_message = try_parse_from_begin(data[i:])
        if len_message > 0 and i + len_message <= len(data):
            msg_type = get_msg_type(data[i+3:])
            return i, len_message, msg_type
        if len_message == -2:   # 报文未完，不能删除
            return 0, len_message, -1
    return len(data), -1, -1


def try_parse_from_begin(data):
    """从 data 首字节开始解析

    Args:
        data: 要解析的数据

    Returns:
        正整数: 报文长度
        -1: 无效
        -2: 报文不完整
    """

    # 检查引导字和保留字
    if (len(data) < 3) or (data[0] != 0xd3) or (data[1] & 0b11111100 != 0x0):
        return -1

    # 报文长度
    len_rtcm = (data[1] & 0b11) * 0x100 + data[2]
    len_full_message = len_rtcm + 3 + 3     # 加上引导字、保留字、校验后的总长度
    if len_rtcm <= 0:
        return -1
    elif len_full_message > len(data):
        return -2

    # 校验
    message = data[0:3+len_rtcm]
    crc_from_message = int.from_bytes(data[3+len_rtcm:3+len_rtcm+3], 'big')

    # 计算 CRC
    if crc24q_func is not None:
        crc = crc24q_func(bytes(message))
    else:
        message_binary = ''.join(['{0:08b}'.format(x) for x in message])
        crc = int(get_crc(message_binary), 2)

    if crc != crc_from_message:
        return -1

    return len_full_message


def get_crc(msg, div='1100001100100110011111011', code='0'*24):
    """Cyclic Redundancy Check

    https://gist.github.com/evansneath/4650991

    Args:
        msg: 需要校验的信息
        div: 生成多项式
        code: 需要校验的信息

    Returns:
        CRC码，默认使用 CRC-24Q 方法
    """
    # Append the code to the message. If no code is given, default to '000'
    msg += code

    # Convert msg and div into list form for easier handling
    msg = list(msg)
    div = list(div)

    # Loop over every message bit (minus the appended code)
    for i in range(len(msg)-len(code)):
        # If that message bit is 1, perform modulo 2 multiplication
        if msg[i] == '1':
            for j in range(len(div)):
                # Perform modulo 2 multiplication on each index of the divisor
                msg[i+j] = str((int(msg[i+j])+int(div[j]))%2)

    # Output the last error-checking code portion of the message generated
    return ''.join(msg[-len(code):])


def get_msg_type(msg):
    """判断报文类型

    Args:
        msg: 待解析消息

    Returns:
        msg_type: 消息类型
    """
    msg_type = (msg[0] << 4) + ((msg[1] & 0xF0) >> 4)
    return msg_type
