#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_trans.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : socket 转发数据
# 

import os
import sys
import json
import time
import signal
from rtk_trans import log
from rtk_trans.rtk_thread import RtkThread


class Rtk:
    def __init__(self):
        self.rtk_threads = {}
        self.thread_count = 0
        self.is_interrupt = False

    def exit_by_signal(self, signum, frame):
        """响应 SIGINT"""
        self.is_interrupt = True

    def wait_for_keyboard(self):
        """quit when press q or press ctrl-c, or exception from other threads"""
        try:
            while True:
                print("enter 'q' to quit, 'r' to reload.")
                key = input().lower().strip()
                if key == 'q':
                    break
                elif key == 'r':
                    log.info('main: reload config.')
                    self.start_threads_from_config()
        except KeyboardInterrupt:
            pass
        except EOFError:
            # no input
            signal.signal(signal.SIGINT, self.exit_by_signal)
            while not self.is_interrupt:
                time.sleep(1)

    def start_threads_from_config(self):
        """读取配置文件，启动所有 rtk 线程"""
        # config
        config_file_name = os.path.join(sys.path[0], 'conf/config.json')
        try:
            with open(config_file_name) as config_fp:
                configs = json.load(config_fp)
        except Exception as e:
            log.error('main: failed to load config from conf/config.json: %s' % e)
            return

        # threads
        if 'entry' in configs.keys():
            entries = configs['entry']
            if isinstance(entries, dict):
                for name, config in entries.items():
                    # start one thread
                    try:
                        if name in self.rtk_threads.keys():
                            rtk_thread = self.rtk_threads[name]
                            # 判断配置是否发生改变，如果不变就跳过
                            if rtk_thread.config_equals(config):
                                continue
                            self.stop_and_wait_for_thread(name)
                        rtk_thread = RtkThread(name, self.thread_count, config)
                        self.thread_count += 1
                        rtk_thread.start()
                        self.rtk_threads[name] = rtk_thread
                    except Exception as e:
                        log.error('main: failed to start thread %s: %s' % (name, e))

    def stop_thread(self, name):
        """停止某 rtk 线程，不等待

        之后需要调用 wait_for_thread

        Args:
            name: rtk 线程名
        """
        try:
            if name in self.rtk_threads.keys():
                rtk_thread = self.rtk_threads[name]
                if isinstance(rtk_thread, RtkThread) and rtk_thread.is_alive():
                    rtk_thread.running = False
                    log.info('main: require stop thread %d %s.' % (rtk_thread.thread_id, name))
        except Exception as e:
            log.error('main: failed to stop thread %s: %s' % (name, e))

    def wait_for_thread(self, name):
        """等待某 rtk 线程完全退出

        在 stop_thread 之后调用

        Args:
            name: rtk 线程名
        """
        try:
            if name in self.rtk_threads.keys():
                rtk_thread = self.rtk_threads[name]
                if isinstance(rtk_thread, RtkThread) and rtk_thread.is_alive():
                    # wait
                    rtk_thread.join()
                log.info('main: thread %d %s has stopped.' % (rtk_thread.thread_id, name))
                # remove
                del self.rtk_threads[name]
        except Exception as e:
            log.error('main: error when wait for thread %s: %s' % (name, e))

    def stop_and_wait_for_thread(self, name):
        """停止某 rtk 线程，等待直到退出成功

        Args:
            name: rtk 线程名
        """
        self.stop_thread(name)
        self.wait_for_thread(name)

    def main(self):
        # log init
        log.initialize_logging(True)
        log.info('main: start')

        # start rtk
        self.start_threads_from_config()

        # wait
        self.wait_for_keyboard()

        # quit & clean up
        for name in self.rtk_threads.keys():
            self.stop_thread(name)
        for name in sorted(self.rtk_threads.keys()):
            self.wait_for_thread(name)
        log.info('main: bye')
