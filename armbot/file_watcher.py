#!/usr/bin/env python3
import os
import time
import subprocess
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

# 监控的目标文件夹
TARGET_DIR = '/home/unitree/yqw/input'
TARGET_FILE = 'control.py'


def clear_directory(directory_path):
    """清空指定目录下的所有文件和符号链接"""
    logger.info(f"开始清空目录: {directory_path}")
    try:
        with os.scandir(directory_path) as it:
            entry_found = False
            for entry in it:
                entry_found = True
                entry_path = os.path.join(directory_path, entry.name)
                try:
                    if entry.is_file() or entry.is_symlink():
                        os.unlink(entry_path)
                        logger.info(f"已删除文件: {entry_path}")
                    elif entry.is_dir():
                        # 这里仅删除文件和符号链接，如果需要删除子目录请告知
                        logger.warning(f"发现子目录，未删除: {entry_path}")
                except Exception as e:
                    logger.error(f"删除 {entry_path} 时出错: {e}")
            if entry_found:
                logger.info(f"目录 {directory_path} 已清空。")
            else:
                logger.info(f"目录 {directory_path} 为空，无需清空。")
    except FileNotFoundError:
        logger.warning(f"尝试清空目录时发现目录不存在: {directory_path}")
    except Exception as e:
        logger.error(f"清空目录 {directory_path} 时发生错误: {e}")


class FileHandler(FileSystemEventHandler):
    def on_created(self, event):
        """当监测到创建文件时触发"""
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            if filename == TARGET_FILE:
                logger.info(f"检测到新文件: {event.src_path}")
                self.execute_script(event.src_path)
    
    def on_moved(self, event):
        """当监测到移动/重命名文件时触发"""
        if not event.is_directory and os.path.basename(event.dest_path) == TARGET_FILE:
            logger.info(f"检测到移动/重命名文件: {event.dest_path}")
            self.execute_script(event.dest_path)
            
    def execute_script(self, script_path):
        """执行Python脚本，并在执行后清空目录"""
        try:
            logger.info(f"开始执行脚本: {script_path}")
            subprocess.run(['python3', script_path], check=True)
            logger.info(f"脚本执行完成: {script_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"脚本执行出错: {e}")
        except Exception as e:
            logger.error(f"发生未知错误: {e}")
        finally:
            # 无论成功或失败，都尝试清空目录
            clear_directory(TARGET_DIR)


def main():
    # 确保目标目录存在
    if not os.path.exists(TARGET_DIR):
        try:
            os.makedirs(TARGET_DIR)
            logger.info(f"创建目标目录: {TARGET_DIR}")
        except PermissionError:
            logger.error(f"无权限创建目录: {TARGET_DIR}")
            return
        except Exception as e:
            logger.error(f"创建目录时发生错误: {e}")
            return
    else:
        # 如果目录存在且不为空，则清空目录
        logger.info(f"目标目录 {TARGET_DIR} 已存在，检查是否需要清空...")
        clear_directory(TARGET_DIR)

    # 设置事件处理器和观察者
    event_handler = FileHandler()
    observer = Observer()
    observer.schedule(event_handler, TARGET_DIR, recursive=False)
    
    # 开始监控
    observer.start()
    logger.info(f"开始监控目录: {TARGET_DIR}")
    
    try:
        # 保持程序运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("监控已停止")
    
    observer.join()


if __name__ == "__main__":
    main() 