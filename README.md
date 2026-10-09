# Minecraft 服务器管理工具

本机 Windows 桌面工具，用于管理 `D:\mc-server\mc-server` 下的 Forge 1.20.1 服务端。

## 启动

```bash
cd D:\mc-server\mc-server-manager
D:\ANACONDA\python.exe -m app
```

## 功能

- 显示服务端运行状态、PID、端口、地图、CPU、内存和在线玩家
- 启动服务端
- 发送 `stop` 安全关闭
- 强制结束由本工具启动的 Java 进程树
- 只读显示 `logs/latest.log` 最近内容
- 检测端口是否已被外部服务端占用

## 启动方式说明

工具不直接执行 `run.bat`，因为 `run.bat` 末尾的 `pause` 会让管理程序在服务端退出后仍认为进程存活。它改为在相同工作目录下直接启动：

```bash
java @user_jvm_args.txt @libraries/net/minecraftforge/forge/<version>/win_args.txt nogui
```

这与 `run.bat` 实际启动的服务端相同，但能正确接管标准输入、退出状态和进程树。

## 测试

```bash
cd D:\mc-server\mc-server-manager
D:\ANACONDA\python.exe -m pytest -v
```

## 限制

- 第一版不修改 `server.properties`、JVM 参数、OP、白名单或封禁配置
- 第一版不管理 frp 隧道、备份或世界删除
- 只能管理由本工具启动的服务端进程；如果服务端已经通过 `run.bat` 启动，工具会显示端口被外部进程占用
- 强制停止可能来不及完整保存世界，只在安全停止无响应时使用
