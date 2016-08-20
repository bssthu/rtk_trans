#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : station_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import threading


class StationThread(threading.Thread):
    """从差分源服务器接收数据的线程，差分源为 tcp server, 本地为 tcp client"""

    def __init__(self, name, config, got_data_cb):
        """构造函数

        Args:
            name: rtk 服务名
            config: 配置
            got_data_cb: 接收到数据包时调用的回调函数
        """
        super().__init__()
        self.name = name
        self.config = config
        self.got_data_cb = got_data_cb
        self.connection_thread = None
        self.log = None
        self.running = True

    def send(self, data):
        """向差分源发送数据"""
        connection_thread = self.connection_thread
        if connection_thread is not None:
            connection_thread.add_data_to_send_queue(data)

    def disconnect(self):
        """关闭连接，准备退出"""
        if self.connection_thread is not None and self.connection_thread.is_alive():
            self.connection_thread.running = False
            self.connection_thread.join()
