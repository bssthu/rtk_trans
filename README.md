# rtk_trans
直接转发

## Intro
每一组 rtk_trans 通过 socket 连接到一台上层服务器并接收、解析数据。
同时，监听来自若干下层客户端的连接，
并将数据转发到下层客户端。

## Setup
```bash
cp ./docs/config.json.default ./conf/config.json
```
并按需修改配置文件`conf/config.json`。

## Usage
- 启动方法
```bash
python3 rtk.py
# or
./start.sh
```

按'r'+回车重新加载配置。
按'q'+回车或Ctrl+c退出程序。

通过 socket 发送命令到 `controlPort` 端口，命令格式为 `*#*#command#*#*`。

- `reset server` 关闭所有连到 rtk_trans 的客户 socket
- `list` 查询

## 其他说明
* [主要模块](docs/modules.md)

## License
All rights reserved.
