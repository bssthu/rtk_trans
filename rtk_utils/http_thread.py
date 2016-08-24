#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : http_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import datetime
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from rtk_utils import log


class HttpThread(threading.Thread):
    """http 服务器，web 管理"""

    def __init__(self, http_port, rtk_names):
        """构造函数

        Args:
            http_port: web 服务器端口号
            rtk_names: 开启的 rtk 服务名
        """
        super().__init__()
        self.port = http_port
        self.update_names(rtk_names)

        self.server = None

    def update_names(self, rtk_names):
        """更新 rtk 状态查询的名字表

        Args:
            rtk_names: 开启的 rtk 服务名
        """
        log.info('http thread: load %d name(s)' % len(rtk_names))
        RtkStatus.update_names(rtk_names)

    def run(self):
        """线程主函数

        启动定时器，用于检查心跳超时
        循环运行，接受新的客户端的连接。
        """
        log.info('http thread: start, port: %d' % self.port)

        try:
            self.server = ThreadingHTTPServer(('', self.port), RequestHandler)
            self.server.serve_forever()
        except Exception as e:
            log.error('http thread error: %s' % e)

        time.sleep(0.5)
        log.info('http thread: bye')

    def shutdown(self):
        """退出"""
        if self.server is not None:
            self.server.shutdown()


class RtkStatus:
    """rtk 服务状态管理"""
    rtk_last_rcv_time = {}
    rtk_status = {}

    S_UNKNOWN = 'unknown'
    S_CONNECTED = 'online'
    S_RECEIVING = 'receiving'
    S_DISCONNECTED = 'offline'
    S_TERMINATED = 'terminated'

    def update_names(names):
        """更新 rtk 服务列表

        Args:
            names: 开启的 rtk 服务名
        """
        RtkStatus.rtk_last_rcv_time = {name: 'NULL' for name in names}
        RtkStatus.rtk_status = {name: RtkStatus.S_UNKNOWN for name in names}

    def update_rcv_time(name):
        """接收到 rtk 数据，更新时间戳

        Args:
            name: rtk 服务名
        """
        try:
            # 此处可能不是很线程安全
            if name in RtkStatus.rtk_last_rcv_time.keys():
                RtkStatus.rtk_last_rcv_time[name] = get_time_string()
                RtkStatus.update_status(name, RtkStatus.S_RECEIVING)
        except Exception as e:
            log.warning('Failed when update rcv time: %s' % e)

    def update_status(name, status):
        """接收到 rtk 状态更新

        Args:
            name: rtk 服务名
            status: 服务当前状态, None 表示只 update_rcv_time
        """
        if status is None:
            RtkStatus.update_rcv_time(name)
        else:
            try:
                if name in RtkStatus.rtk_status.keys():
                    RtkStatus.rtk_status[name] = status
            except Exception as e:
                log.warning('Failed when update status: %s' % e)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理"""

    def __init__(self, request, client_address, server):
        """设置超时"""
        self.timeout = 20
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        try:
            self.send_response(200, message=None)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            # header
            self.wfile.write(b'<html><head>')
            self.wfile.write(b'<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />')
            self.wfile.write(b'</head><body>')
            self.wfile.write(('<div>server time: %s</div>' % get_time_string()).encode())
            self.wfile.write(b'<div>...</div>')
            # body
            self.wfile.write(b'<div>possible status: unknown, online, receiving, offline, terminated.</div>')
            self.wfile.write(b'<div>rtk server(s):</div>')
            self.wfile.write(b'<div>...</div>')
            rtk_last_rcv_time = RtkStatus.rtk_last_rcv_time.copy()
            rtk_status = RtkStatus.rtk_status.copy()
            for name, timestamp in sorted(rtk_last_rcv_time.items()):
                if name in rtk_status.keys():
                    self.wfile.write(('<div class="rtk_status">%s, %s, %s</div>'
                                      % (name, rtk_status[name], timestamp)).encode())
            self.wfile.write(b'<div>...</div>')
            self.wfile.write(b'</body></html>')
        except IOError:
            self.send_error(404, message=None)

    def do_POST(self):
        pass

    def log_request(self, code='-', size='-'):
        """覆盖基类方法，不输出到屏幕

        This is called by send_response().

        Args:
            code: 状态码
            size:
        """
        log.debug('%s - - "%s" %s %s' % (self.address_string(), self.requestline, str(code), str(size)))

    def log_error(self, format, *args):
        """覆盖基类方法，不输出到屏幕"""
        log.debug('%s - - %s' % (self.address_string(), format % args))


def get_time_string(timestamp=None):
    if timestamp is None:
        timestamp = datetime.datetime.now()
    return timestamp.strftime('%Y-%m-%d, %H:%M:%S')
