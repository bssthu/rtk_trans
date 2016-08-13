#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : select_protocol.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 编辑本文件，根据 config 决定使用的协议解析工具
#

from rtk_protocol.base_protocol_handler import BaseProtocolHandler


def select_protocol(config):
    """根据配置选择协议解析类"""
    return BaseProtocolHandler(config)
