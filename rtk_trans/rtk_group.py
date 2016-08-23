#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_group.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 管理一组差分
# 

import threading
from multiprocessing import Process, Queue, queues
from rtk_trans.rtk_thread import RtkThread
from rtk_trans.http_thread import RtkStatus
from rtk_trans import log


class RtkGroup(threading.Thread):
    def __init__(self, name, thread_id, config):
        """初始化

        Args:
            name: rtk 线程名
            thread_id: 线程 id
            config: 配置 dict
        """
        super().__init__()
        self.name = name
        self.thread_id = thread_id
        self.config = config
        self.running = True

    def run(self):
        queue_in = Queue()
        queue_out = Queue()
        p = Process(target=process_main, args=(queue_in, queue_out, self.name, self.config))
        p.start()

        # wait
        while self.running:
            try:
                name = queue_out.get(timeout=1)
                RtkStatus.update_rcv_time(name)
            except queues.Empty:
                pass
        queue_in.put(False)
        p.join()
        RtkStatus.update_status(self.name, RtkStatus.S_TERMINATED)


def process_main(queue_in, queue_out, name, config):
    """进程主函数"""
    enable_log = config['enableLog'].lower() == 'true'
    log.init(name, enable_log)

    rtk_thread = RtkThread(name, config, lambda data: queue_out.put(name))
    rtk_thread.start()

    while True:
        try:
            running = queue_in.get(timeout=1)
            if not running:
                break
        except queues.Empty:
            pass
    rtk_thread.running = False
    rtk_thread.join()

    log.close()
