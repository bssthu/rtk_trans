#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : base_data_handler.py
# Author        : bssthu
# Project       : rtk_trans
# Description   :
#

from rtk_utils import log


class BaseDataHandler:
    def __init__(self):
        self.data = []

    def push_back(self, data):
        """加入新收到的数据

        Args:
            data: 新收到的数据
        """
        try:
            self.data.extend(data)
        except Exception as e:
            log.error('checker error when add: %s' % e)

    def pop_front(self, len_to_remove):
        """从 data 开头移除数据

        Args:
            len_to_remove: 要删除的数据长度

        Returns:
            <bytes> ret_data: 被删除的数据
        """
        ret_data = None
        try:
            if len_to_remove > 0:
                if len_to_remove < len(self.data):
                    ret_data = self.data[:len_to_remove]
                    self.data = self.data[len_to_remove:]
                else:
                    ret_data = self.data[:]
                    self.data.clear()
        except Exception as e:
            log.error('checker error when remove data: %s' % e)
        return bytes(ret_data)
