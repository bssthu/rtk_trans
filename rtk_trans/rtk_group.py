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
            name: rtk 线程名
            thread_id: 线程 id
            config: 配置 dict
            status_queue: 更新差分状态的队列
        """
        self.name = name
        self.thread_id = thread_id
        self.config = config
        self.status_queue = status_queue

        self.quit_event = Event()
        self.p = Process(name=self.name, target=process_main,
                         args=(self.quit_event, self.status_queue, self.name, self.config))
        self.p.daemon = True

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


def process_main(quit_event, queue_out, name, config):
    """进程主函数

    Args:
        quit_event: 需要退出的事件
        queue_out: 每当收到数据时，将线程名填入此队列
        name: 线程名
        config: 配置 dict
    """
    enable_log = config['enableLog'].lower() == 'true'
    log.init(name, enable_log)

    rtk_thread = RtkThread(name, config, lambda status: queue_out.put((name, status)))
    rtk_thread.start()

    try:
        quit_event.wait()
    except KeyboardInterrupt:
        pass

    rtk_thread.running = False
    rtk_thread.join()

    log.close(name)
