#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_trans.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : socket 转发数据
# 

import json
import multiprocessing
from multiprocessing import Queue
import os
import signal
import sys
import time

from rtk_trans.rtk_group import RtkGroup
from rtk_utils import log
from rtk_utils.http_process import HttpProcess


class Rtk:
    def __init__(self):
        self.rtk_threads = {}
        self.thread_count = 0
        self.web_interface_thread = None
        self.is_interrupt = False
        self.status_queue = Queue()
        # log init
        self.configs = self.load_config()
        if 'logPath' in self.configs.keys() and os.path.isdir(self.configs['logPath']):
            log.log_dir = self.configs['logPath']
        multiprocessing.current_process().name = 'rtk'
        log.init(multiprocessing.current_process().name, True)

    def exit_by_signal(self, signum, frame):
        """响应 SIGINT, SIGTERM"""
        self.is_interrupt = True

    def wait_for_keyboard(self):
        """quit when press q or press ctrl-c, or exception from other threads"""
        try:
            while True:
                print("enter 'q' to quit, 'r' to reload, 'l' to list ports.")
                key = input().lower().strip()
                if key == 'q':
                    break
                elif key == 'r':
                    log.info('main: reload config.')
                    self.start_threads_from_config()
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

    def update_status_cb(self, name, status):
        """更新 rtk 状态

        Args:
            name: rtk 服务名
            status: 服务当前状态, None 表示只 update_rcv_time
        """
        self.status_queue.put((name, status))

    def start_threads_from_config(self):
        """读取配置文件，启动所有 rtk 线程"""
        # config
        configs = self.load_config()
        self.configs = configs

        # rtk 转发服务
        try:
            if 'entry' in configs.keys():
                self.start_rtk_threads(configs['entry'])
        except Exception as e:
            log.error('main: failed to start rtk threads: %s' % e)
        # web 管理界面
        try:
            port = configs['webInterface']['port']
            if configs['webInterface']['allow'].lower() != 'true':
                port = None
            self.start_web_interface(port, sorted(configs['entry'].keys()))
        except Exception as e:
            log.error('main: failed to start web interface: %s' % e)

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
                        if rtk_thread.config == config:
                            continue
                        self.stop_and_wait_for_thread(name)
                    rtk_thread = RtkGroup(name, self.thread_count, config, self.status_queue)
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
                if isinstance(rtk_thread, RtkGroup):
                    rtk_thread.stop()
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
        self.web_interface_thread = HttpProcess(port, rtk_names, self.status_queue)
        self.web_interface_thread.start()

    def stop_and_wait_for_web_interface(self):
        """关闭 web 管理服务器"""
        if isinstance(self.web_interface_thread, HttpProcess):
            self.web_interface_thread.stop()
            self.web_interface_thread.join()
        self.web_interface_thread = None

    def load_config(self):
        """载入配置文件

        先读入 conf/config.json 中的配置，再读入 conf/ 中其他 json 文件里的 entry
        """
        config_dir = os.path.join(sys.path[0], 'conf')
        configs = {}
        # main config
        config_file_name = os.path.join(config_dir, 'config.json')
        try:
            with open(config_file_name) as config_fp:
                configs = json.load(config_fp)
        except Exception as e:
            log.error('main: failed to load config from conf/config.json: %s' % e)
        if 'entry' not in configs.keys():
            configs['entry'] = {}

        # other entries
        for dir_path, dir_names, file_names in os.walk(config_dir):
            for file_name in file_names:
                if file_name != 'config.json' and file_name.endswith('.json'):
                    # load sub config
                    config_file_name = os.path.join(config_dir, file_name)
                    try:
                        with open(config_file_name) as config_fp:
                            sub_configs = json.load(config_fp)
                        # insert into main config
                        for name, config in sorted(sub_configs['entry'].items()):
                            if name not in configs['entry'].keys():
                                configs['entry'][name] = config
                    except Exception as e:
                        log.error('main: failed to load config from conf/%s: %s' % (file_name, e))

        return configs

    def main(self):
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
        self.stop_and_wait_for_web_interface()

        # clear queue
        while not self.status_queue.empty():
            self.status_queue.get(block=False)

        log.info('main: bye')
        log.close_all()
