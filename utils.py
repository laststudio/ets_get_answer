import requests
import time
import hashlib
import base64
import json
import os
import zipfile
import getpass
import shutil
from typing import Dict, List, Tuple, Optional, Any

# 调试模式开关
DEBUG_MODE = True
# API基础URL
BASE_URL = "https://api.ets100.com"
# CDN基础URL
CDN_BASE_URL = "cdn.subject.ets100.com"
# 常量定义
PID = "grlx"
SECRET_KEY = "555ffbe95ccf4e9535a110170b445ab8"
FOOTER_SIZE = 336


def make_sign(content: str, timestamp: int = int(time.time())) -> str:
    """
    生成API请求签名
    
    Args:
        content: 需要签名的内容
        timestamp: 时间戳，默认为当前时间
    
    Returns:
        str: MD5签名值
    """
    md5 = hashlib.md5()
    sign_str = f"{PID}{timestamp}{content}{SECRET_KEY}"
    md5.update(sign_str.encode("utf-8"))
    return md5.hexdigest()


def create_request_payload(api_method: str, params: Dict[str, Any]) -> str:
    """
    创建API请求的载荷
    
    Args:
        api_method: API方法名
        params: 请求参数
    
    Returns:
        str: JSON格式的请求载荷
    """
    # 构建请求体
    body = [{"r": api_method, "params": params}]
    body_json = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    body_b64 = base64.b64encode(body_json.encode("utf-8")).decode("utf-8")
    
    # 获取当前时间戳
    timestamp = int(time.time())
    
    # 构建请求头
    head = {
        "version": "1.0",
        "sign": make_sign(content=body_b64, timestamp=timestamp),
        "pid": PID,
        "time": timestamp,
    }
    
    # 构建完整载荷
    payload = {"body": body_b64, "head": head}
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def send_api_request(api_url: str, payload: str) -> Optional[Dict[str, Any]]:
    """
    发送API请求并处理响应
    
    Args:
        api_url: 完整的API URL
        payload: 请求载荷
    
    Returns:
        Optional[Dict]: 解析后的JSON响应或None（如果请求失败）
    """
    headers = {
        "Host": "api.ets100.com",
        "User-Agent": "libcurl-agent/1.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "*/*"
    }
    
    try:
        response = requests.post(url=api_url, data=payload, headers=headers, timeout=30)
        response.raise_for_status()  # 如果响应状态码不是200，抛出异常
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"响应JSON解析失败: {e}")
        return None


def login(phone: str, password: str, device_code: str = "DA6FDF42C0849761|0C072A134F008B9F", 
          device_name: str = "LEITIANSHUO", system: str = "4", sign_response: int = 1, 
          version: str = "3", global_client_version: str = "", sn: str = "test") -> Optional[str]:
    """
    用户登录函数
    
    Args:
        phone: 手机号
        password: 密码
        device_code: 设备代码
        device_name: 设备名称
        system: 系统版本
        sign_response: 签名响应
        version: API版本
        global_client_version: 全局客户端版本
        sn: 序列号
    
    Returns:
        Optional[str]: 登录成功返回token，失败返回None
    """
    params = {
        "sn": sn,
        "phone": phone,
        "password": password,
        "device_code": device_code,
        "device_name": device_name,
        "version": version,
        "local_ip": "192.168.1.3",
        "system": system,
        "global_client_version": global_client_version,
        "sign_response": sign_response,
    }
    
    payload = create_request_payload("user/login", params)
    response = send_api_request(f"{BASE_URL}/user/login", payload)
    
    if response and len(response) > 0 and "body" in response[0] and "token" in response[0]["body"]:
        return response[0]["body"]["token"]
    else:
        print("登录失败，请检查手机号和密码")
        return None


def get_parent_account_id(token: str, system: str = "4", sign_response: int = 1, 
                         version: str = "2", global_client_version: str = "", sn: str = "test") -> Optional[str]:
    """
    获取家长账户ID
    
    Args:
        token: 登录令牌
        system: 系统版本
        sign_response: 签名响应
        version: API版本
        global_client_version: 全局客户端版本
        sn: 序列号
    
    Returns:
        Optional[str]: 家长账户ID或None（如果获取失败）
    """
    params = {
        "sn": sn,
        "token": token,
        "version": version,
        "system": system,
        "global_client_version": global_client_version,
        "sign_response": sign_response,
    }
    
    payload = create_request_payload("m/ecard/list", params)
    response = send_api_request(f"{BASE_URL}/m/ecard/list", payload)
    
    if response and len(response) > 0 and "body" in response[0] and "0" in response[0]["body"]:
        return response[0]["body"]["0"]["parent_id"]
    else:
        print("获取家长账户ID失败")
        return None


def get_homework_list(parent_account_id: str, token: str, limit: str = "10", system: str = "4", 
                     sign_response: int = 1, version: str = "2", global_client_version: str = "5.4.5", 
                     sn: str = "test") -> Optional[Dict[str, Any]]:
    """
    获取作业列表
    
    Args:
        parent_account_id: 家长账户ID
        token: 登录令牌
        limit: 限制数量
        system: 系统版本
        sign_response: 签名响应
        version: API版本
        global_client_version: 全局客户端版本
        sn: 序列号
    
    Returns:
        Optional[Dict]: 作业列表数据或None（如果获取失败）
    """
    params = {
        "sn": sn,
        "token": token,
        "parent_account_id": parent_account_id,
        "limit": limit,
        "status": "1",
        "offset": "0",
        "max_end_time": "",
        "max_homework_id": "",
        "min_end_time": "",
        "min_homework_id": "",
        "get_to_do_count": "1",
        "show_old_homework": "1",
        "parent_homework_id": "",
        "get_all_count": 1,
        "check_pass": 1,
        "get_to_overtime_count": 1,
        "version": version,
        "system": system,
        "global_client_version": global_client_version,
        "sign_response": sign_response
    }
    
    payload = create_request_payload("g/homework/list", params)
    response = send_api_request(f"{BASE_URL}/g/homework/list", payload)
    
    if response and len(response) > 0 and "body" in response[0]:
        return response[0]["body"]
    else:
        print("获取作业列表失败")
        return None


def get_homework_urls(parent_account_id: str, token: str) -> List[Dict[str, Any]]:
    """
    获取作业URL列表
    
    Args:
        parent_account_id: 家长账户ID
        token: 登录令牌
    
    Returns:
        List[Dict]: 包含作业名称和URL的字典列表
    """
    homework_data = get_homework_list(parent_account_id=parent_account_id, token=token)
    if not homework_data:
        return []
    
    base_url = homework_data.get("base_url", "")
    datas = homework_data.get("data", [])
    homework_list = []
    
    for data in datas:
        if "struct" not in data or "contents" not in data["struct"]:
            continue
            
        zip_info = data["struct"]["contents"]
        content_dict = {}
        
        for info in zip_info:
            group_name = info.get("group_name", "未知分组")
            url = info.get("url", "")
            
            if group_name not in content_dict:
                content_dict[group_name] = []
            
            if url:
                content_dict[group_name].append(base_url + url)
        
        homework_list.append({
            "name": data.get("name", "未知作业"),
            "contents": content_dict
        })
    
    return homework_list


def calculate_md5(data: bytes) -> bytes:
    """计算二进制数据的MD5哈希值"""
    md5 = hashlib.md5()
    md5.update(data)
    return md5.digest()


def bytes_to_hex_string(data: bytes) -> str:
    """将二进制数据转换为大写十六进制字符串"""
    return data.hex().upper()


def generate_zip_password(zip_data: bytes) -> str:
    """
    生成压缩包密码
    
    Args:
        zip_data: 压缩包二进制数据
    
    Returns:
        str: 64字符的密码
    
    Raises:
        ValueError: 当文件签名无效或数据太小
    """
    if len(zip_data) < FOOTER_SIZE:
        raise ValueError("文件数据太小，无法提取尾部信息")
    
    # 提取尾部336字节
    footer = zip_data[-FOOTER_SIZE:]
    
    # 验证签名 (MSTCHINA 或 EPLAT)
    valid_signature = (footer[:8] == b'MSTCHINA' or footer[144:149] == b'EPLAT')
    
    if not valid_signature:
        raise ValueError("无效的文件签名")
    
    # 提取128字节种子数据 (偏移16-143)
    seed = footer[16:144]
    
    # 第一重MD5: 计算种子数据的MD5
    first_md5 = calculate_md5(seed)
    first_hex = bytes_to_hex_string(first_md5)
    
    # 第二重MD5: 计算第一重结果的十六进制字符串的MD5
    second_md5 = calculate_md5(first_hex.encode('ascii'))
    second_hex = bytes_to_hex_string(second_md5)
    
    # 拼接最终密码 (64字符)
    return first_hex + second_hex


def download_file(url: str, save_path: str) -> bool:
    """
    下载文件到指定路径
    
    Args:
        url: 文件URL
        save_path: 保存路径
    
    Returns:
        bool: 下载是否成功
    """
    headers = {
        "Host": CDN_BASE_URL,
        "User-Agent": "libcurl-agent/1.0",
        "Accept": "*/*"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(response.content)
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"下载文件失败: {e}")
        return False
    except IOError as e:
        print(f"保存文件失败: {e}")
        return False


