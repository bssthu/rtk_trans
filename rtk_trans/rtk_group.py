#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : rtk_group.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 管理一组差分
# 

from multiprocessing import Process, Event, Queue, queues
from rtk_trans.rtk_thread import RtkThread
from rtk_utils import log
from rtk_utils.http_thread import RtkStatus


class RtkGroup:
    def __init__(self, name, thread_id, config, update_status_cb):
        """初始化

        Args:
            name: rtk 线程名
            thread_id: 线程 id
            config: 配置 dict
            update_status_cb: 更新差分状态的回调函数
        """
        self.name = name
        self.thread_id = thread_id
        self.config = config
        self.update_status_cb = update_status_cb

        self.quit_event = Event()
        self.queue_out = Queue()
        self.p = Process(name=self.name, target=process_main,
                    args=(self.quit_event, self.queue_out, self.name, self.config))

    def start(self):
        self.run()

    def run(self):
        self.p.start()

        # # wait
        # while self.running and p.is_alive():
        #     try:
        #         while not queue_out.empty():
        #             status = queue_out.get(block=False)
        #             self.update_status_cb(self.name, status)
        #         p.join(timeout=1)
        #     except queues.Empty:
        #         pass

    def stop(self):
        # require stop
        self.quit_event.set()

    def join(self):
        self.p.join()
        # clear queue
        while not self.queue_out.empty():
            self.queue_out.get(block=False)
        self.update_status_cb(self.name, RtkStatus.S_TERMINATED)


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

    rtk_thread = RtkThread(name, config, lambda status: queue_out.put(status))
    rtk_thread.start()

    try:
        quit_event.wait()
    except KeyboardInterrupt:
        pass

    rtk_thread.running = False
    rtk_thread.join()

    log.close(name)
