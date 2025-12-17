#!/usr/bin/env python3
"""
Jetson 音频录制与处理完整流程脚本
功能：1.录音为WAV 2.播放WAV 3.转码为FLAC 4.播放FLAC
"""

import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write as write_wav
import subprocess
import os
import time

# ==================== 用户配置区域 ====================
# 录音参数（基于我们之前的调试结果）
# INPUT_DEVICE = 'plughw:3,0'  # 你的USB麦克风地址，也可使用 'pulse'
INPUT_DEVICE = "pulse"  # 你的USB麦克风地址，也可使用 'pulse'
SAMPLE_RATE = 44100  # 采样率 (Hz)，你的设备原生支持
DURATION = 10  # 默认录音时长（秒）
CHANNELS = 1  # 声道数，单声道兼容性最好

# 文件路径
WAV_FILENAME = "recording.wav"
FLAC_FILENAME = "Recording.flac"


# ==================== 核心功能函数 ====================
def list_audio_devices():
    """列出所有音频设备，用于检查"""
    print("=== 可用的音频设备 ===")
    try:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            print(f"  索引 {i}: {dev['name']}")
    except Exception as e:
        print(f"   无法查询设备列表: {e}")
        print(
            "   提示：请尝试运行 'arecord -l' 命令查看系统识别到的录音设备[citation:7]"
        )
    print("=" * 40)


def record_audio_to_wav(filename, duration=DURATION):
    """
    1. 录制音频并保存为WAV文件
    返回: (成功标志, 音频数据)
    """
    print(f"[步骤1] 开始录音，时长 {duration} 秒...")
    try:
        # 使用验证过的参数进行录音
        audio_data = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",  # 16位PCM，WAV标准格式
            device=INPUT_DEVICE,
        )
        sd.wait()  # 阻塞等待录音结束
        print("    录音结束。")

        # 处理数据形状：确保为一维数组 (单声道)
        if audio_data.ndim > 1 and audio_data.shape[1] == 1:
            audio_data = audio_data.squeeze()

        # 保存为WAV文件
        write_wav(filename, SAMPLE_RATE, audio_data)
        file_size = os.path.getsize(filename) / 1024  # KB
        print(f"    ✅ WAV文件已保存: {filename} ({file_size:.1f} KB)")

        return True, audio_data

    except Exception as e:
        print(f"    ❌ 录音失败: {e}")
        print("   可能原因：设备地址错误、麦克风被占用或权限不足")
        return False, None


def play_audio_file(filename):
    """
    2. 使用系统默认音频设备播放文件
    注意：此函数会阻塞直到播放完成
    """
    print(f"[步骤2] 尝试播放文件: {filename}")

    if not os.path.exists(filename):
        print(f"    ❌ 文件不存在: {filename}")
        return False

    try:
        # 方法A: 使用aplay命令播放 (针对WAV/PCM格式最可靠)
        print("    使用系统音频设备播放 (aplay)...")
        # -D default 指定使用默认播放设备
        result = subprocess.run(
            ["aplay", "-D", "default", filename],
            capture_output=True,
            text=True,
            timeout=DURATION + 2,
        )
        if result.returncode == 0:
            print("    ✅ 播放完成")
            return True
        else:
            print(f"    aplay播放失败: {result.stderr}")
            # 方法A失败，不尝试方法B，直接返回
            return False

    except subprocess.TimeoutExpired:
        print("    ⚠️ 播放超时，进程已终止")
        return False
    except FileNotFoundError:
        print("    ❌ 'aplay' 命令未找到，请确保ALSA系统工具已安装")
        return False
    except Exception as e:
        print(f"    ❌ 播放过程出错: {e}")
        return False


