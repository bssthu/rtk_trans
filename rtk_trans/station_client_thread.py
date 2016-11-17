#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : station_client_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import socket
import time

from rtk_trans.station_connection_thread import StationConnectionThread
from rtk_trans.station_thread import StationThread
from rtk_utils.config_loader import Entry
from rtk_utils import log


class StationClientThread(StationThread):
    """从差分源服务器接收数据的线程，差分源为 tcp server, 本地为 tcp client"""

    def __init__(self, name, config, got_data_cb, update_status_cb):
        """构造函数

        Args:
            name (str): rtk 服务名
            config (Entry): 配置
            got_data_cb (Callable[[bytes], None]): 接收到数据包时调用的回调函数
            update_status_cb (Callable[[str], None]): 更新差分状态的回调函数
        """
        super().__init__(name, config, got_data_cb, update_status_cb)
        self.server_ip = config.station_ip_address
        self.server_port = config.station_port

    def run(self):
        """线程主函数

        循环运行，建立连接、接收数据，并在连接出错时重连。
        """
        log.info('station client thread: start')
        while self.running:
            try:
                # 建立连接
                conn = self.connect()
                log.info('station client thread: connected')
                # 开启数据接收线程
                self.run_receive_data_thread(conn)
            except Exception as e:
                log.error('station client thread error: %s' % e)
                time.sleep(3)
        # disconnect
        self.disconnect()
        log.info('station client thread: bye')

    def run_receive_data_thread(self, conn):
        """循环接收数据

        在超时时返回（重连），在出错时返回（重连）。

        Args:
            conn (socket.socket): 新建的连接 socket
        """
        # start connection thread
        address = str((self.server_ip, self.server_port))
        self.connection_thread = StationConnectionThread(self.name, conn, address, self.config)
        self.connection_thread.got_data_cb = self.got_data_cb   # 本地为 client, 不验证对方身份，走个流程即可
        self.connection_thread.update_status_cb = self.update_status_cb
        self.connection_thread.start()
        # wait for connection thread
        while self.running and self.connection_thread.is_alive():
            self.connection_thread.join(timeout=1)

    def connect(self):
        """尝试建立连接并设置超时参数"""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)
        try:
            client.connect((self.server_ip, self.server_port))
        except socket.timeout as e:
            raise socket.timeout('%s when connect' % e)
        client.settimeout(3)
        return client
