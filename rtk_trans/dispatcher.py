#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : dispatcher.py
# Author        : bssthu
# Project       : rtk_trans
# Description   :
#

import queue

from rtk_trans.sender_thread import SenderThread
from rtk_utils import log


class Dispatcher:
    """向客户端分发收到的差分数据的工具"""

    def __init__(self):
        """构造函数"""
        super().__init__()
        self.data_queue = queue.Queue()
        self.clients = {}
        self.new_client_id = 0
        self.running = True

    def dispatch(self):
        """每次执行时，把 self.data_queue 中的所有数据包合并，再分发给各 SenderThread"""
        data = b''
        try:
            while self.data_queue.qsize() > 0:
                data += self.data_queue.get(block=False)
                self.data_queue.task_done()
        except queue.Empty:
            pass
        if len(data) > 0:
            num_of_sender = self.send_data(bytes(data))
            log.debug('send %d bytes to %d clients.' % (len(data), num_of_sender))

    def send_data(self, data):
        """分发数据

        Args:
            data (bytes): 要分发的数据

        Returns:
            return (int): 客户端数量
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
            client_socket (socket.socket): 与客户端通信的 socket
            address (tuple[str, int]): 客户端地址
        """
        sender = SenderThread(client_socket, address, self.new_client_id)
        self.clients[self.new_client_id] = sender
        self.new_client_id += 1
        sender.start()

    def close_all_clients(self):
        """关闭所有与客户端的连接"""
        for _id, sender in self.clients.items():
            sender.running = False
        for _id, sender in self.clients.items():
            sender.join()
