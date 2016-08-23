#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_group.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 管理一组差分
# 

import threading
import time
from multiprocessing import Process, Queue, queues
from rtk_trans.rtk_thread import RtkThread


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
        self.log = None

    def run(self):
        state_queue = Queue()
        p = Process(target=process_main, args=(state_queue, self.name, self.config))
        p.start()

        # wait
        while self.running:
            time.sleep(2)
        state_queue.put(False)
        p.join()


def process_main(state_queue, name, config):
    rtk_thread = RtkThread(name, config)
    rtk_thread.start()

    while True:
        try:
            running = state_queue.get(timeout=1)
            if not running:
                break
        except queues.Empty:
            pass
    rtk_thread.running = False
    rtk_thread.join()
