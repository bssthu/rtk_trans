#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : socket 转发数据
# 

import threading
import time
from rtk_trans import log
from rtk_trans.control_thread import ControlThread
from rtk_trans.server_thread import ServerThread
from rtk_trans.station_client_thread import StationClientThread
from rtk_trans.station_server_thread import StationServerThread
from rtk_trans.http_thread import RtkStatus


class RtkThread(threading.Thread):
    def __init__(self, name, config):
        """初始化

        Args:
            name: rtk 线程名
            config: 配置 dict
        """
        super().__init__()
        self.name = name
        self.server = None
        self.controller = None
        self.station = None
        self.running = True

        self.config = config
        self.station_mode = config['stationMode'].lower().strip()
        if self.station_mode != 'server' and self.station_mode != 'client':
            raise Exception('Unrecognized station mode "%s". Should be "server" or "client". %s' % self.station_mode)
        if self.station_mode == 'server':
            self.station_ip_address = config['stationIpAddress']
        else:
            self.station_ip_address = None
        self.station_port = config['stationPort']
        self.listen_port = config['listenPort']
        self.control_port = config['controlPort'] if 'controlPort' in config.keys() else None
        self.rtk_filter = config['filter'] if 'filter' in config.keys() else None
        if not isinstance(self.rtk_filter, list):
            self.rtk_filter = None
        self.enable_log = config['enableLog'].lower() == 'true'
        # log init
        self.log = log.Log(name, self.enable_log)

    def got_data_cb(self, data):
        """接收到差分数据的回调函数

        Args:
            <bytes> data: 收到的数据包
        """
        self.server.dispatcher.data_queue.put(data)
        RtkStatus.update_rcv_time(self.name)

    def got_command_cb(self, command):
        """接收到来自控制端口的指令的回调函数

        Args:
            command: 待处理的命令
        """
        if command == b'reset server':
            old_server = self.server
            self.server = ServerThread(self.listen_port)
            self.server.log = self.log
            old_server.running = False
            self.server.start()
        elif command == b'list':
            self.controller.msg_queue.put('client count: %d\r\n' % len(self.server.dispatcher.clients))
            for _id, sender in self.server.dispatcher.clients.copy().items():
                self.controller.msg_queue.put('%d: %s, %d\r\n' % (sender.sender_id, sender.address, sender.send_count))
        elif command.startswith(b'send:') and len(command) > len('send:'):
            self.station.send(command[len('send:'):])

    def stop_thread(self, name, thread_to_stop):
        try:
            thread_to_stop.running = False
            thread_to_stop.join()
        except Exception as e:
            self.log.error('rtk thread: failed to stop thread %s: %s' % (name, e))

    def run(self):
        self.log.info('rtk thread: start')

        # threads
        self.server = ServerThread(self.listen_port)
        self.controller = ControlThread(self.control_port, self.got_command_cb)
        # station_mode 指基站的模式，本地的模式与之相反
        if self.station_mode == 'server':
            # 基站为 server, 本地为 client
            self.station = StationClientThread(self.name, self.config, self.got_data_cb)
        else:
            # 基站为 client, 本地为 server
            self.station = StationServerThread(self.name, self.config, self.got_data_cb)

        self.server.log = self.log
        self.controller.log = self.log
        self.station.log = self.log

        self.server.start()
        self.controller.start()
        self.station.start()

        # wait
        while self.running:
            time.sleep(2)

        # quit & clean up
        self.stop_thread('controller', self.controller)
        self.stop_thread('station', self.station)
        self.stop_thread('server', self.server)

        RtkStatus.update_status(self.name, RtkStatus.S_TERMINATED)

        self.log.info('rtk thread: bye')
        self.log.close()
