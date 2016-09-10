## 组件说明

#### rtk
主程序，启动各子进程，负责键盘交互。

#### log
日志。

#### rtk_group
管理一组差分配置的进程

#### rtk_thread
管理一组差分线程的线程。
每个 `RtkGroup` 中运行一个 `RtkThread`。

#### station_thread
基站线程基类。

#### station_server_thread
socket server 线程，继承自 `StationThread`，
接受差分源服务器连接，并接收数据。

#### station_client_thread
socket client 线程，继承自 `StationThread`，
主动连接到差分源服务器，并接收数据。

#### station_connection_thread
socket 线程，从差分源服务器接收数据。

#### server_thread
本地 socket server 线程，监听来自下层客户端的连接。

#### dispatcher
数据分发工具，由 `ServerThread` 维护，
将 `StationConnectionThread` 收到的数据转发到各 SenderThread。

#### sender_thread
每个 `SenderThread` 管理一个从 `ServerThread` accept 到的 `socket`，
负责数据发送。

#### control_thread
查询状态，调试（或维护）用。

#### http_process
web 管理进程。

#### http_thread
web 管理接口。
