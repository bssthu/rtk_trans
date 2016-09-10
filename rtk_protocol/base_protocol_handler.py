#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : base_protocol_handler.py
# Author        : bssthu
# Project       : rtk_trans
# Description   :
#

from rtk_protocol.base_data_handler import BaseDataHandler
from rtk_protocol.rtcm_checker import RtcmChecker
from rtk_utils import log


class BaseProtocolHandler(BaseDataHandler):
    """协议解析工具"""

    def __init__(self, config):
        """构造函数

        Args:
            config (dict): 配置
        """
        super().__init__()
        self.config = config
        # rtk_filter 表示 rtcm 报文过滤。
        # None 表示不过滤，[] (empty list) 表示保留所有 rtcm 报文，list 表示保留其中的整数对应的报文
        self.rtk_filter = config['filter'] if 'filter' in config.keys() else None
        self.rtcm_checker = RtcmChecker(self.rtk_filter)
        self.data = []

    def handshake(self):
        """重载方法实现握手"""
        return True

    def get_parsed_data(self):
        """解析数据

        Returns:
            return (bytes): 解析了的完整报文
        """

        # 拷贝
        self.rtcm_checker.push_back(self.data)
        self.data.clear()

        try:
            # 解析
            return self.rtcm_checker.get_parsed_data()
        except Exception as e:
            log.error('checker error when parse msg: %s' % e)
        return None
