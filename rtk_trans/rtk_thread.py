#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : socket 转发数据
# 

import threading
import time

from rtk_trans.control_thread import ControlThread
from rtk_trans.server_thread import ServerThread
from rtk_trans.station_client_thread import StationClientThread
from rtk_trans.station_server_thread import StationServerThread
from rtk_utils.config_loader import Entry
from rtk_utils.http_thread import RtkStatus
from rtk_utils import log


class RtkThread(threading.Thread):
    def __init__(self, name, config, update_status_cb):
        """初始化

        Args:
            name (str): rtk 线程名
            config (Entry): 配置 dict
            update_status_cb (Callable[[str], None]): 更新差分状态的回调函数
        """
        super().__init__()
        self.name = name
        self.update_status_cb = update_status_cb
        self.server = None
        self.controller = None
        self.station = None
        self.running = True

        self.config = config
        self.station_mode = config.station_mode

        self.listen_port = config.listen_port
        self.control_port = config.control_port
        self.rtk_filter = config.filter

    def got_data_cb(self, data):
        """接收到差分数据的回调函数

        Args:
            data (bytes): 收到的数据包
        """
        self.server.dispatcher.data_queue.put(data)
        self.update_status_cb(None)

    def got_command_cb(self, command):
        """接收到来自控制端口的指令的回调函数

        Args:
            command (bytes): 待处理的命令
        """
        if command == b'reset server':
            old_server = self.server
            self.server = ServerThread(self.listen_port)
            old_server.running = False
            self.server.start()
        elif command == b'list':
            self.controller.msg_queue.put('client count: %d\r\n' % len(self.server.dispatcher.clients))
            for _id, sender in self.server.dispatcher.clients.copy().items():
                self.controller.msg_queue.put('%d: %s, %d\r\n' %
                                              (sender.sender_id, sender.address, sender.send_count))
        elif command.startswith(b'send:') and len(command) > len('send:'):
            self.station.send(command[len('send:'):])

    def stop_thread(self, name, thread_to_stop):
        """结束指定线程

        Args:
            name (str): 要结束的线程名，名字仅用于 log
            thread_to_stop (threading.Thread): 要结束的线程
        """
        try:
            thread_to_stop.running = False
            thread_to_stop.join()
        except Exception as e:
            log.error('rtk thread: failed to stop thread %s: %s' % (name, e))

    def run(self):
        log.info('rtk thread: start')

        # threads
        self.server = ServerThread(self.listen_port)
        self.controller = ControlThread(self.control_port, self.got_command_cb)
        # station_mode 指基站的模式，本地的模式与之相反
        if self.station_mode == 'server':
            # 基站为 server, 本地为 client
            self.station = StationClientThread(self.name, self.config,
                                               self.got_data_cb, self.update_status_cb)
        else:
            # 基站为 client, 本地为 server
            self.station = StationServerThread(self.name, self.config,
                                               self.got_data_cb, self.update_status_cb)

        self.server.start()
        self.controller.start()
        self.station.start()

        # wait
        while self.running and self.server.running and self.station.running:
            time.sleep(2)

        # quit & clean up
        self.stop_thread('controller', self.controller)
        self.stop_thread('station', self.station)
        self.stop_thread('server', self.server)

        self.update_status_cb(RtkStatus.S_TERMINATED)

        log.info('rtk thread: bye')
        self.running = False
