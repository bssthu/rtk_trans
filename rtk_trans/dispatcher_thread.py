#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : dispatcher_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   :
#

import threading
import queue
from rtk_trans import log
from rtk_trans.sender_thread import SenderThread


class DispatcherThread(threading.Thread):
    """分发收到的差分数据的线程"""

    def __init__(self):
        """构造函数"""
        super().__init__()
        self.data_queue = queue.Queue()
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
                try:
                    num_clients = self.send_data(data)
                    self.data_queue.task_done()
                    self.log.debug('send %d bytes to %d clients. id: %d' % (len(data), num_clients, rcv_count))
                except Exception as e:
                    self.log.error('dispatcher thread error: %s' % e)
            except queue.Empty:
                pass
        self.stop_all_clients()
        self.log.info('dispatcher thread: bye')

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
        self.clients[self.new_client_id] = sender
        self.new_client_id += 1
        sender.start()

    def stop_all_clients(self):
        """关闭所有与客户端的连接"""
        for _id, sender in self.clients.items():
            sender.running = False
        for _id, sender in self.clients.items():
            sender.join()
