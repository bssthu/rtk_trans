#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : server_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import os
import socket
import threading

from rtk_trans.dispatcher import Dispatcher
from rtk_utils import log


class ServerThread(threading.Thread):
    """监听来自客户端的连接的线程"""

    def __init__(self, port):
        """构造函数

        Args:
            port (int): 监听的端口
        """
        super().__init__()
        self.port = port
        self.dispatcher = Dispatcher()
        self.running = True

    def run(self):
        """线程主函数

        循环运行，接受新的客户端的连接。
        """
        log.info('server thread: start, port: %d' % self.port)
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if os.name != 'nt':
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
                    log.debug('new client from: %s' % str(address))
                except socket.timeout:
                    pass
                # 分发数据
                self.dispatcher.dispatch()
            server.close()
            self.dispatcher.close_all_clients()
            log.info('server thread: bye')
        except Exception as e:
            log.error('server thread error: %s' % e)
            self.running = False
