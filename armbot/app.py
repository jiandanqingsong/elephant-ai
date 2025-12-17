from flask import Flask, render_template, request, jsonify
import paramiko
import os
import subprocess
import threading
import queue
import time
import json

app = Flask(__name__)

# --- 配置 ---
hostname = "192.168.0.197"
port = 22
username = "unitree"
password = "123" # 警告：硬编码密码存在安全风险
local_file_path = "control.py"
remote_file_path = "/home/unitree/yqw/input/control.py"

# 机械臂相关配置
armbot_hostname = "192.168.1.100"  # 假设机械臂的IP地址
armbot_port = 22
armbot_username = "unitree"
armbot_password = "123"

# agent.py配置
AGENT_PATH = "/elephant-ai/agent2.py"
AGENT_WORKING_DIR = "/elephant-ai"
# -----------

def run_agent_command(prompt, timeout=600):
    """
    运行agent.py命令
    
    Args:
        prompt (str): 要传递给agent.py的prompt
        timeout (int): 超时时间（秒）
    
    Returns:
        dict: 包含执行结果的字典
    """
    if not prompt:
        return {"success": False, "output": "", "error": "prompt不能为空"}
    
    if not os.path.exists(AGENT_PATH):
        return {"success": False, "output": "", "error": f"找不到agent.py文件: {AGENT_PATH}"}
    
    try:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始执行agent命令: {repr(prompt)}")
        
        # 构建命令
        cmd = ['python', AGENT_PATH, prompt]
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 执行命令: {' '.join(cmd)}")
        
        # 运行进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=AGENT_WORKING_DIR
        )
        
        # 等待进程完成
        stdout, stderr = process.communicate(timeout=600)
        
        return_code = process.returncode
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] agent命令执行完成，返回码: {return_code}")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 输出长度: {len(stdout)} 字符")
        if stderr:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 错误输出: {stderr[:200]}...")
        
        success = return_code == 0
        return {
            "success": success,
            "output": stdout,
            "error": stderr,
            "return_code": return_code
        }
        
    except subprocess.TimeoutExpired:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] agent命令执行超时")
        try:
            process.kill()
            stdout, stderr = process.communicate()
        except:
            stdout, stderr = "", ""
        
        return {
            "success": False,
            "output": stdout,
            "error": f"命令执行超时（{timeout}秒）\n" + stderr,
            "return_code": -1
        }
        
    except Exception as e:
        error_msg = f"执行agent命令时发生错误: {str(e)}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}")
        return {
            "success": False,
            "output": "",
            "error": error_msg,
            "return_code": -1
        }

def run_agent_command_async(prompt, callback=None, timeout=30):
    """
    异步运行agent.py命令
    
    Args:
        prompt (str): 要传递给agent.py的prompt
        callback (function): 回调函数，接收结果字典作为参数
        timeout (int): 超时时间（秒）
    
    Returns:
        threading.Thread: 执行任务的线程对象
    """
    def _run():
        result = run_agent_command(prompt, timeout)
        if callback:
            callback(result)
        return result
    
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread

@app.route('/go2')
def go2_index():
    """提供GO2编辑器页面。"""
    return render_template('go2-coder-v1.html')

@app.route('/armbot')
def armbot_index():
    """提供机械臂控制页面。"""
    return render_template('armbot.html')

@app.route('/armbot/execute', methods=['POST'])
def execute_agent_command():
    """
    执行agent命令的API接口
    
    POST请求体格式:
    {
        "prompt": "grab a yellow cube",
        "timeout": 30  // 可选，默认30秒
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "请求体不能为空"}), 400
        
        prompt = data.get('prompt', '').strip()
        timeout = data.get('timeout', 30)
        
        if not prompt:
            return jsonify({"success": False, "error": "prompt参数不能为空"}), 400
        
        # 验证timeout参数
        try:
            timeout = int(timeout)
            if timeout <= 0 or timeout > 300:  # 最大5分钟
                timeout = 30
        except (ValueError, TypeError):
            timeout = 30
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 收到agent执行请求: {repr(prompt)}")
        
        # 执行agent命令
        result = run_agent_command(prompt, timeout)
        
        # 返回结果
        return jsonify(result)
        
    except Exception as e:
        error_msg = f"处理请求时发生错误: {str(e)}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500

@app.route('/armbot/execute_async', methods=['POST'])
def execute_agent_command_async():
    """
    异步执行agent命令的API接口
    立即返回任务ID，可通过其他接口查询状态
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "请求体不能为空"}), 400
        
        prompt = data.get('prompt', '').strip()
        timeout = data.get('timeout', 30)
        
        if not prompt:
            return jsonify({"success": False, "error": "prompt参数不能为空"}), 400
        
        try:
            timeout = int(timeout)
            if timeout <= 0 or timeout > 300:
                timeout = 30
        except (ValueError, TypeError):
            timeout = 30
        
        # 生成任务ID
        import uuid
        task_id = str(uuid.uuid4())
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 收到异步agent执行请求: {repr(prompt)}, 任务ID: {task_id}")
        
        # 存储任务状态（简单的内存存储，生产环境建议使用Redis等）
        if not hasattr(app, 'agent_tasks'):
            app.agent_tasks = {}
        
        app.agent_tasks[task_id] = {
            "status": "running",
            "prompt": prompt,
            "start_time": time.time(),
            "result": None
        }
        
        # 定义回调函数
        def task_callback(result):
            if hasattr(app, 'agent_tasks') and task_id in app.agent_tasks:
                app.agent_tasks[task_id]["status"] = "completed"
                app.agent_tasks[task_id]["result"] = result
                app.agent_tasks[task_id]["end_time"] = time.time()
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 异步任务 {task_id} 完成")
        
        # 启动异步任务
        thread = run_agent_command_async(prompt, task_callback, timeout)
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "任务已启动"
        })
        
    except Exception as e:
        error_msg = f"处理异步请求时发生错误: {str(e)}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500

