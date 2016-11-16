#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_trans.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : socket 转发数据
# 

import multiprocessing
import os
import signal
import time

from rtk_trans.rtk_process_mgr import RtkProcessMgr
from rtk_utils import log
from rtk_utils import config_loader


class Rtk:
    def __init__(self):
        self.is_interrupt = False

        # config
        self.configs = config_loader.load_config()
        if 'logPath' in self.configs.keys() and os.path.isdir(self.configs['logPath']):
            log.log_dir = self.configs['logPath']

        self.rtk_mgr = RtkProcessMgr(self.configs)

        # log init
        multiprocessing.current_process().name = 'rtk'
        log.init(multiprocessing.current_process().name, True)

    def exit_by_signal(self, signum, frame):
        """响应 SIGINT, SIGTERM"""
        self.is_interrupt = True

    def wait_for_keyboard(self):
        """quit when press q or press ctrl-c, or exception from other threads"""
        try:
            while True:
                time.sleep(2)   # 减少死锁概率
                print("enter 'q' to quit, 'r' to reload, 'l' to list ports.")
                key = input().lower().strip()
                if key == 'q':
                    break
                elif key == 'r':
                    log.info('main: reload config.')
                    configs = config_loader.load_config()
                    self.configs = configs
                    self.rtk_mgr.start_threads_from_config(self.configs)
                elif key == 'l':
                    try:
                        print('name, station_port, dispatch_port, control_port')
                        for name, config in sorted(self.configs['entry'].items()):
                            control_port = str(config['controlPort']) if 'controlPort' in config else None
                            print('%s, %d, %d, %s'
                                  % (name, config['stationPort'], config['listenPort'], control_port))
                    except Exception as e:
                        print('Error when list config: %s' % e)
        except KeyboardInterrupt:
            pass
        except (EOFError, OSError):
            # no input
            signal.signal(signal.SIGINT, self.exit_by_signal)
            signal.signal(signal.SIGTERM, self.exit_by_signal)
            while not self.is_interrupt:
                time.sleep(1)

    def main(self):
        log.info('main: start')

        # start rtk & loop
        self.rtk_mgr.start()

        # wait
        self.wait_for_keyboard()

        # quit & clean up
        self.rtk_mgr.running = False
        self.rtk_mgr.join()

        log.info('main: bye')
        log.close_all()
