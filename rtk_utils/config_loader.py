#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : config_loader.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
#

import json
import os
import sys

from rtk_utils import log


def load_config():
    """载入配置文件

    先读入 conf/config.json 中的配置，再读入 conf/ 中其他 json 文件里的 entry
    """
    config_dir = os.path.join(sys.path[0], 'conf')
    configs = {}
    # main config
    config_file_name = os.path.join(config_dir, 'config.json')
    try:
        with open(config_file_name) as config_fp:
            configs = json.load(config_fp)
    except Exception as e:
        log.error('main: failed to load config from conf/config.json: %s' % e)
    if 'entry' not in configs.keys():
        configs['entry'] = {}

    # other entries
    for dir_path, dir_names, file_names in os.walk(config_dir):
        for file_name in file_names:
            if file_name != 'config.json' and file_name.endswith('.json'):
                # load sub config
                config_file_name = os.path.join(config_dir, file_name)
                try:
                    with open(config_file_name) as config_fp:
                        sub_configs = json.load(config_fp)
                    # insert into main config
                    for name, config in sorted(sub_configs['entry'].items()):
                        if name not in configs['entry'].keys():
                            configs['entry'][name] = config
                except Exception as e:
                    log.error('main: failed to load config from conf/%s: %s' % (file_name, e))

    return configs
