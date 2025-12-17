# 文件监控服务

这个服务会监控 `/home/unitree/input` 目录，当检测到新的 `control.py` 文件时，自动执行该Python脚本。

## 依赖安装

此服务依赖于Python的watchdog库。请使用以下命令安装：

```bash
pip3 install watchdog
```

## 安装步骤

1. 复制脚本到合适的位置：

```bash
sudo cp file_watcher.py /usr/local/bin/
sudo chmod +x /usr/local/bin/file_watcher.py
```

2. 编辑systemd服务文件中的路径：

```bash
# 编辑文件
sudo nano file_watcher.service

# 修改ExecStart行为正确的路径
ExecStart=/usr/bin/python3 /usr/local/bin/file_watcher.py
```

3. 安装systemd服务：

```bash
sudo cp file_watcher.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable file_watcher.service
sudo systemctl start file_watcher.service
```

4. 检查服务状态：

```bash
sudo systemctl status file_watcher.service
```

## 使用方法

将任何命名为`control.py`的Python文件放入`/home/unitree/input`目录即可自动执行。

## 日志查看

使用以下命令查看服务日志：

```bash
sudo journalctl -u file_watcher.service
``` 