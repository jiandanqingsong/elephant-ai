from react_agent.LLM import RequestLLM
from react_agent.agent import ReactAgent
from react_agent.tools import tools_registry
import time
import json
import os
import voice
import tools

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

if __name__ == "__main__":
    # 1. 实例化agent
    llm = RequestLLM(base_url="https://api.deepseek.com/v1/", model_name="deepseek-chat")
    agent = ReactAgent(llm)
    # 2. 注册工具
    for name, cls in tools_registry.items():
        agent.register_tool(name, cls)
    # 3. 更新系统prompt
    agent.update_system_message()

    with open("config.json", "r") as config_file:
        config_data = json.load(config_file)

    use_voice = config_data.get("voice", False)
    recording_file_path = "Recording.flac"
    last_mtime = None

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