@app.route('/armbot/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """查询异步任务状态"""
    try:
        if not hasattr(app, 'agent_tasks') or task_id not in app.agent_tasks:
            return jsonify({"success": False, "error": "任务不存在"}), 404
        
        task = app.agent_tasks[task_id]
        
        response = {
            "success": True,
            "task_id": task_id,
            "status": task["status"],
            "prompt": task["prompt"],
            "start_time": task["start_time"]
        }
        
        if task["status"] == "completed":
            response["result"] = task["result"]
            response["end_time"] = task.get("end_time")
            response["duration"] = task.get("end_time", 0) - task["start_time"]
        
        return jsonify(response)
        
    except Exception as e:
        error_msg = f"查询任务状态时发生错误: {str(e)}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500

@app.route('/upload', methods=['POST'])
def upload_code():
    """接收代码，保存为 control.py 并通过 SFTP 上传。"""
    code = request.form.get('code')
    if not code:
        return jsonify({"error": "没有接收到代码"}), 400

    # 将代码写入本地文件
    try:
        with open(local_file_path, 'w', encoding='utf-8') as f:
            f.write(code)
    except IOError as e:
        print(f"写入本地文件错误: {e}")
        return jsonify({"error": f"无法写入本地文件: {e}"}), 500

    # --- SFTP 上传逻辑 ---
    ssh_client = None
    sftp_client = None
    try:
        print("开始 SFTP 上传...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # 仅用于测试

        print(f"正在连接到 {hostname}...")
        ssh_client.connect(hostname=hostname, port=port, username=username, password=password, timeout=10)
        print("SSH 连接成功！")

        sftp_client = ssh_client.open_sftp()
        print(f"正在上传 '{local_file_path}' 到 '{remote_file_path}'...")
        sftp_client.put(local_file_path, remote_file_path)
        print("文件上传成功！")
        return jsonify({"message": "代码上传成功！"})

    except paramiko.AuthenticationException:
        print("认证失败。")
        return jsonify({"error": "远程服务器认证失败，请检查用户名或密码。"}), 500
    except paramiko.SSHException as sshException:
        print(f"SSH 连接失败: {sshException}")
        return jsonify({"error": f"无法建立 SSH 连接: {sshException}"}), 500
    except FileNotFoundError:
        print(f"远程路径错误: {remote_file_path}")
        return jsonify({"error": f"远程路径 '{os.path.dirname(remote_file_path)}' 可能不存在或无权限访问。"}), 500
    except Exception as e:
        print(f"上传过程中发生未知错误: {e}")
        return jsonify({"error": f"上传过程中发生未知错误: {e}"}), 500
    finally:
        if sftp_client:
            sftp_client.close()
            print("SFTP 连接已关闭。")
        if ssh_client:
            ssh_client.close()
            print("SSH 连接已关闭。")

# 测试函数（可选）
def test_agent_command():
    """测试agent命令执行"""
    test_prompts = [
        "grab a yellow cube",
        "move to position (0, 0, 0.5)",
        "wave hello"
    ]
    
    for prompt in test_prompts:
        print(f"\n=== 测试prompt: {prompt} ===")
        result = run_agent_command(prompt, timeout=10)
        print(f"成功: {result['success']}")
        print(f"输出: {result['output'][:200]}...")
        if result['error']:
            print(f"错误: {result['error'][:200]}...")

if __name__ == '__main__':
    # 启动时测试agent.py是否可用（可选）
    if os.path.exists(AGENT_PATH):
        print(f"✓ agent.py文件存在: {AGENT_PATH}")
    else:
        print(f"✗ agent.py文件不存在: {AGENT_PATH}")
    
    # 可以取消注释进行测试
    # test_agent_command()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