def extract_zip(zip_path: str, extract_dir: str, password: str) -> bool:
    """
    解压ZIP文件
    
    Args:
        zip_path: ZIP文件路径
        extract_dir: 解压目录
        password: 解压密码
    
    Returns:
        bool: 解压是否成功
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir, pwd=password.encode("utf-8"))
        return True
    except zipfile.BadZipFile:
        print(f"文件损坏或不是有效的ZIP文件: {zip_path}")
        return False
    except RuntimeError as e:
        print(f"解压失败，密码可能错误: {e}")
        return False
    except Exception as e:
        print(f"解压过程中发生错误: {e}")
        return False


def process_listening_choice(extract_dir: str, file_path: str) -> str:
    """
    处理听后选择题型
    
    Args:
        extract_dir: 解压目录
        file_path: 文件路径
    
    Returns:
        str: 处理后的答案文本
    """
    result = ""
    info_path = os.path.join(extract_dir, "info.json")
    
    try:
        with open(info_path, "r", encoding="utf-8") as f:
            info_data = json.load(f)
            code_json_array = json.loads(info_data[1]["code_json_array"])
            
            for item in code_json_array:
                result += item.get("answer", "")
            
            result += "\n"
    except (IOError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"处理听后选择失败: {e}")
    
    return result


def process_listening_answer(extract_dir: str, file_path: str) -> str:
    """
    处理听后回答题型
    
    Args:
        extract_dir: 解压目录
        file_path: 文件路径
    
    Returns:
        str: 处理后的答案文本
    """
    result = ""
    content_path = os.path.join(extract_dir, "content.json")
    
    try:
        with open(content_path, "r", encoding="utf-8") as f:
            content_data = json.load(f)
            questions = content_data["info"]["question"]
            
            for item in questions:
                std = item.get("std", [])
                answer1 = std[0].get("value", "").replace("</br>", "") if len(std) > 0 else ""
                answer2 = std[1].get("value", "").replace("</br>", "") if len(std) > 1 else ""
                answer3 = std[2].get("value", "").replace("</br>", "") if len(std) > 2 else ""
                keywords = item.get("keywords", "")
                
                result += f"第一答案:{answer1} 第二答案:{answer2} 第三答案:{answer3} 关键词:{keywords}\n"
    except (IOError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"处理听后回答失败: {e}")
    
    return result


def process_listening_retelling(extract_dir: str, file_path: str) -> str:
    """
    处理听后转述题型
    
    Args:
        extract_dir: 解压目录
        file_path: 文件路径
    
    Returns:
        str: 处理后的答案文本
    """
    result = ""
    content_path = os.path.join(extract_dir, "content.json")
    
    try:
        with open(content_path, "r", encoding="utf-8") as f:
            content_data = json.load(f)
            info = content_data["info"]
            std = info.get("std", [])
            
            if len(std) > 0:
                answer1 = std[0].get("value", "").replace("<i>", "").replace("</i>", "")
                result += f"第一答案:{answer1}\n"
            
            if len(std) > 1:
                answer2 = std[1].get("value", "").replace("<i>", "").replace("</i>", "")
                result += f"第二答案:{answer2}\n"
            
            if len(std) > 2:
                answer3 = std[2].get("value", "").replace("<i>", "").replace("</i>", "")
                result += f"第三答案:{answer3}\n"
    except (IOError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"处理听后转述失败: {e}")
    
    return result


def process_reading_aloud(extract_dir: str, file_path: str) -> str:
    """
    处理短文朗读题型
    
    Args:
        extract_dir: 解压目录
        file_path: 文件路径
    
    Returns:
        str: 处理后的答案文本
    """
    result = ""
    content_path = os.path.join(extract_dir, "content.json")
    
    try:
        with open(content_path, "r", encoding="utf-8") as f:
            content_data = json.load(f)
            value = content_data["info"].get("value", "")
            result = value.replace("<p>", "").replace("</p>", "")
    except (IOError, json.JSONDecodeError, KeyError) as e:
        print(f"处理短文朗读失败: {e}")
    
    return result


def process_question_group(group_name: str, url: str, temp_dir: str) -> str:
    """
    处理一个问题组的所有题目
    
    Args:
        group_name: 问题组名称
        url: 问题组ZIP文件URL
        temp_dir: 临时目录
    
    Returns:
        str: 处理后的答案文本
    """
    result = f"{group_name}:\n"
    
    # 下载ZIP文件
    zip_filename = url.split("/")[-1]
    zip_path = os.path.join(temp_dir, zip_filename)
    
    if not download_file(url, zip_path):
        return result + "下载失败\n"
    
    # 读取ZIP文件内容生成密码
    try:
        with open(zip_path, "rb") as f:
            zip_data = f.read()
        password = generate_zip_password(zip_data)
    except (IOError, ValueError) as e:
        print(f"生成密码失败: {e}")
        return result + "密码生成失败\n"
    
    # 解压ZIP文件
    extract_dir = os.path.join(temp_dir, zip_filename.split(".")[0])
    if not extract_zip(zip_path, extract_dir, password):
        return result + "解压失败\n"
    
    # 根据题型处理内容
    normalized_group_name = group_name.replace(" ", "")
    
    if normalized_group_name == "听后选择":
        result += process_listening_choice(extract_dir, zip_path)
    elif normalized_group_name == "听后回答":
        result += process_listening_answer(extract_dir, zip_path)
    elif normalized_group_name == "听后转述":
        result += process_listening_retelling(extract_dir, zip_path)
    elif normalized_group_name == "短文朗读":
        result += process_reading_aloud(extract_dir, zip_path)
    else:
        result += f"未知题型: {group_name}\n"
    
    return result + "\n"


def save_answers_to_file(homework: Dict[str, Any], output_path: str, temp_dir: str) -> bool:
    """
    保存作业答案到文件
    
    Args:
        homework: 作业数据
        output_path: 输出文件路径
        temp_dir: 临时目录
    
    Returns:
        bool: 保存是否成功
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"作业名称: {homework['name']}\n\n")
            
            for group_name, urls in homework["contents"].items():
                f.write(f"{group_name}:\n")
                
                for url in urls:
                    answer_text = process_question_group(group_name, url, temp_dir)
                    f.write(answer_text)
        
        return True
    except IOError as e:
        print(f"保存答案文件失败: {e}")
        return False


