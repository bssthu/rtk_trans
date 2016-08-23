#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# File          : control_thread.py
# Author        : bssthu
# Project       : rtk_trans
# Description   : 
# 

import socket
import threading
import queue
from rtk_trans import log

BUFFER_SIZE = 4096
CMD_BEGIN = [c for c in b'*#*#']    # 命令起始标记
CMD_END = [c for c in b'#*#*']      # 命令结尾标记


class ControlThread(threading.Thread):
    """从控制端口接收指令的线程"""

    def __init__(self, port, got_command_cb):
        """构造函数

        Args:
            port: 控制端口号, None 表示不启用
            got_command_cb: 接收到指令时调用的回调函数
        """
        super().__init__()
        self.port = port
        self.got_command_cb = got_command_cb
        self.client = None
        self.buffer = []
        self.is_in_command = False
        self.msg_queue = queue.Queue()
        self.is_transparency = False   # 从 controller 透传到 station
        self.running = True
        self.log = None

    def run(self):
        """线程主函数

        循环运行，接受到控制端口的 socket 连接（唯一），接收命令。
        """
        if self.port is None:
            return

        self.log.info('control thread: start, port: %d' % self.port)
        try:
            # 开始监听
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', self.port))
            server.listen(1)
            server.settimeout(3)    # timeout: 3s
            # 循环运行，监听端口，接收命令
            while self.running:
                self.accept_client(server)
                self.receive_command()
                self.resolve_command()
                self.send_message()
            server.close()
            self.disconnect_client()
            self.log.info('control thread: bye')
        except Exception as e:
            self.log.error('control thread error: %s' % e)
            self.running = False

    def accept_client(self, server):
        """监听控制端口

        尝试接受连接，如果有新连接，就关闭旧的连接。

        Args:
            server: server socket
        """
        try:
            conn, address = server.accept()
            self.disconnect_client()
            self.client = conn
            self.client.settimeout(3)
            self.is_transparency = False   # 新连接不透传
            self.log.info('new control client from: %s' % str(address))
        except socket.timeout:
            pass

    def receive_command(self):
        """从控制端口接收数据

        并在发生异常时进行处理。
        """
        if self.client is not None:
            try:
                self.receive_data()
            except socket.timeout:      # 允许超时
                pass
            except Exception as e:
                self.log.error('control client error: %s' % e)
                self.disconnect_client()

    def resolve_command(self):
        """解析来自控制端口的数据

        首先寻找指令起始标记，找不到就从 buffer 头删除一个字节，再继续寻找。
        然后调用 resolve_command_from_begin() 从 buffer 的开头开始解析，直到遇到结尾标记为止。
        """
        if self.is_transparency and len(self.buffer) > 0:
            # 透传模式
            command = b'send:' + bytes(self.buffer[:])
            self.buffer.clear()
            self.log.info('control command: %s' % command)
            self.got_command_cb(command)

        while len(self.buffer) >= 4:
            # 解析指令
            try:
                if self.is_in_command:      # 指令从 buffer[0] 开始
                    command = self.resolve_command_from_begin()
                    if self.is_in_command:      # 没有遇到结尾，收到的指令还不完整
                        break
                    elif command is not None:   # 收到了指令
                        self.log.info('control command: %s' % command)
                        self.got_command_cb(command)
                        if command == b'%MODE1':
                            # 透传模式
                            # TODO: 身份验证
                            self.is_transparency = True
                            break
                elif self.buffer[:4] == CMD_BEGIN:  # begin of command
                    self.is_in_command = True
                else:
                    del self.buffer[0]      # 出队一个字节
            except Exception as e:
                self.log.warning('control thread resolve: %s' % e)

    def resolve_command_from_begin(self):
        """从 buffer 的起点开始解析"""
        for i in range(5, len(self.buffer) + 1):
            if self.buffer[i - 4:i] == CMD_BEGIN:   # begin again
                del self.buffer[:i - 4]
                return self.resolve_command_from_begin()
            elif i >= 8 and self.buffer[i - 4:i] == CMD_END:   # end of command
                command = bytes(self.buffer[4:i - 4])
                del self.buffer[:i]
                self.is_in_command = False
                return command
        return None

    def receive_data(self):
        """接收一个数据包

        并追加到 self.buffer 中。
        """
        data = self.client.recv(BUFFER_SIZE)
        if len(data) == 0:
            raise RuntimeError('socket connection broken')
        self.buffer.extend(data)
        self.log.debug('control rcv %d bytes.' % len(data))

    def send_message(self):
        """向控制端口发送数据

        数据来自 self.msg_queue
        """
        while self.msg_queue.qsize() > 0:
            try:
                msg = self.msg_queue.get(False)
                self.msg_queue.task_done()
                try:
                    self.client.sendall(bytearray(msg, 'utf-8'))
                except:
                    pass
            except queue.Empty:
                break

    def disconnect_client(self):
        """断开连接并清理"""
        if self.client is not None:
            # say goodbye
            try:
                self.client.sendall(b'bye')
            except:
                pass

            # close socket
            try:
                self.client.close()
            except socket.error:
                pass
            except Exception as e:
                self.log.error('control client exception when close: %s' % e)
        # clean up
        self.client = None
        self.buffer.clear()
        self.is_in_command = False
