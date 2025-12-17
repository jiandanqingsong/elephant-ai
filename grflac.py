import gradio as gr
import numpy as np
import soundfile as sf
import shutil
import os
import sys
import json
import contextlib
from io import StringIO

# 引入Agent相关模块
from react_agent.LLM import RequestLLM
from react_agent.agent import ReactAgent
from react_agent.tools import tools_registry
import voice
import tools  # 导入tools以注册工具

# 固定的文件名
FIXED_FLAC_FILE = "current_recording.flac"
TARGET_FLAC_FILE = "Recording.flac"

# 初始化Agent
print("正在初始化Agent...")
try:
    llm = RequestLLM(base_url="https://api.deepseek.com/v1", model_name="deepseek-chat")
    agent = ReactAgent(llm)

    # 注册工具
    for name, cls in tools_registry.items():
        agent.register_tool(name, cls)

    # 更新系统prompt
    agent.update_system_message()

    # 加载配置
    try:
        with open("config.json", "r") as config_file:
            config_data = json.load(config_file)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        config_data = {}
    print("Agent初始化完成")
except Exception as e:
    print(f"Agent初始化失败: {e}")
    agent = None

@contextlib.contextmanager
def capture_stdout():
    new_out = StringIO()
    old_out = sys.stdout
    try:
        sys.stdout = new_out
        yield new_out
    finally:
        sys.stdout = old_out

def save_and_process_audio(audio):
    """录音完成后自动保存为FLAC文件"""
    if audio is None:
        return "❌ 未检测到音频输入", None
    
    sample_rate, audio_data = audio
    
    try:
        # 保存为固定FLAC文件（覆盖模式）
        sf.write(file=FIXED_FLAC_FILE,
                 data=audio_data,
                 samplerate=sample_rate,
                 format='FLAC',
                 subtype='PCM_16')
        
        duration = len(audio_data) / sample_rate
        message = f"✅ 录音已保存: {FIXED_FLAC_FILE}\n时长: {duration:.1f}秒, 采样率: {sample_rate}Hz"
        
        return message, FIXED_FLAC_FILE
    except Exception as e:
        return f"❌ 保存失败: {str(e)}", None

def copy_to_recording():
    """复制文件到当前目录的Recording.flac"""
    if not os.path.exists(FIXED_FLAC_FILE):
        return f"❌ 找不到 {FIXED_FLAC_FILE}，请先录制音频"
    
    try:
        # 复制文件
        shutil.copy2(FIXED_FLAC_FILE, TARGET_FLAC_FILE)
        
        # 验证复制结果
        if os.path.exists(TARGET_FLAC_FILE):
            file_size = os.path.getsize(TARGET_FLAC_FILE) / 1024
            return f"✅ 复制成功: {TARGET_FLAC_FILE} ({file_size:.1f}KB)"
        else:
            return "❌ 复制失败：目标文件未创建"
    except Exception as e:
        return f"❌ 复制失败: {str(e)}"

def process_text_interaction(text, history):
    """处理文字交互"""
    if not text:
        return "", history
    
    history = history or []
    history.append({"role": "user", "content": text})
    
    if agent is None:
        history.append({"role": "assistant", "content": "❌ Agent未初始化成功，无法处理指令。"})
        return "", history

    with capture_stdout() as out:
        try:
            print(f"<USER>: {text}")
            agent.chat(text)
        except Exception as e:
            print(f"Error during chat: {e}")
    
    output = out.getvalue()
    history.append({"role": "assistant", "content": output})
    return "", history

def process_voice_interaction(history):
    """处理语音交互：复制文件 -> 识别 -> Agent对话"""
    history = history or []

    # 1. 复制文件
    copy_msg = copy_to_recording()
    if "❌" in copy_msg:
        history.append({"role": "assistant", "content": copy_msg})
        return history, copy_msg

    # 2. 语音识别
    try:
        # voice.record_auto() 读取 Recording.flac 并返回文本
        user_input = voice.record_auto()
    except Exception as e:
        msg = f"语音识别失败: {e}"
        history.append({"role": "assistant", "content": msg})
        return history, msg

    if not user_input:
        return history, "语音识别结果为空"

    # 3. Agent对话
    history.append({"role": "user", "content": f"[语音] {user_input}"})

    if agent is None:
        history.append({"role": "assistant", "content": "❌ Agent未初始化成功，无法处理指令。"})
        return history, "Agent未初始化"

    with capture_stdout() as out:
        try:
            agent.chat(user_input)
        except Exception as e:
            print(f"Error during chat: {e}")
            
    output = out.getvalue()
    history.append({"role": "assistant", "content": output})
    
    return history, f"语音指令已执行: {user_input}"

# 创建交互界面
with gr.Blocks(title="Jetson AI 交互终端", theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🤖 Jetson AI 交互终端")
    
    # 1. 摄像头画面 (预留)
    with gr.Row():
        camera_display = gr.Image(label="摄像头画面", height=400, interactive=False, sources=None)

    # 聊天记录显示
    chatbot = gr.Chatbot(label="交互记录", height=500)

    # 2. 交互区域
    with gr.Row():
        # 文字交互区域
        with gr.Column():
            gr.Markdown("### 📝 文字交互")
            text_input = gr.Textbox(label="输入指令", placeholder="请输入文字并回车...")
            text_button = gr.Button("发送文字")
            
            text_input.submit(process_text_interaction, inputs=[text_input, chatbot], outputs=[text_input, chatbot])
            text_button.click(process_text_interaction, inputs=[text_input, chatbot], outputs=[text_input, chatbot])

        # 语音交互区域
        with gr.Column():
            gr.Markdown("### 🗣️ 语音交互")
            audio_input = gr.Audio(
                sources=["microphone"],
                type="numpy",
                label="语音录入",
                format="wav",
                interactive=True
            )
            status_display = gr.Textbox(label="状态", value="等待录音...", lines=2)
            # 隐藏的音频播放组件
            audio_output = gr.Audio(label="录音回放", visible=False, interactive=False)
            
            voice_button = gr.Button("发送语音 (复制到Recording.flac)", variant="primary")
            
            # 录音完成后自动保存
            audio_input.change(
                fn=save_and_process_audio,
                inputs=[audio_input],
                outputs=[status_display, audio_output]
            )
            
            # 点击按钮执行语音流程
            voice_button.click(
                fn=process_voice_interaction,
                inputs=[chatbot],
                outputs=[chatbot, status_display]
            )

# 启动应用
if __name__ == "__main__":
    print("启动Jetson AI 交互终端...")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
