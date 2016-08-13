#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : station_client_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import socket
import threading
import time
from rtk_trans.station_connection_thread import StationConnectionThread

BUFFER_SIZE = 4096


class StationClientThread(threading.Thread):
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
        self.server_ip = config['stationIpAddress']
        self.server_port = config['stationPort']
        self.got_data_cb = got_data_cb
        self.connection_thread = None
        self.rcv_count = 0
        self.log = None
        self.running = True

    def run(self):
        """线程主函数

        循环运行，建立连接、接收数据，并在连接出错时重连。
        """
        self.log.info('station client thread: start')
        while self.running:
            try:
                # 建立连接
                conn = self.connect()
                self.log.info('station client thread: connected')
                # 开启数据接收线程
                self.run_receive_data_thread(conn)
            except Exception as e:
                self.log.error('station client thread error: %s' % e)
                time.sleep(3)
        # disconnect
        if self.connection_thread is not None and self.connection_thread.is_alive():
            self.connection_thread.running = False
            self.connection_thread.join()
        self.log.info('station client thread: bye')

    def run_receive_data_thread(self, conn):
        """循环接收数据

        在超时时返回（重连），在出错时返回（重连）。

        Args:
            conn: 新建的连接 socket
        """
        # start connection thread
        address = str((self.server_ip, self.server_port))
        self.connection_thread = StationConnectionThread(self.name, conn, address, self.config)
        self.connection_thread.got_data_cb = self.got_data_cb   # 本地为 client, 不验证对方身份，走个流程即可
        self.connection_thread.log = self.log
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

    def reconnect(self, client):
        """重连 socket"""
        try:
            client.close()
        except:
            self.log.error('station client exception when close.')
        return self.connect()
