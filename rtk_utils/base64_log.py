#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : base64_log.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import base64
import os
import multiprocessing
import logging
from logging import handlers

log_dir = 'logs/raw'
loggers = {}


class Base64Log:
    def __init__(self, name, to_file):
        """初始化 bytes 日志系统

        使用本模块中的其他方法之前必须调用本方法。

        Args:
            name (str): log 名字
            to_file (bool): 写入到文件系统 (default True)
        """

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(message)s')

        # to file
        self.fh = None
        if to_file:
            log_path = str(os.path.join(log_dir, '%s.log' % name))
            fh = logging.handlers.RotatingFileHandler(log_path, maxBytes=104857600, backupCount=5)
            fh.setLevel(logging.DEBUG)
            fh.doRollover()
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            self.fh = fh
        self.logging = True

    def close(self):
        """关闭日志"""
        if self.logging:
            self.logger.removeHandler(self.fh)
            if self.fh is not None:
                self.fh.close()
            self.logging = False


def init(name, to_file=True):
    """实例化一个日志工具"""
    global loggers
    if name not in loggers.keys():
        logger = Base64Log(name, to_file)
        loggers[name] = logger


def close(name):
    """关闭一个日志工具"""
    global loggers
    if name in loggers.keys():
        loggers[name].close()
        del loggers[name]


def close_all():
    """关闭所有日志工具"""
    global loggers
    for name in loggers.copy().keys():
        close(name)


def raw(buf, *args, **kwargs):
    """以 base64 形式记录"""
    name = multiprocessing.current_process().name + '_raw'
    global loggers
    if name in loggers.keys():
        msg = base64.b64encode(buf).decode('utf-8')
        loggers[name].logger.log(logging.DEBUG, msg, *args, **kwargs)
