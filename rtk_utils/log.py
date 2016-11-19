#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : log.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import os
import multiprocessing
import logging
from logging import handlers, LogRecord, getLevelName

log_dir = 'logs'
loggers = {}

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
COLORS = {
    'DEBUG': GREEN,
    'INFO': GREEN,
    'WARNING': YELLOW,
    'ERROR': RED,
    'CRITICAL': RED
}


class ColoredLogRecord(LogRecord):
    """增加 colorlevelname 一项"""
    def __init__(self, name, level, pathname, lineno,
                 msg, args, exc_info, func=None, sinfo=None, **kwargs):
        super().__init__(name, level, pathname, lineno,
                         msg, args, exc_info, func, sinfo, **kwargs)
        self.colorlevelname = get_color_level_name(level)


def get_color_level_name(level):
    level_name = getLevelName(level)
    if level_name in COLORS:
        return '\033[1;%dm%s\033[0m' % (30 + COLORS[level_name], level_name)
    else:
        return level_name


class Log:
    def __init__(self, name, to_file):
        """初始化日志系统

        使用本模块中的其他方法之前必须调用本方法。

        Args:
            name (str): log 名字
            to_file (bool): 写入到文件系统 (default True)
        """

        logging.setLogRecordFactory(ColoredLogRecord)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        color_formatter = logging.Formatter('%(asctime)s - %(name)s - %(colorlevelname)s - %(message)s')

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
        ch.setFormatter(color_formatter)
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
    """实例化一个日志工具"""
    global loggers
    if name not in loggers.keys():
        logger = Log(name, to_file)
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


def debug(msg, *args, **kwargs):
    log(logging.DEBUG, msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    log(logging.INFO, msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    log(logging.WARNING, msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    log(logging.ERROR, msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    log(logging.CRITICAL, msg, *args, **kwargs)


def log(lvl, msg, *args, **kwargs):
    name = multiprocessing.current_process().name
    global loggers
    if name in loggers.keys():
        loggers[name].logger.log(lvl, msg, *args, **kwargs)
