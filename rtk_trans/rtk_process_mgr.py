#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_process_mgr.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import multiprocessing
import threading
import time

from rtk_trans.rtk_group import RtkGroup
from rtk_utils import log
from rtk_utils.http_process import HttpProcess


class RtkProcessMgr(threading.Thread):
    def __init__(self, configs):
        super().__init__()
        self.init_configs = configs
        self.rtk_threads = {}
        self.thread_count = 0
        self.web_interface_thread = None
        self.rtk_names_queue = multiprocessing.Queue()
        self.status_queue = multiprocessing.Queue()
        self.running = True

    def start_threads_from_config(self, configs):
        """读取配置文件，启动所有 rtk 线程"""

        # web 管理界面
        try:
            port = configs['webInterface']['port']
            if configs['webInterface']['allow'].lower() == 'true':
                self.start_web_interface(port)
        except Exception as e:
            log.error('main: failed to start web interface: %s' % e)
        # rtk 转发服务
        try:
            if 'entry' in configs.keys():
                self.start_rtk_threads(configs['entry'])
        except Exception as e:
            log.error('main: failed to start rtk threads: %s' % e)
        # web 管理界面的配置
        try:
            if configs['webInterface']['allow'].lower() == 'true':
                self.update_web_interface(sorted(configs['entry'].keys()))
        except Exception as e:
            log.error('main: failed to update web interface: %s' % e)

    def start_rtk_threads(self, entries):
        """根据配置文件启动 rtk 线程

        Args:
            entries (dict[str, dict]): 各组 rtk 转发配置
        """
        if isinstance(entries, dict):
            # stop threads not in config
            for name in sorted(self.rtk_threads.keys()):
                if name not in entries.keys():
                    self.stop_and_wait_for_thread(name)
            # start threads from config
            for name, config in entries.items():
                # start one thread
                try:
                    if name in self.rtk_threads.keys():
                        # 如果已有
                        rtk_group = self.rtk_threads[name]
                        # 判断配置是否发生改变，如果不变并且在运行，就跳过
                        if rtk_group.is_alive() and rtk_group.config == config:
                            continue
                        self.stop_and_wait_for_thread(name)
                    rtk_group = RtkGroup(name, self.thread_count, config, self.status_queue)
                    self.thread_count += 1
                    rtk_group.start()
                    self.rtk_threads[name] = rtk_group
                except Exception as e:
                    log.error('main: failed to start thread %s: %s' % (name, e))

    def stop_thread(self, name):
        """停止某 rtk 线程，不等待

        之后需要调用 wait_for_thread

        Args:
            name (str): rtk 线程名
        """
        try:
            if name in self.rtk_threads.keys():
                rtk_thread = self.rtk_threads[name]
                if isinstance(rtk_thread, RtkGroup):
                    rtk_thread.stop()
                    log.info('main: require stop thread %d %s.' % (rtk_thread.thread_id, name))
        except Exception as e:
            log.error('main: failed to stop thread %s: %s' % (name, e))

    def wait_for_thread(self, name):
        """等待某 rtk 线程完全退出

        在 stop_thread 之后调用

        Args:
            name (str): rtk 线程名
        """
        try:
            if name in self.rtk_threads.keys():
                rtk_thread = self.rtk_threads[name]
                if isinstance(rtk_thread, RtkGroup):
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
            name (str): rtk 线程名
        """
        self.stop_thread(name)
        self.wait_for_thread(name)

    def start_web_interface(self, port):
        """启动 web 管理服务器

        Args:
            port (int): web 服务器端口号
        """
        if self.web_interface_thread is None:
            # start new
            self.web_interface_thread = HttpProcess(port, self.rtk_names_queue, self.status_queue)
            self.web_interface_thread.start()

    def update_web_interface(self, rtk_names):
        """更新 web 管理服务器的配置

        Args:
            rtk_names (list[str]): 开启的 rtk 服务名
        """
        if self.web_interface_thread is not None:
            self.web_interface_thread.update_names(rtk_names)

    def stop_and_wait_for_web_interface(self):
        """关闭 web 管理服务器"""
        if isinstance(self.web_interface_thread, HttpProcess):
            self.web_interface_thread.stop()
            self.web_interface_thread.join()
        self.web_interface_thread = None

    def run(self):
        """线程管理工具的主循环，阻塞运行直到 looping 为 False"""
        # start rtk
        self.start_threads_from_config(self.init_configs)

        # wait
        while self.running:
            time.sleep(1)

        # quit & clean up
        for name in self.rtk_threads.keys():
            self.stop_thread(name)
        for name in sorted(self.rtk_threads.keys()):
            self.wait_for_thread(name)
        self.stop_and_wait_for_web_interface()

        # clear queue
        while not self.status_queue.empty():
            self.status_queue.get(block=False)
