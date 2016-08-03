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

    def __init__(self, server_ip, server_port, got_data_cb):
        """构造函数

        Args:
            server_ip: 差分源服务器IP地址
            server_port: 差分源服务器端口
            got_data_cb: 接收到数据包时调用的回调函数
        """
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port
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
                self.receive_data()
            except Exception as e:
                self.log.error('station client thread error: %s' % e)
                time.sleep(3)
        if self.connection_thread is not None and self.connection_thread.is_alive():
            self.connection_thread.running = False
            self.connection_thread.join()
        self.log.info('station client thread: bye')

    def receive_data(self):
        """建立连接并循环接收数据

        在超时时重连，在出错时返回。
        """
        conn = self.connect()
        self.log.info('station client thread: connected')
        # start connection thread
        self.connection_thread = StationConnectionThread(conn, str((self.server_ip, self.server_port)), self.got_data_cb)
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
