#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : log.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : socket 转发数据
# 

import os
import logging
from logging import handlers

log_dir = 'logs'
logger = None


class Log:
    def __init__(self, name, to_file):
        """初始化日志系统

        使用本模块中的其他方法之前必须调用本方法。

        Args:
            name: log 名字
            to_file: 写入到文件系统 (default True)
        """

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # to file
        self.fh = None
        if to_file:
            log_path = str(os.path.join(log_dir, '%s.log' % name))
            fh = logging.handlers.RotatingFileHandler(log_path, maxBytes=524288000, backupCount=10)
            fh.setLevel(logging.DEBUG)
            fh.doRollover()
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            self.fh = fh

        # to screen
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.ch = ch
        self.logging = True

    def close(self):
        """关闭日志"""
        if self.logging:
            self.logger.removeHandler(self.fh)
            self.logger.removeHandler(self.ch)
            if self.fh is not None:
                self.fh.close()
            self.ch.close()
            self.logging = False


def init(name, to_file=True):
    global logger
    if logger is None:
        logger = Log(name, to_file)


def close():
    global logger
    if logger is not None:
        logger.close()
        logger = None


def debug(msg, *args, **kwargs):
    logger.logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    logger.logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    logger.logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    logger.logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    logger.logger.critical(msg, *args, **kwargs)


def log(lvl, msg, *args, **kwargs):
    logger.logger.log(lvl, msg, *args, **kwargs)
