#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : station_connection_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   :
#

import queue
import socket
import threading

from rtk_protocol.select_protocol import select_protocol
from rtk_utils import log, base64_log
from rtk_utils.config_loader import Entry
from rtk_utils.http_thread import RtkStatus

BUFFER_SIZE = 4096


class StationConnectionThread(threading.Thread):
    """负责与差分源客户端通信的线程

    该线程同时负责协议解析
    """

    def __init__(self, name, client_socket, address, config):
        """构造函数

        Args:
            name (str): rtk 服务名
            client_socket (socket.socket): 与客户端通信的 socket
            address (str): 客户端地址，用于 log
            config (Entry): 配置
        """
        super().__init__()
        self.name = name
        self.client_socket = client_socket
        self.address = address

        self.data_queue = queue.Queue()
        self.protocol_handler = select_protocol(config.__dict__)

        self.got_data_cb = lambda data: None    # 连接建立后再设置
        self.update_status_cb = lambda status: None

        self.rcv_count = 0
        self.handshake_ok = False
        self.running = True

    def run(self):
        """线程主函数

        循环运行，接收来自客户端的数据并丢弃，向客户端发送 data_queue 中的数据包。
        当 data_queue 过长时，丢弃旧的数据包。
        """
        log.info('station connection thread: start, %s' % self.address)
        self.update_status_cb(RtkStatus.S_CONNECTED)

        try:
            self.send_and_receive_data()
        except Exception as e:
            log.error('station connection thread error: %s' % e)
        self.update_status_cb(RtkStatus.S_DISCONNECTED)
        log.info('station connection thread: bye')

    def send_and_receive_data(self):
        """循环发送、接收数据"""
        timeout_count = 0
        while self.running:
            # 发送数据
            self.send_data_from_queue()
            # 接收数据
            try:
                data = self.client_socket.recv(BUFFER_SIZE)
                # 连接失败的处理
                if len(data) == 0:
                    raise RuntimeError('socket connection broken')
                # 收到数据后的处理
                self.parse_data(data)
                timeout_count = 0
            except socket.timeout:
                # 超时处理，超时 10 次时主动断开
                # 超时时间短是为了在需要时能快速退出
                timeout_count += 1
                if timeout_count >= 10:
                    self.running = False
                    log.info('station connection thread: timeout')
        self.disconnect()

    def send_data_from_queue(self):
        """发送队列里的所有数据"""
        data = b''
        try:
            while self.data_queue.qsize() > 0:
                data += self.data_queue.get(block=False)
                self.data_queue.task_done()
        except queue.Empty:
            pass
        if len(data) > 0:
            self.client_socket.sendall(data)

    def parse_data(self, data):
        """收到数据后的处理

        Args:
            data (list): 新收到的数据
        """
        self.rcv_count += 1
        log.debug('rcv %d bytes. id: %d' % (len(data), self.rcv_count))
        base64_log.raw(bytes(data))
        self.protocol_handler.push_back(data)

        # 握手
        if not self.handshake_ok:
            self.handshake_ok = self.protocol_handler.handshake()
        # 处理
        while self.running and self.handshake_ok:
            data = self.protocol_handler.get_parsed_data()
            if data is None or len(data) <= 0:
                break
            self.got_data_cb(data)

    def add_data_to_send_queue(self, data):
        """向发送队列加入数据

        Args:
            data (bytes): 要发送的数据
        """
        self.data_queue.put(data)

    def disconnect(self):
        """断开连接"""
        try:
            self.client_socket.close()
        except socket.error:
            pass
        except Exception as e:
            log.error('station connection thread exception when close: %s' % e)
