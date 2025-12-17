import requests
import base64
import re
import json

qwen_vl_url="https://llm.educg.com/svc/AfW1gQzE-1/image"
qwen_audio_url="https://llm.educg.com/svc/AfW1gQzE-1/audio"

def AudioRecognize(flac_file):
    """
    将 FLAC 文件发送到 /audio 端点进行语音识别，并返回 %...% 中的部分内容
    """
    files = {'audio_url': open(flac_file, 'rb')}
    try:
        response = requests.post(qwen_audio_url, files=files)
        if response.status_code == 200:
            result = response.json()
            print("语音识别结果:", result)

            # 使用正则表达式提取 %...% 中的内容
            matches = re.findall(r'"(.*?)"', result["response"])
            print(matches[0])
            if matches:
                return matches[0]  # 返回匹配到的内容
            else:
                return None  # 如果没有找到匹配的内容，返回 None
        else:
            print("请求失败，状态码:", response.status_code)
            return None
    except Exception as e:
        print("请求失败:", str(e))
        return None

def QwenVLRequest(object_name, image_path):
    """
       发送请求到指定的URL，包含物体名称和Base64编码的图像数据。

       :param object_name: 要识别或处理的物体名称
       :param image_path: 本地图像文件路径
       :param url: 请求的目标URL，默认为指定URL
       :return: 返回请求的响应结果，JSON格式
       """
    try:
        # 将图像文件转换为Base64
        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

        # 构造要发送的JSON数据
        payload = {
            "text": object_name,
            "image_base64": image_base64
        }

        # 发送POST请求
        response = requests.post(qwen_vl_url, json=payload)

        # 检查响应状态码并返回相应结果
        if response.status_code == 200:
            return response.json()  # 返回响应的JSON数据
        else:
            return {"error": "Request failed", "status_code": response.status_code, "response": response.text}

    except requests.exceptions.RequestException as e:
        return {"error": "An exception occurred", "details": str(e)}