#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : server_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import socket
import threading
from rtk_trans.dispatcher import Dispatcher


class ServerThread(threading.Thread):
    """监听来自客户端的连接的线程"""

    def __init__(self, port):
        """构造函数

        Args:
            port: 监听的端口
        """
        super().__init__()
        self.port = port
        self.dispatcher = Dispatcher()
        self.log = None
        self.running = True

    def run(self):
        """线程主函数

        循环运行，接受新的客户端的连接。
        """
        self.dispatcher.log = self.log
        self.log.info('server thread: start, port: %d' % self.port)
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', self.port))
            server.listen(100)      # 并发
            server.settimeout(1)    # timeout: 1s
            while self.running:
                # 接受连接
                try:
                    conn, address = server.accept()
                    conn.settimeout(3)
                    self.dispatcher.add_client(conn, address)
                    self.log.debug('new client from: %s' % str(address))
                except socket.timeout:
                    pass
                # 分发数据
                self.dispatcher.dispatch()
            server.close()
            self.dispatcher.close_all_clients()
            self.log.info('server thread: bye')
        except Exception as e:
            self.log.error('server thread error: %s' % e)
            self.running = False
