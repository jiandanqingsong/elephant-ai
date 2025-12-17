from react_agent.LLM import RequestLLM
from react_agent.agent import ReactAgent
from react_agent.tools import tools_registry
import time
import json
import os
import voice
import tools
import sys
import argparse

def exit_function():
    """在程序退出时执行的清理函数"""
    print("\n程序即将退出，正在执行清理操作（如机械臂归位）...")
    # 在这里添加机械臂归位的代码
    print("清理完成，程序退出。")

def wait_for_file_update(file_path, last_mtime):
    """ 持续等待文件更新 """
    while True:
        try:
            current_mtime = os.path.getmtime(file_path)
            if current_mtime != last_mtime:
                return current_mtime
        except FileNotFoundError:
            pass
        time.sleep(1)  # 等待 1 秒后再检查

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='React Agent with command-line input')
    parser.add_argument('user_input', nargs='*', 
                       help='用户输入内容，多个词会被合并成一句话')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='交互模式，忽略命令行输入，等待用户输入')
    parser.add_argument('--voice', '-v', action='store_true',
                       help='强制使用语音模式，覆盖配置文件设置')
    return parser.parse_args()

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_arguments()
    
    # 1. 实例化agent
    llm = RequestLLM(base_url="https://api.deepseek.com/v1", model_name="deepseek-chat")
    agent = ReactAgent(llm)
    
    # 2. 注册工具
    for name, cls in tools_registry.items():
        agent.register_tool(name, cls)
    
    # 3. 更新系统prompt
    agent.update_system_message()
    
    with open("config.json", "r") as config_file:
        config_data = json.load(config_file)
    
    # 语音设置：命令行参数优先，否则使用配置文件
    use_voice = args.voice or config_data.get("voice", False)
    recording_file_path = "Recording.flac"
    last_mtime = None
    
    try:
        # 如果提供了命令行输入且不是交互模式
        if args.user_input and not args.interactive:
            # 将命令行参数合并成一句话
            user_input = ' '.join(args.user_input)
            print(f"<USER>: {user_input}")
            agent.chat(user_input)
        else:
            # 交互模式或没有提供命令行输入时的原有逻辑
            print("进入交互模式...")
            while True:
                time.sleep(5)
                if use_voice:
                    if last_mtime is None:
                        # 第一次直接识别
                        user_input = voice.record_auto()
                        last_mtime = os.path.getmtime(recording_file_path)
                    else:
                        # 等待文件更新
                        last_mtime = wait_for_file_update(recording_file_path, last_mtime)
                        user_input = voice.record_auto()
                else:
                    user_input = input("<USER>:")
                agent.chat(user_input)
    finally:
        exit_function()
