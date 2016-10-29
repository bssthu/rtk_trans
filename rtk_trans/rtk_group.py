#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_group.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 管理一组差分
# 

from multiprocessing import Process, Event

from rtk_trans.rtk_thread import RtkThread
from rtk_utils import log
from rtk_utils.http_thread import RtkStatus


class RtkGroup:
    def __init__(self, name, thread_id, config, status_queue):
        """初始化

        Args:
            name (str): rtk 线程名
            thread_id (int): 线程 id
            config (dict): 配置表
            status_queue (multiprocessing.Queue): 更新差分状态的队列
        """
        self.name = name
        self.thread_id = thread_id
        self.config = config
        self.status_queue = status_queue

        self.quit_event = Event()
        self.p = Process(name=self.name, target=process_main,
                         args=(self.quit_event, self.status_queue, self.name, self.config))
        self.p.daemon = True
        self.status_queue.put((self.name, RtkStatus.S_UNKNOWN))

    def start(self):
        if not self.p.is_alive():
            self.run()

    def run(self):
        self.p.start()

    def stop(self):
        # require stop
        self.quit_event.set()

    def join(self):
        self.p.join()
        self.status_queue.put((self.name, RtkStatus.S_TERMINATED))

    def is_alive(self):
        return self.p.is_alive()


def process_main(quit_event, queue_out, name, config):
    """进程主函数

    Args:
        quit_event (multiprocessing.Event): 需要退出的事件
        queue_out (multiprocessing.Queue): 每当收到数据时，将线程名填入此队列
        name (str): 线程名
        config (dict): 配置表
    """
    enable_log = config['enableLog'].lower() == 'true'
    log.init(name, enable_log)

    rtk_thread = RtkThread(name, config, lambda status: queue_out.put((name, status)))
    rtk_thread.start()

    while rtk_thread.running:
        try:
            if quit_event.wait(timeout=3):      # true means event set
                break
        except KeyboardInterrupt:
            pass

    rtk_thread.running = False
    rtk_thread.join()

    log.close(name)
