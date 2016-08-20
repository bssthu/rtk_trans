#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : station_connection_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   :
#

import socket
import threading
import queue
from rtk_protocol.select_protocol import select_protocol
from rtk_trans.http_thread import RtkStatus

BUFFER_SIZE = 4096


class StationConnectionThread(threading.Thread):
    """负责与差分源客户端通信的线程

    该线程同时负责协议解析
    """

    def __init__(self, name, client_socket, address, config):
        """构造函数

        Args:
            name: rtk 服务名
            client_socket: 与客户端通信的 socket
            address: 客户端地址
            config: 配置
        """
        super().__init__()
        self.name = name
        self.client_socket = client_socket
        self.address = address

        self.data_queue = queue.Queue()
        self.protocol_handler = select_protocol(config)

        self.got_data_cb = lambda data: None    # 连接建立后再设置
        self.rcv_count = 0
        self.handshake_ok = False
        self.log = None
        self.running = True

    def run(self):
        """线程主函数

        循环运行，接收来自客户端的数据并丢弃，向客户端发送 data_queue 中的数据包。
        当 data_queue 过长时，丢弃旧的数据包。
        """
        self.protocol_handler.log = self.log
        self.protocol_handler.rtcm_checker.log = self.log
        self.log.info('station connection thread: start, %s' % self.address)
        RtkStatus.update_status(self.name, RtkStatus.S_CONNECTED)

        try:
            self.send_and_receive_data()
        except Exception as e:
            self.log.error('station connection thread error: %s' % e)
        RtkStatus.update_status(self.name, RtkStatus.S_DISCONNECTED)
        self.log.info('station connection thread: bye')

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
                # 超时处理，超时5次时主动断开
                # 超时时间短是为了在需要时能快速退出
                timeout_count += 1
                if timeout_count >= 5:
                    self.running = False
                    self.log.info('station connection thread: timeout')
        self.disconnect()

    def send_data_from_queue(self):
        """发送队列里的所有数据"""
        data = []
        try:
            while True:
                data = self.data_queue.get(timeout=0.1)
                self.data_queue.task_done()
        except queue.Empty:
            pass
        if len(data) > 0:
            self.client_socket.sendall(data)

    def parse_data(self, data):
        """收到数据后的处理"""
        self.rcv_count += 1
        self.log.debug('rcv %d bytes. id: %d' % (len(data), self.rcv_count))
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
        """向发送队列加入数据"""
        self.data_queue.put(data)

    def disconnect(self):
        """断开连接"""
        try:
            self.client_socket.close()
        except socket.error:
            pass
        except Exception as e:
            self.log.error('station connection thread exception when close: %s' % e)
