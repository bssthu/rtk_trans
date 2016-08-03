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
import rtk_trans.http_thread
from rtk_trans.http_thread import HttpThread


class Rtk:
    def __init__(self):
        self.rtk_threads = {}
        self.thread_count = 0
        self.web_interface_thread = None
        self.is_interrupt = False
        # log init
        self.log = log.Log('rtk', True)
        rtk_trans.http_thread.log = log.Log('web', True)

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
                    self.log.info('main: reload config.')
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
            self.log.error('main: failed to load config from conf/config.json: %s' % e)
            return

        # rtk 转发服务
        try:
            if 'entry' in configs.keys():
                self.start_rtk_threads(configs['entry'])
        except Exception as e:
            self.log.error('main: failed to start rtk threads: %s' % e)
        # web 管理界面
        try:
            if configs['webInterface']['allow'].lower() == 'true':
                self.start_web_interface(configs['webInterface']['port'], sorted(configs['entry'].keys()))
        except Exception as e:
            self.log.error('main: failed to start web interface: %s' % e)

    def start_rtk_threads(self, entries):
        """停止某 rtk 线程，不等待

        之后需要调用 wait_for_thread

        Args:
            entries: 各组 rtk 转发配置
        """
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
                    self.log.error('main: failed to start thread %s: %s' % (name, e))

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
                    self.log.info('main: require stop thread %d %s.' % (rtk_thread.thread_id, name))
        except Exception as e:
            self.log.error('main: failed to stop thread %s: %s' % (name, e))

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
                self.log.info('main: thread %d %s has stopped.' % (rtk_thread.thread_id, name))
                # remove
                del self.rtk_threads[name]
        except Exception as e:
            self.log.error('main: error when wait for thread %s: %s' % (name, e))

    def stop_and_wait_for_thread(self, name):
        """停止某 rtk 线程，等待直到退出成功

        Args:
            name: rtk 线程名
        """
        self.stop_thread(name)
        self.wait_for_thread(name)

    def start_web_interface(self, port, rtk_names):
        """启动 web 管理服务器

        Args:
            port: web 服务器端口号
            rtk_names: 开启的 rtk 服务名
        """
        # stop old
        self.stop_and_wait_for_web_interface()
        # start new
        self.web_interface_thread = HttpThread(port, rtk_names)
        self.web_interface_thread.start()

    def stop_and_wait_for_web_interface(self):
        """关闭 web 管理服务器"""
        if isinstance(self.web_interface_thread, HttpThread) and self.web_interface_thread.is_alive():
            self.web_interface_thread.shutdown()
            self.web_interface_thread.join()

    def main(self):
        self.log.info('main: start')

        # start rtk
        self.start_threads_from_config()

        # wait
        self.wait_for_keyboard()

        # quit & clean up
        for name in self.rtk_threads.keys():
            self.stop_thread(name)
        for name in sorted(self.rtk_threads.keys()):
            self.wait_for_thread(name)
        self.stop_and_wait_for_web_interface()

        self.log.info('main: bye')
        self.log.close()
        rtk_trans.http_thread.log.close()
