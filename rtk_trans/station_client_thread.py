#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : station_client_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import socket
import threading
import time
from rtk_trans import log

BUFFER_SIZE = 4096


class StationClientThread(threading.Thread):
    """从差分源服务器接收数据的线程，差分源为 tcp server, 本地为 tcp client"""

    def __init__(self, server_ip, server_port, got_data_cb):
        """构造函数

        Args:
            server_ip: 差分源服务器IP地址
            server_port: 差分源服务器端口
            got_data_cb: 接收到数据包时调用的回调函数
        """
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port
        self.got_data_cb = got_data_cb
        self.rcv_count = 0
        self.log = None
        self.running = True

    def run(self):
        """线程主函数

        循环运行，建立连接、接收数据，并在连接出错时重连。
        """
        self.log.info('client thread: start')
        while self.running:
            try:
                self.receive_data()
            except Exception as e:
                self.log.error('client thread error: %s' % e)
                time.sleep(3)
        self.log.info('client thread: bye')

    def receive_data(self):
        """建立连接并循环接收数据

        在超时时重连，在出错时返回。
        """
        client = self.connect()
        self.log.info('client thread: connected')
        timeout_count = 0
        while self.running:
            try:
                # 接收数据
                data = client.recv(BUFFER_SIZE)
                # 连接失败的处理
                if len(data) == 0:
                    raise RuntimeError('socket connection broken')
                # 收到数据后的处理
                self.rcv_count += 1
                self.log.debug('rcv %d bytes. id: %d' % (len(data), self.rcv_count))
                self.got_data_cb(data, self.rcv_count)
                timeout_count = 0
            except socket.timeout:
                # 超时处理，超时5次时主动重连
                # 超时时间短是为了在需要时能快速退出
                timeout_count += 1
                if timeout_count >= 5:
                    timeout_count = 0
                    client = self.reconnect(client)
                    self.log.debug('client timeout, reconnect')
        try:
            client.close()
        except socket.error:
            pass
        except Exception as e:
            self.log.error('client exception when close: %s' % e)

    def connect(self):
        """尝试建立连接并设置超时参数"""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)
        try:
            client.connect((self.server_ip, self.server_port))
        except socket.timeout as e:
            raise socket.timeout('%s when connect' % e)
        client.settimeout(3)
        return client

    def reconnect(self, client):
        """重连 socket"""
        try:
            client.close()
        except:
            self.log.error('client exception when close.')
        return self.connect()
