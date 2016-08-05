#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : dispatcher_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   :
#

import threading
import queue
from rtk_trans.sender_thread import SenderThread
from rtk_trans.rtcm_checker import RtcmChecker


class DispatcherThread(threading.Thread):
    """分发收到的差分数据的线程"""

    def __init__(self, rtk_filter):
        """构造函数

        Args:
            rtk_filter: rtcm 报文过滤。None 表示不过滤，[] (empty list) 表示保留所有 rtcm 报文，list 表示保留其中的整数对应的报文
        """
        super().__init__()
        self.data_queue = queue.Queue()
        self.checker = RtcmChecker(rtk_filter, self.got_data)
        self.clients = {}
        self.new_client_id = 0
        self.log = None
        self.running = True

    def run(self):
        """线程主函数

        循环运行，不断把 self.data_queue 中的数据包分发给各 SenderThread
        """
        self.log.info('dispatcher thread: start')
        while self.running:
            try:
                data, rcv_count = self.data_queue.get(timeout=1)
                self.data_queue.task_done()
                self.checker.add_data(data)
                self.checker.parse_data()
            except queue.Empty:
                pass
        self.stop_all_clients()
        self.log.info('dispatcher thread: bye')

    def got_data(self, data):
        """收到数据时的处理，在 send_data 之前

        Args:
            data: 收到的数据
        """
        try:
            num_clients = self.send_data(data)
            self.log.debug('send %d bytes to %d clients.' % (len(data), num_clients))
        except Exception as e:
            self.log.error('dispatcher thread error: %s' % e)

    def send_data(self, data):
        """分发数据

        Args:
            data: 要分发的数据
        """
        clients = self.clients.copy()   # 防止因中途被修改而异常
        for _id, sender in clients.items():
            if sender.running:
                sender.data_queue.put(data)
            else:
                del self.clients[_id]
        return len(clients)

    def add_client(self, client_socket, address):
        """新的客户端连入时调用此函数

        建立新的 SenderThread 并加入分发列表。

        Args:
            client_socket: 与客户端通信的 socket
            address: 客户端地址
        """
        sender = SenderThread(client_socket, address, self.new_client_id)
        sender.log = self.log
        self.clients[self.new_client_id] = sender
        self.new_client_id += 1
        sender.start()

    def stop_all_clients(self):
        """关闭所有与客户端的连接"""
        for _id, sender in self.clients.items():
            sender.running = False
        for _id, sender in self.clients.items():
            sender.join()
