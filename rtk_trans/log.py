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


class Log:
    def __init__(self, name, to_file=True):
        """初始化日志系统

        使用本模块中的其他方法之前必须调用本方法。

        Args:
            name: log 名字
            to_file: 写入到文件系统 (default True)
        """

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # to file
        self.fh = None
        if to_file:
            log_path = str(os.path.join(log_dir, '%s.log' % name))
            fh = logging.handlers.RotatingFileHandler(log_path, maxBytes=524288000, backupCount=10)
            fh.setLevel(logging.DEBUG)
            fh.doRollover()
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            self.fh = fh

        # to screen
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        self.ch = ch
        self.logger = logger
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

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def log(self, lvl, msg, *args, **kwargs):
        self.logger.log(lvl, msg, *args, **kwargs)
