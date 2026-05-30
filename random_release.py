import requests
import time
import hashlib
import base64
import json
import os
import zipfile
import getpass
import shutil
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
import random_hwid
import win32con
import win32api

# 配置日志
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局配置
DEBUG_MODE = False
API_BASE_URL = "https://api.ets100.com"
CDN_BASE_URL = "https://cdn.subject.ets100.com"
PID = "grlx"
SECRET_KEY = "555ffbe95ccf4e9535a110170b445ab8"
FOOTER_SIZE = 336


class ETSClient:
    """ETS客户端类，用于处理与ETS服务器的交互"""
    
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.parent_account_id = None
        self.headers = {
            "Host": "api.ets100.com",
            "User-Agent": "libcurl-agent/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*"
        }
    
    def make_signature(self, content: str, timestamp: int) -> str:
        """
        生成请求签名
        
        Args:
            content: 请求内容
            timestamp: 时间戳
            
        Returns:
            MD5签名字符串
        """
        try:
            sign_string = f"{PID}{timestamp}{content}{SECRET_KEY}"
            md5_hash = hashlib.md5(sign_string.encode("utf-8"))
            return md5_hash.hexdigest()
        except Exception as e:
            logger.error(f"生成签名时出错: {e}")
            raise
    
    def send_request(self, endpoint: str, body_data: List[Dict]) -> Dict:
        """
        发送请求到ETS服务器
        
        Args:
            endpoint: API端点
            body_data: 请求体数据
            
        Returns:
            服务器响应数据
        """
        try:
            # 准备请求数据
            body_json = json.dumps(body_data, separators=(',', ':'), ensure_ascii=False)
            body_b64 = base64.b64encode(body_json.encode("utf-8")).decode("utf-8")
            timestamp = int(time.time())
            
            # 构建请求头
            headers = self.headers.copy()
            headers["Host"] = endpoint.split("/")[2] if "://" in endpoint else "api.ets100.com"
            
            # 构建请求负载
            payload = {
                "body": body_b64,
                "head": {
                    "version": "1.0",
                    "sign": self.make_signature(content=body_b64, timestamp=timestamp),
                    "pid": PID,
                    "time": timestamp,
                }
            }
            
            payload_json = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
            
            # 发送请求
            response = self.session.post(
                url=endpoint,
                data=payload_json,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"处理请求时出错: {e}")
            raise
    

    def login(self, phone: str, password: str, system: str = "4", sign_response: int = 1, 
              version: str = "3", global_client_version: str = "", sn: str = "test") -> bool:
        """
        登录ETS系统
        
        Args:
            phone: 手机号
            password: 密码
            device_code: 设备代码
            device_name: 设备名称
            system: 系统版本
            sign_response: 签名响应
            version: 客户端版本
            global_client_version: 全局客户端版本
            sn: 序列号
            
        Returns:
            登录是否成功
        """
        try:
            body_data = [{
                "r": "user/login",
                "params": {
                    "sn": sn,
                    "phone": phone,
                    "password": password,
                    "device_code": random_hwid.generate_machine_code(),
                    "device_name": os.environ['COMPUTERNAME'],
                    "version": version,
                    "local_ip": "127.0.0.1",
                    "system": system,
                    "global_client_version": global_client_version,
                    "sign_response": sign_response,
                }
            }]
            # sn以及一些其他信息不应该硬编码，推荐更改
            
            response = self.send_request(f"{API_BASE_URL}/user/login", body_data)
            if response[0]["code"] == 0:
                self.token = response[0]["body"]["token"]
            elif response[0]["code"] == 30014:
                self.bind_device(phone = phone, password = password, device_name = os.environ['COMPUTERNAME'])
            else:
                raise ValueError(f"登录失败，服务器返回错误码: {response[0]['code']}")
            logger.info("登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False
    
    def bind_device(self, phone: str, password: str, system: str = "4", sign_response: int = 1, 
                    email: str = "", code: str = "0", version: str = "2", device_name: str = "1337", 
                    local_ip: str = "127.0.0.1", global_client_version: str = "", sn: str = "test") -> bool:
        """
        绑定设备到账户

        Args:
            phone: 手机号
            password: 密码
            system: 系统版本
            sign_response: 签名响应
            version: 客户端版本
            global_client_version: 全局客户端版本
            sn: 序列号
            device_name: 设备名称
            local_ip: 本地IP
            email: 邮箱
            code: 验证码
        
        Returns:
            绑定是否成功
        """
        # 在login判断之后，应该调用/user/info接口，获取用户信息，这里简写了，没太大必要

        try:
            body_data = [{
                "r": "user/rebind-code",
                "params": {
                    "sn": sn,
                    "phone": phone,
                    "email": email,
                    "password": password,
                    "code": code,
                    "version": version,
                    "device_name": device_name,
                    "device_code": random_hwid.generate_machine_code(),
                    "local_ip": local_ip,
                    "system": system,
                    "global_client_version": global_client_version,
                    "sign_response": sign_response
                }
            }]

            response = self.send_request(f"{API_BASE_URL}/user/rebind-code", body_data)
            self.token = response[0]["body"]["token"]
            logger.info("设备绑定成功")
            return True
        except Exception as e:
            logger.error(f"设备绑定失败: {e}")
            return False

    def get_parent_account_id(self, system: str = "4", sign_response: int = 1, 
                             version: str = "2", global_client_version: str = "", sn: str = "test") -> Optional[str]:
        """
        获取父账户ID
        
        Args:
            system: 系统版本
            sign_response: 签名响应
            version: 客户端版本
            global_client_version: 全局客户端版本
            sn: 序列号
            
        Returns:
            父账户ID或None
        """
        try:
            if not self.token:
                raise ValueError("未登录，请先登录")
                
            body_data = [{
                "r": "m/ecard/list",
                "params": {
                    "sn": sn,
                    "token": self.token,
                    "version": version,
                    "system": system,
                    "global_client_version": global_client_version,
                    "sign_response": sign_response,
                }
            }]
            
            response = self.send_request(f"{API_BASE_URL}/m/ecard/list", body_data)
            self.parent_account_id = response[0]["body"]["0"]["parent_id"]
            return self.parent_account_id
        except Exception as e:
            logger.error(f"获取父账户ID失败: {e}")
            return None
    
    def get_homework_list(self, limit: str = "0", system: str = "4", sign_response: int = 1, 
                         version: str = "2", global_client_version: str = "5.4.5", sn: str = "test") -> Optional[Dict]:
        """
        获取作业列表
        
        Args:
            limit: 限制数量
            system: 系统版本
            sign_response: 签名响应
            version: 客户端版本
            global_client_version: 全局客户端版本
            sn: 序列号
            
        Returns:
            作业列表数据或None
        """
        try:
            if not self.token or not self.parent_account_id:
                raise ValueError("未登录或未获取父账户ID")
                
            body_data = [{
                "r": "g/homework/list",
                "params": {
                    "sn": sn,
                    "token": self.token,
                    "parent_account_id": self.parent_account_id,
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
            }]
            
            response = self.send_request(f"{API_BASE_URL}/g/homework/list", body_data)
            return response[0]["body"]
        except Exception as e:
            logger.error(f"获取作业列表失败: {e}")
            return None
    
    def get_homework_urls(self) -> List[Dict]:
        """
        获取作业URL列表
        
        Returns:
            作业URL列表
        """
        try:
            homework_data = self.get_homework_list()
            if not homework_data:
                return []
                
            base_url = homework_data["base_url"]
            homework_items = homework_data["data"]
            homework_list = []
            
            for item in homework_items:
                zip_info = item["struct"]["contents"]
                grouped_content = {}
                
                for info in zip_info:
                    group_name = info["group_name"]
                    url = info["url"]
                    full_url = base_url + url
                    
                    if group_name in grouped_content:
                        grouped_content[group_name].append(full_url)
                    else:
                        grouped_content[group_name] = [full_url]
                
                homework_list.append({
                    "name": item["name"],
                    "contents": grouped_content
                })
            
            return homework_list
        except Exception as e:
            logger.error(f"获取作业URL失败: {e}")
            return []


class ZipProcessor:
    """ZIP文件处理器类"""
    
    @staticmethod
    def generate_zip_password(zip_data: bytes) -> str:
        """
        生成ZIP文件密码
        
        Args:
            zip_data: ZIP文件数据
            
        Returns:
            ZIP文件密码
            
        Raises:
            ValueError: 当文件数据无效时
        """
        try:
            if len(zip_data) < FOOTER_SIZE:
                raise ValueError("文件数据太小")
            
            # 提取尾部336字节
            footer = zip_data[-FOOTER_SIZE:]
            
            # 验证签名
            valid_signature = (
                footer[:8] == b'MSTCHINA' or 
                footer[144:149] == b'EPLAT'
            )
            
            if not valid_signature:
                raise ValueError("无效的文件签名")
            
            # 提取128字节种子数据
            seed = footer[16:144]
            
            # 计算第一重MD5
            first_md5 = hashlib.md5(seed).digest()
            first_hex = first_md5.hex().upper()
            
            # 计算第二重MD5
            second_md5 = hashlib.md5(first_hex.encode('ascii')).digest()
            second_hex = second_md5.hex().upper()
            
            # 拼接最终密码
            return first_hex + second_hex
        except Exception as e:
            logger.error(f"生成ZIP密码失败: {e}")
            raise
    
    @staticmethod
    def download_and_extract_zip(url: str, temp_dir: str = "./temp") -> Optional[str]:
        """
        下载并解压ZIP文件
        
        Args:
            url: ZIP文件URL
            temp_dir: 临时目录路径
            
        Returns:
            解压后的目录路径或None
        """
        try:
            os.makedirs(temp_dir, exist_ok=True)
            
            # 下载文件
            headers = {
                "Host": "cdn.subject.ets100.com",
                "User-Agent": "libcurl-agent/1.0",
                "Accept": "*/*"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            zip_data = response.content
            
            # 保存ZIP文件
            zip_filename = url.split("/")[-1]
            zip_path = os.path.join(temp_dir, zip_filename)
            
            with open(zip_path, "wb") as f:
                f.write(zip_data)
            
            # 生成密码并解压
            extract_dir = os.path.join(temp_dir, zip_filename.split(".")[0])
            password = ZipProcessor.generate_zip_password(zip_data)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir, pwd=password.encode("utf-8"))
            
            return extract_dir
        except Exception as e:
            logger.error(f"下载和解压ZIP文件失败: {e}")
            return None


class AnswerExtractor:
    """答案提取器类"""
    
    @staticmethod
    def extract_listen_choice_answer(extract_dir: str) -> str:
        """
        提取听后选择题答案
        
        Args:
            extract_dir: 解压目录路径
            
        Returns:
            答案字符串
        """
        try:
            answer_file_path = os.path.join(extract_dir, "info.json")
            with open(answer_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                code_json_array = json.loads(data[1]["code_json_array"])
                
                answers = ""
                for item in code_json_array:
                    answers += item["answer"]
                
                return answers
        except Exception as e:
            logger.error(f"提取听后选择题答案失败: {e}")
            return ""
    
    @staticmethod
    def extract_listen_answer_answer(extract_dir: str) -> str:
        """
        提取听后回答题答案
        
        Args:
            extract_dir: 解压目录路径
            
        Returns:
            答案字符串
        """
        try:
            answer_file_path = os.path.join(extract_dir, "content.json")
            with open(answer_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                questions = data["info"]["question"]
                
                answers = ""
                for item in questions:
                    answer1 = item["std"][0]["value"].replace("</br>", "")
                    answer2 = item["std"][1]["value"].replace("</br>", "") if len(item["std"]) > 1 else ""
                    answer3 = item["std"][2]["value"].replace("</br>", "") if len(item["std"]) > 2 else ""
                    keywords = item.get("keywords", "")
                    
                    answers += f"(1):{answer1}\n(2):{answer2}\n(3):{answer3}\n关键词:{keywords}\n"
                
                return answers
        except Exception as e:
            logger.error(f"提取听后回答题答案失败: {e}")
            return ""
    
    @staticmethod
    def extract_listen_retell_answer(extract_dir: str) -> str:
        """
        提取听后转述题答案
        
        Args:
            extract_dir: 解压目录路径
            
        Returns:
            答案字符串
        """
        try:
            answer_file_path = os.path.join(extract_dir, "content.json")
            with open(answer_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                info = data["info"]
                
                answers = ""
                try:
                    answer1 = info["std"][0]["value"].replace("<i>", "").replace("</i>", "")
                    answer2 = info["std"][1]["value"].replace("<i>", "").replace("</i>", "") if len(info["std"]) > 1 else ""
                    answer3 = info["std"][2]["value"].replace("<i>", "").replace("</i>", "") if len(info["std"]) > 2 else ""
                    
                    answers = f"(1):{answer1}\n\n(2):{answer2}\n\n(3):{answer3}\n\n"
                except (IndexError, KeyError):
                    # 处理可能的标准答案数量不足的情况
                    answer1 = info["std"][0]["value"].replace("<i>", "").replace("</i>", "")
                    answers = f"(1):{answer1}\n"
                
                return answers
        except Exception as e:
            logger.error(f"提取听后转述题答案失败: {e}")
            return ""
    
    @staticmethod
    def extract_read_aloud_answer(extract_dir: str) -> str:
        """
        提取短文朗读题答案
        
        Args:
            extract_dir: 解压目录路径
            
        Returns:
            答案字符串
        """
        try:
            answer_file_path = os.path.join(extract_dir, "content.json")
            with open(answer_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                value = data["info"]["value"].replace("<p>", "").replace("</p>", "")
                return value
        except Exception as e:
            logger.error(f"提取短文朗读题答案失败: {e}")
            return ""
    
    @staticmethod
    def extract_answers(extract_dir: str, question_type: str) -> str:
        """
        根据题型提取答案
        
        Args:
            extract_dir: 解压目录路径
            question_type: 题型名称
            
        Returns:
            答案字符串
        """
        try:
            normalized_type = question_type.replace(" ", "")
            
            if normalized_type == "听后选择":
                return AnswerExtractor.extract_listen_choice_answer(extract_dir)
            elif normalized_type == "听后回答":
                return AnswerExtractor.extract_listen_answer_answer(extract_dir)
            elif normalized_type == "听后转述":
                return AnswerExtractor.extract_listen_retell_answer(extract_dir)
            elif normalized_type == "短文朗读":
                return AnswerExtractor.extract_read_aloud_answer(extract_dir)
            else:
                logger.warning(f"未知题型: {question_type}")
                return ""
        except Exception as e:
            logger.error(f"提取答案失败: {e}")
            return ""


def save_credentials(phone: str, password: str) -> bool:
    """
    保存登录凭据到文件
    
    Args:
        phone: 手机号
        password: 密码
        
    Returns:
        保存是否成功
    """
    try:
        credentials = {
            "phone": phone,
            "password": password
        }
        
        with open("pwd.json", "w", encoding="utf-8") as f:
            json.dump(credentials, f)
        
        return True
    except Exception as e:
        logger.error(f"保存凭据失败: {e}")
        return False


def load_credentials() -> Optional[Tuple[str, str]]:
    """
    从文件加载登录凭据
    
    Returns:
        手机号和密码元组或None
    """
    try:
        if os.path.exists("pwd.json"):
            with open("pwd.json", "r", encoding="utf-8") as f:
                credentials = json.load(f)
                return credentials["phone"], credentials["password"]
        return None
    except Exception as e:
        logger.error(f"加载凭据失败: {e}")
        return None


def main():
    """主函数"""
    print("欢迎使用作业答案生成器v1.0(Release)")
    print("需要在计算机上安装ets本体或者进行特殊的修复工作")
    print("ets.exe cracked by leitianshuo1337")
    print("This program -> Copyright(©) 2025 leitianshuo1337, All Rights Reserved")
    print("ets.exe -> Copyright(©) 2019 ETS100, All Rights Reserved")
    
    # 初始化客户端
    client = ETSClient()
    
    # 尝试加载保存的凭据
    credentials = load_credentials()
    if credentials:
        phone, password = credentials
        print("检测到保存的凭据，使用保存的账号登录")
    else:
        # 获取用户输入
        phone = input("请输入手机号: ")
        password = getpass.getpass("请输入密码(密码不会显示): ")
        save_option = input("是否保存密码以便下次使用(y/n): ").lower()
        
        if save_option == 'y':
            if save_credentials(phone, password):
                print("凭据已保存")
            else:
                print("凭据保存失败")
    
    # 登录
    print("正在登录...")
    if not client.login(phone, password):
        print("登录失败，请检查凭据后重试")
        return
    
    # 获取父账户ID
    parent_id = client.get_parent_account_id()
    if not parent_id:
        print("获取父账户ID失败")
        return
    
    print("登录成功")
    
    # 获取作业列表
    print("正在获取作业列表...")
    homework_list = client.get_homework_urls()
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
        if choice < 0 or choice > len(homework_list):
            print("无效的选择")
            return
    except ValueError:
        print("请输入有效的数字")
        return
    
    # 处理作业
    print("正在生成答案...")
    try:
        os.makedirs("./temp", exist_ok=True)
        win32api.SetFileAttributes('./temp', win32con.FILE_ATTRIBUTE_HIDDEN)
        
        if choice == 0:
            # 处理所有作业
            for homework in homework_list:
                process_homework(homework)
        else:
            # 处理选中的作业
            selected_homework = homework_list[choice - 1]
            process_homework(selected_homework)
        
        print("答案生成完毕,请查看当前目录下的txt文件")
    except Exception as e:
        logger.error(f"处理作业时出错: {e}")
        print("处理作业时发生错误")
    finally:
        # 清理临时文件
        if not DEBUG_MODE and os.path.exists("./temp"):
            shutil.rmtree("./temp")


def process_homework(homework: Dict) -> bool:
    """
    处理单个作业
    
    Args:
        homework: 作业数据
        
    Returns:
        处理是否成功
    """
    try:
        filename = f"{homework['name']}_answer.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"{homework['name']}答案:\n\n")
            for question_type, urls in homework["contents"].items():
                f.write(f"{question_type}:\n")
                
                for url in urls:
                    # 下载并解压ZIP文件
                    extract_dir = ZipProcessor.download_and_extract_zip(url)
                    if not extract_dir:
                        f.write("获取答案失败\n\n")
                        continue
                    
                    # 提取答案
                    answer = AnswerExtractor.extract_answers(extract_dir, question_type)
                    f.write(answer)
                    f.write("\n")
                
                f.write("\n")
        
        return True
    except Exception as e:
        logger.error(f"处理作业失败: {e}")
        return False


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print("程序运行出错，请查看日志获取详细信息")