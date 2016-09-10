#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : sender_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   :
#

import queue
import socket
import threading

from rtk_utils import log


class SenderThread(threading.Thread):
    """负责与一个客户端通信的线程"""

    def __init__(self, client_socket, address, _id):
        """构造函数

        Args:
            client_socket (socket.socket): 与客户端通信的 socket
            address (tuple[str, int]): 客户端地址
            _id (int): SenderThread 的 ID
        """
        super().__init__()
        self.client_socket = client_socket
        self.address = address
        self.sender_id = _id
        self.data_queue = queue.Queue()
        self.send_count = 0
        self.running = True

    def run(self):
        """线程主函数

        循环运行，接收来自客户端的数据并丢弃，向客户端发送 data_queue 中的数据包。
        当 data_queue 过长时，丢弃旧的数据包。
        """
        log.info('sender thread %d: start, %s' % (self.sender_id, self.address))
        try:
            while self.running:
                # ignore old data
                while self.data_queue.qsize() > 10:
                    self.data_queue.get(block=False)
                # send data
                try:
                    data = self.data_queue.get(timeout=1)
                    self.client_socket.settimeout(5)
                    self.client_socket.sendall(data)
                    self.send_count += 1
                    self.data_queue.task_done()
                except queue.Empty:
                    pass
                # rcv useless data
                try:
                    self.client_socket.settimeout(0.1)
                    rcv_buf = self.client_socket.recv(256)
                    if len(rcv_buf) == 0:
                        log.info('sender thread %d has disconnected.' % self.sender_id)
                        # 退出
                        break
                except socket.timeout:
                    pass
        except Exception as e:
            log.error('sender thread %d error: %s' % (self.sender_id, e))
        self.disconnect()
        self.running = False
        log.info('sender thread %d: bye' % self.sender_id)

    def disconnect(self):
        """断开连接"""
        try:
            self.client_socket.close()
        except socket.error:
            pass
        except Exception as e:
            log.error('sender thread %d exception when close: %s' % (self.sender_id, e))