def main():
    """主函数"""
    print("欢迎使用作业答案生成器v1.0(Beta)")
    print("ets.exe cracked by leitianshuo1337")
    print("This program -> Copyright(©) 2025 leitianshuo1337, All Rights Reserved")
    print("ets.exe -> Copyright(©) 2019 ETS100, All Rights Reserved")
    
    # 获取用户输入
    try:
        phone = input("请输入手机号: ")
        password = getpass.getpass("请输入密码: ")
    except (KeyboardInterrupt, EOFError):
        print("\n用户取消输入")
        return
    
    # 登录并获取token
    print("正在登录...")
    token = login(phone=phone, password=password)
    if not token:
        return
    
    # 获取家长账户ID
    parent_account_id = get_parent_account_id(token=token)
    if not parent_account_id:
        return
    
    print("登录成功")
    
    # 获取作业列表
    print("正在获取作业列表...")
    homework_list = get_homework_urls(parent_account_id=parent_account_id, token=token)
    if not homework_list:
        print("获取作业列表失败")
        return
    
    # 显示作业列表
    print("作业列表:")
    for i, homework in enumerate(homework_list, 1):
        print(f"{i}. {homework['name']}")
    
    # 获取用户选择
    try:
        choice = int(input("请选择作业编号（0则为全部获取）: "))
    except ValueError:
        print("输入无效，请输入数字")
        return
    
    # 创建临时目录
    temp_dir = "./temp"
    try:
        os.makedirs(temp_dir, exist_ok=True)
    except OSError as e:
        print(f"创建临时目录失败: {e}")
        return
    
    print("正在生成答案...")
    
    # 处理选择的作业
    try:
        if choice == 0:
            # 处理所有作业
            for homework in homework_list:
                output_path = f"{homework['name']}_answer.txt"
                if save_answers_to_file(homework, output_path, temp_dir):
                    print(f"已生成: {output_path}")
        else:
            # 处理单个作业
            if 1 <= choice <= len(homework_list):
                homework = homework_list[choice - 1]
                output_path = f"{homework['name']}_answer.txt"
                if save_answers_to_file(homework, output_path, temp_dir):
                    print(f"已生成: {output_path}")
            else:
                print("选择的作业编号无效")
    except Exception as e:
        print(f"处理作业时发生错误: {e}")
    
    # 清理临时目录
    if not DEBUG_MODE:
        try:
            shutil.rmtree(temp_dir)
            print("临时文件已清理")
        except OSError as e:
            print(f"清理临时目录失败: {e}")
    
    print("答案生成完毕,请查看当前目录下的txt文件")


if __name__ == "__main__":
    main()