#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : station_server_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import socket
import threading
from rtk_trans.station_connection_thread import StationConnectionThread


class StationServerThread(threading.Thread):
    """从差分源服务器接收数据的线程，差分源为 tcp client, 本地为 tcp server"""

    def __init__(self, port, got_data_cb):
        """构造函数

        Args:
            port: 监听的端口
            got_data_cb: 接收到数据包时调用的回调函数
        """
        super().__init__()
        self.port = port
        self.got_data_cb = got_data_cb
        self.connection_thread = None
        self.log = None
        self.running = True

    def run(self):
        """线程主函数

        循环运行，接受新的客户端的连接。
        """
        self.log.info('station server thread: start, port: %d' % self.port)
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', self.port))
            server.listen(1)
            server.settimeout(3)    # timeout: 3s
            while self.running:
                try:
                    conn, address = server.accept()
                    conn.settimeout(3)
                    self.log.debug('new station connection from: %s' % str(address))
                    self.got_client(conn, str(address))
                except socket.timeout:
                    pass
            # clean up
            server.close()
            if self.connection_thread is not None and self.connection_thread.is_alive():
                self.connection_thread.running = False
                self.connection_thread.join()
            self.log.info('station server thread: bye')
        except Exception as e:
            self.log.error('station server thread error: %s' % e)
            self.running = False

    def got_client(self, conn, address):
        # stop old
        if self.connection_thread is not None and self.connection_thread.is_alive():
            self.log.info('stopping existing station connection thread.')
            self.connection_thread.running = False
            self.connection_thread.join()
            self.connection_thread = None
        self.connection_thread = StationConnectionThread(conn, address, self.got_data_cb)
        self.connection_thread.log = self.log
        self.connection_thread.start()
