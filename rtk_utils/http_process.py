#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : http_process.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

from multiprocessing import Process, Event, queues

from rtk_utils.http_thread import HttpThread, RtkStatus
from rtk_utils import log

PROCESS_NAME = 'http'


class HttpProcess:
    """http 服务器，多进程封装"""

    def __init__(self, http_port, rtk_names, status_queue):
        """构造函数

        Args:
            http_port (int): web 服务器端口号, None 表示不开启
            rtk_names (list[str]): 开启的 rtk 服务名
            status_queue (multiprocessing.Queue): 差分状态队列
        """
        self.port = http_port
        self.rtk_names = rtk_names
        self.status_queue = status_queue

        self.quit_event = Event()
        self.p = Process(name=PROCESS_NAME, target=process_http,
                         args=(self.quit_event, self.status_queue, self.port, self.rtk_names))

    def start(self):
        self.run()

    def run(self):
        if not self.p.is_alive():
            self.p.start()

    def stop(self):
        # require stop
        self.quit_event.set()

    def join(self):
        self.p.join()

    def update_status(self, name, status):
        """更新 rtk 状态

        Args:
            name (str): rtk 服务名
            status (str): 服务当前状态, None 表示只 update_rcv_time
        """
        self.status_queue.put((name, status))


def process_http(quit_event, rtk_status_queue, http_port, rtk_names):
    """HTTP 进程主函数

    Args:
        quit_event (multiprocessing.Event): 需要退出的事件
        rtk_status_queue (multiprocessing.Queue): 更新状态的队列
        http_port (int): web 服务器端口号
        rtk_names (list[str]): 开启的 rtk 服务名
    """
    if http_port is not None:
        log.init(PROCESS_NAME)

    # start
    http_thread = HttpThread(http_port, rtk_names)

    if http_port is not None:
        http_thread.start()

    # loop
    try:
        while not quit_event.is_set():
            quit_event.wait(timeout=1)
            update_from_queue(rtk_status_queue,
                              lambda name_status: RtkStatus.update_status(name_status[0], name_status[1]))
    except KeyboardInterrupt:
        pass

    # quit
    if http_port is not None:
        http_thread.shutdown()
        http_thread.join()

    log.close(PROCESS_NAME)


def update_from_queue(q, cb):
    """从队列中取出数据并依次执行操作

    Args:
        q (multiprocessing.Queue): 队列
        cb (Callable[[str], None]): 回调函数
    """
    try:
        while not q.empty():
            data = q.get(block=False)
            cb(data)
    except queues.Empty:
        pass