def convert_wav_to_flac_with_ffmpeg(wav_file, flac_file):
    """
    3. 使用FFmpeg将WAV文件转换为FLAC格式
    """
    print(f"[步骤3] 转换 {wav_file} -> {flac_file}")

    if not os.path.exists(wav_file):
        print(f"    ❌ 源文件不存在: {wav_file}")
        return False

    try:
        # 使用FFmpeg进行转换，-y 参数表示覆盖已存在的输出文件
        # -compression_level 5 是压缩级别（0最快/压缩率低，12最慢/压缩率高）
        cmd = [
            "ffmpeg",
            "-i",
            wav_file,
            "-c:a",
            "flac",  # 指定音频编码器为FLAC
            "-compression_level",
            "5",
            "-y",  # 覆盖输出文件
            flac_file,
        ]

        # 运行命令，隐藏正常输出，只捕获错误
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
        )

        if result.returncode == 0 and os.path.exists(flac_file):
            # 计算和显示压缩率
            flac_size = os.path.getsize(flac_file) / 1024  # KB
            wav_size = os.path.getsize(wav_file) / 1024
            if wav_size > 0:
                compression = (1 - flac_size / wav_size) * 100
                print(f"    ✅ 转换成功！")
                print(
                    f"       WAV: {wav_size:.1f} KB, FLAC: {flac_size:.1f} KB, 压缩率: {compression:.1f}%"
                )
            else:
                print(f"    ✅ 转换成功！文件大小: {flac_size:.1f} KB")
            return True
        else:
            print(f"    ❌ FFmpeg转换失败")
            if result.stderr:
                # 提取错误信息中的关键行
                for line in result.stderr.split("\n"):
                    if "Error" in line or "failed" in line.lower():
                        print(f"       错误: {line.strip()}")
            return False

    except FileNotFoundError:
        print("    ❌ 'ffmpeg' 命令未找到，请先安装FFmpeg[citation:7]")
        print("       安装命令: sudo apt-get install ffmpeg")
        return False
    except Exception as e:
        print(f"    ❌ 转换过程出错: {e}")
        return False


def play_flac_with_ffplay(flac_file):
    """
    4. 使用ffplay播放FLAC文件[citation:9]
    """
    print(f"[步骤4] 使用ffplay播放FLAC文件...")

    if not os.path.exists(flac_file):
        print(f"    ❌ FLAC文件不存在: {flac_file}")
        return False

    try:
        # ffplay会自动使用默认音频输出设备
        # 增加 '-autoexit' 参数让播放完成后自动退出
        # 增加 '-nodisp' 参数因为这是纯音频文件，不需要显示窗口
        cmd = ["ffplay", "-autoexit", "-nodisp", flac_file]

        print("    正在播放 (使用 ffplay)...")
        # 设置超时，避免文件损坏导致无限等待
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=DURATION + 5
        )

        if result.returncode == 0:
            print("    ✅ FLAC播放完成")
            return True
        else:
            print(f"    ❌ ffplay播放失败，返回码: {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print("    ⚠️ 播放超时，进程已终止")
        return False
    except FileNotFoundError:
        print("    ❌ 'ffplay' 命令未找到，它是FFmpeg的一部分[citation:9]")
        print("       请确保FFmpeg已完整安装: sudo apt-get install ffmpeg")
        return False
    except Exception as e:
        print(f"    ❌ 播放过程出错: {e}")
        return False


# ==================== 主程序 ====================
def main():
    print("\n" + "=" * 50)
    print("Jetson 音频录制与处理全流程")
    print("=" * 50)

    # 可选：显示音频设备列表（调试用）
    # list_audio_devices()

    # 步骤1: 录音并保存为WAV
    success, audio_data = record_audio_to_wav(WAV_FILENAME)
    if not success:
        print("程序终止：录音步骤失败。")
        return

    # 步骤2: 播放刚录制的WAV文件
    play_audio_file(WAV_FILENAME)

    # 步骤3: 转换为FLAC格式
    if convert_wav_to_flac_with_ffmpeg(WAV_FILENAME, FLAC_FILENAME):
        # 步骤4: 播放FLAC文件
        play_flac_with_ffplay(FLAC_FILENAME)

    print("\n" + "=" * 50)
    print("✨ 处理完成！")
    print(f"   生成文件: {WAV_FILENAME}, {FLAC_FILENAME}")
    print("=" * 50)


# ==================== 脚本入口 ====================
if __name__ == "__main__":
    # 检查必要的Python库
    try:
        import sounddevice as sd
        import numpy as np
        from scipy.io.wavfile import write
    except ImportError as e:
        print(f"❌ 缺少必要的Python库: {e}")
        print("请安装依赖: pip3 install sounddevice numpy scipy")
        exit(1)

    # 运行主程序
    main()
