#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : station_server_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import socket
import threading
import time
from rtk_trans.station_connection_thread import StationConnectionThread
from rtk_trans import handshake_timeout_second


class StationServerThread(threading.Thread):
    """从差分源服务器接收数据的线程，差分源为 tcp client, 本地为 tcp server"""

    def __init__(self, name, port, got_data_cb, rtk_filter):
        """构造函数

        Args:
            name: rtk 服务名
            port: 监听的端口
            got_data_cb: 接收到数据包时调用的回调函数
            rtk_filter: rtcm 报文过滤
        """
        super().__init__()
        self.name = name
        self.port = port
        self.got_data_cb = got_data_cb
        self.rtk_filter = rtk_filter
        self.connection_thread = None
        self.new_connections = []   # 成员为: (连接线程, 连接建立时间)
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
                self.check_new_connections()
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
        """新客户端连入时的处理

        Args:
            conn: client socket
            address: 地址 str
        """
        new_connection_thread = StationConnectionThread(self.name, conn, address, self.got_data_cb)
        new_connection_thread.log = self.log
        new_connection_thread.start()
        self.new_connections.append((new_connection_thread, time.time()))

    def check_new_connections(self):
        """检查新建的连接是否通过了握手测试"""
        new_connections = self.new_connections[:]
        time_sec = time.time()

        for i in range(0, len(new_connections)):
            connection_thread, established_time_sec = new_connections[i]
            # 逐个检查新建立的连接，判断是否握手成功、是否超时
            if connection_thread.handshake_ok:
                # 握手成功
                if self.connection_thread is not None and self.connection_thread.is_alive():
                    # stop old
                    self.log.info('stopping existing station connection thread.')
                    self.connection_thread.running = False  # 不用等待
                    self.connection_thread.got_data_cb = lambda data: None
                # set new connection_thread
                self.connection_thread = connection_thread
                self.connection_thread.got_data_cb = self.got_data_cb
                self.new_connections.remove((connection_thread, established_time_sec))
            elif (time_sec - established_time_sec > handshake_timeout_second) or time_sec < established_time_sec:
                # 超时
                connection_thread.running = False   # 不用等待
                connection_thread.got_data_cb = lambda data: None
                self.new_connections.remove((connection_thread, established_time_sec))
