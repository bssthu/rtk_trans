#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : http_process.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import threading
from multiprocessing import Process, Event, Queue, queues
from rtk_utils.http_thread import HttpThread, RtkStatus
from rtk_utils import log

PROCESS_NAME = 'http'


class HttpProcess(threading.Thread):
    """http 服务器，多进程封装"""

    def __init__(self, http_port, rtk_names):
        """构造函数

        Args:
            http_port: web 服务器端口号
            rtk_names: 开启的 rtk 服务名
        """
        super().__init__()
        self.port = http_port
        self.rtk_names = rtk_names
        self.rtk_status_queue = Queue()
        self.running = True

    def run(self):
        quit_event = Event()
        p = Process(name=PROCESS_NAME, target=process_http,
                    args=(quit_event, self.rtk_status_queue, self.port, self.rtk_names))
        p.start()

        # wait
        while self.running and p.is_alive():
            p.join(timeout=1)
        # require stop
        quit_event.set()
        p.join()

    def update_status(self, name, status):
        """更新 rtk 状态

        Args:
            name: rtk 服务名
            status: 服务当前状态, None 表示只 update_rcv_time
        """
        self.rtk_status_queue.put((name, status))


def process_http(quit_event, rtk_status_queue, http_port, rtk_names):
    """HTTP 进程主函数

    Args:
        quit_event: 需要退出的事件
        rtk_status_queue: 更新状态的队列
        http_port: web 服务器端口号
        rtk_names: 开启的 rtk 服务名
    """
    log.init(PROCESS_NAME)

    # start
    http_thread = HttpThread(http_port, rtk_names)
    http_thread.start()

    # loop
    while not quit_event.is_set():
        quit_event.wait(timeout=1)
        update_from_queue(rtk_status_queue,
                          lambda name_status: RtkStatus.update_status(name_status[0], name_status[1]))

    # quit
    http_thread.shutdown()
    http_thread.join()

    log.close(PROCESS_NAME)


def update_from_queue(q, cb):
    """从队列中取出数据并依次执行操作

    Args:
        <multiprocessing.Queue> q: 队列
        cb: 回调函数
    """
    try:
        while not q.empty():
            data = q.get(block=False)
            cb(data)
    except queues.Empty:
        pass
