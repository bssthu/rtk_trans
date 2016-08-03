#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : station_connection_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   :
#

import socket
import threading
from rtk_trans.http_thread import RtkStatus

BUFFER_SIZE = 4096


class StationConnectionThread(threading.Thread):
    """负责与差分源客户端通信的线程"""

    def __init__(self, name, client_socket, address, got_data_cb):
        """构造函数

        Args:
            name: rtk 服务名
            client_socket: 与客户端通信的 socket
            address: 客户端地址
        """
        super().__init__()
        self.name = name
        self.client_socket = client_socket
        self.address = address
        self.got_data_cb = got_data_cb
        self.rcv_count = 0
        self.log = None
        self.running = True

    def run(self):
        """线程主函数

        循环运行，接收来自客户端的数据并丢弃，向客户端发送 data_queue 中的数据包。
        当 data_queue 过长时，丢弃旧的数据包。
        """
        self.log.info('station connection thread: start, %s' % self.address)
        RtkStatus.update_status(self.name, RtkStatus.S_CONNECTED)
        try:
            self.receive_data()
        except Exception as e:
            self.log.error('station connection thread error: %s' % e)
        RtkStatus.update_status(self.name, RtkStatus.S_DISCONNECTED)
        self.log.info('station connection thread: bye')

    def receive_data(self):
        """循环接收数据"""
        timeout_count = 0
        while self.running:
            try:
                # 接收数据
                data = self.client_socket.recv(BUFFER_SIZE)
                # 连接失败的处理
                if len(data) == 0:
                    raise RuntimeError('socket connection broken')
                # 收到数据后的处理
                self.rcv_count += 1
                self.log.debug('rcv %d bytes. id: %d' % (len(data), self.rcv_count))
                self.got_data_cb(data, self.rcv_count)
                timeout_count = 0
            except socket.timeout:
                # 超时处理，超时5次时主动断开
                # 超时时间短是为了在需要时能快速退出
                timeout_count += 1
                if timeout_count >= 5:
                    self.running = False
                    self.log.info('station connection thread: timeout')
        self.disconnect()

    def disconnect(self):
        """断开连接"""
        try:
            self.client_socket.close()
        except socket.error:
            pass
        except Exception as e:
            self.log.error('station connection thread exception when close: %s' % e)
