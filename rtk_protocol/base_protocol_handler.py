#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : base_protocol_handler.py
# Author        : bssthu
# Project       : rtk_checker
# Description   :
#

from rtk_protocol.base_data_handler import BaseDataHandler


class BaseProtocolHandler(BaseDataHandler):
    """协议解析工具"""

    def __init__(self, rtcm_checker):
        """构造函数

        Args:
            rtcm_checker: rtcm 协议检查类
        """
        super().__init__()
        self.rtcm_checker = rtcm_checker
        self.data = []
        self.log = None

    def handshake(self):
        """重载方法实现握手"""
        return True

    def get_parsed_data(self):
        """解析数据

        Returns:
            解析了的完整报文
        """

        # 拷贝
        self.rtcm_checker.push_back(self.data)
        self.data.clear()

        try:
            # 解析
            return self.rtcm_checker.get_parsed_data()
        except Exception as e:
            self.log.error('checker error when parse msg: %s' % e)
        return None
