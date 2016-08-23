#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtcm_checker.py
# Author        : bssthu
# Project       : rtk_checker
# Description   :
#

from rtk_protocol.base_data_handler import BaseDataHandler
from rtk_protocol.rtcm_util import try_parse


class RtcmChecker(BaseDataHandler):
    """解析差分数据的线程"""

    def __init__(self, acceptable_rtcm_msg_type):
        """构造函数

        Args:
            acceptable_rtcm_msg_type: 使用的 rtcm 类型
        """
        super().__init__()
        self.is_acceptable_msg_type = None
        if isinstance(acceptable_rtcm_msg_type, list):
            if len(acceptable_rtcm_msg_type) > 0:
                self.is_acceptable_msg_type = lambda x: x in acceptable_rtcm_msg_type
            else:
                self.is_acceptable_msg_type = lambda x: True
        self.data = []
        self.log = None

    def get_parsed_data(self):
        """解析数据

        Returns:
            <bytes> 解析了的完整报文
        """

        if len(self.data) <= 0:
            return None
        # 拷贝
        data = self.data[:]
        if self.is_acceptable_msg_type is None:
            # 如果不用解析
            self.data.clear()
            return bytes(data)

        try:
            # 解析
            index, len_message, msg_type = try_parse(data)
            if index > 0:
                # 删除无法解析的数据
                self.log.debug('unknown data size: %d' % index)
                # print unknown data
                # print([hex(x) for x in data[:index]])
                # print(bytes(data[:index]).decode('utf-8', errors='ignore'))
                self.pop_front(index)
            if len_message > 0:
                # 删除解析后的数据
                self.log.debug('pkg size: %d, msg size: %d, msg type: %d' % (len_message, len_message-6, msg_type))
                # print([hex(x) for x in data[:index + len_message]])
                # print(bytes(data[:index + len_message]).decode('utf-8', errors='ignore'))
                parsed_data = self.pop_front(len_message)
                if self.is_acceptable_msg_type(msg_type):
                    return bytes(parsed_data)
        except Exception as e:
            self.log.error('checker error when parse msg: %s' % e)
        return None
