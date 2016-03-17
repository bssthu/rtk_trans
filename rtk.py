#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : socket 转发数据
# 

import json
import log
from control_thread import ControlThread
from client_thread import ClientThread
from dispatcher_thread import DispatcherThread
from server_thread import ServerThread


class Rtk:
    def __init__(self):
        self.server = None
        self.controller = None
        self.dispatcher = None
        self.client = None

    def got_data_cb(self, data, rcv_count):
        self.dispatcher.data_queue.put((data, rcv_count))

    def got_client_cb(self, client_socket, address):
        self.dispatcher.add_client(client_socket, address)

    def got_command_cb(self, command):
        if command == 'reset server':
            old_dispatcher = self.dispatcher
            self.dispatcher = DispatcherThread()
            old_dispatcher.running = False
            self.dispatcher.start()
        elif command == 'list':
            self.controller.msg_queue.put('client count: %d\r\n' % len(self.dispatcher.clients))
            for _id, sender in self.dispatcher.clients.copy().items():
                self.controller.msg_queue.put('%d: %s, %d\r\n' % (sender.sender_id, sender.address, sender.send_count))

    def main(self):
        # config
        config_file_name = 'config.json'
        try:
            with open(config_file_name) as config_data:
                configs = json.load(config_data)
        except:
            print('failed to load config from config.json.')
            return

        # log init
        log.initialize_logging(configs['enableLog'].lower() == 'true')
        log.info('main: start')

        # threads
        self.server = ServerThread(configs['listenPort'], self.got_client_cb)
        self.controller = ControlThread(configs['controlPort'], self.got_command_cb)
        self.dispatcher = DispatcherThread()
        self.client = ClientThread(configs['serverIpAddress'], configs['serverPort'], self.got_data_cb)

        self.server.start()
        self.controller.start()
        self.dispatcher.start()
        self.client.start()

        # keyboard
        try:
            print("enter 'q' to quit")
            while input() != 'q':
                print("enter 'q' to quit. rcv count: %d, client count: %d"
                      % (self.client.rcv_count, len(self.dispatcher.clients)))
                if not self.client.running or not self.server.running:
                    break
        except KeyboardInterrupt:
            pass

        # quit & clean up
        self.controller.running = False
        self.controller.join()
        self.client.running = False
        self.client.join()
        self.server.running = False
        self.server.join()
        self.dispatcher.running = False
        self.dispatcher.join()
        log.info('main: bye')


if __name__ == '__main__':
    rtk = Rtk()
    rtk.main()
