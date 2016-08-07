#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtcm_checker.py
# Author        : bssthu
# Project       : rtk_checker
# Description   :
#

from rtk_trans.rtcm_util import try_parse


class RtcmChecker():
    """解析差分数据的线程"""

    def __init__(self, acceptable_rtcm_msg_type):
        """构造函数

        Args:
            acceptable_rtcm_msg_type: 使用的 rtcm 类型
        """
        if isinstance(acceptable_rtcm_msg_type, list):
            self.acceptable_rtcm_msg_type = acceptable_rtcm_msg_type
        else:
            self.acceptable_rtcm_msg_type = None
        self.data = []
        self.log = None

    def parse_data(self):
        """解析数据

        Returns:
            解析了的完整报文
        """

        # 拷贝
        data = None
        try:
            data = self.data.copy()
        except Exception as e:
            self.log.error('checker error when copy data: %s' % e)
        if data is None:
            return None

        try:
            # 解析
            index, len_message, msg_type = try_parse(data)
            if index > 0:
                # 删除无法解析的数据
                self.log.debug('unknown data size: %d' % index)
                # print unknown data
                # print([hex(x) for x in data[:index]])
                # print(bytes(data[:index]).decode('utf-8', errors='ignore'))
                self.remove_from_data(index)
            if len_message > 0:
                # 删除解析后的数据
                self.log.debug('pkg size: %d, msg size: %d, msg type: %d' % (len_message, len_message-6, msg_type))
                # print([hex(x) for x in data[:index + len_message]])
                # print(bytes(data[:index + len_message]).decode('utf-8', errors='ignore'))
                parsed_data = self.remove_from_data(len_message)
                if self.acceptable_rtcm_msg_type is not None \
                        and parsed_data is not None:
                    if len(self.acceptable_rtcm_msg_type) == 0 or msg_type in self.acceptable_rtcm_msg_type:
                        return bytes(parsed_data)
        except Exception as e:
            self.log.error('checker error when parse msg: %s' % e)
        return None

    def add_data(self, data):
        """加入新收到的数据

        Args:
            data: 新收到的数据
        """
        try:
            self.data.extend(data)
        except Exception as e:
            self.log.error('checker error when add: %s' % e)

    def remove_from_data(self, len_to_remove):
        """从 data 开头移除数据

        Args:
            len_to_remove: 要删除的数据长度

        Returns:
            ret_data: 被删除的数据
        """
        ret_data = None
        try:
            if (len_to_remove > 0) and (len_to_remove < len(self.data)):
                ret_data = self.data[:len_to_remove]
                self.data = self.data[len_to_remove:]
            else:
                ret_data = self.data
                self.data = []
        except Exception as e:
            self.log.error('checker error when remove data: %s' % e)
        return ret_data
