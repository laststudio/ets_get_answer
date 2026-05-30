import hashlib
import socket
import struct
import subprocess
import re
import requests
import time
import base64
import json
import os
import zipfile
import getpass
import shutil
import logging
import platform
import uuid
from typing import Dict, List, Tuple, Optional, Any, Union
import getmac

# 尝试导入Windows特定的库
try:
    import winreg
    import ctypes
    from ctypes import wintypes
    import win32con
    import win32api
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    winreg = None
    ctypes = None
    wintypes = None
    win32con = None
    win32api = None

# 尝试导入网络库
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

try:
    import netifaces
    NETIFACES_AVAILABLE = True
except ImportError:
    NETIFACES_AVAILABLE = False
    netifaces = None

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

# 跨平台配置 - 模拟的Windows注册表值
MOCK_REGISTRY_VALUES = {
    "ProductId": "00391-70000-00000-AA676",
    "MachineGuid": "e4917252-ba81-4174-a996-6945dad253c6",
    "InstallDate": "2023-10-31 20:48:29",
    "ComputerName": "LEITIANSHUO"
}

class CrossPlatformRegistry:
    """跨平台注册表访问类"""
    
    @staticmethod
    def get_system_info():
        """获取系统架构信息"""
        arch = platform.machine().lower()
        if arch in ['amd64', 'x86_64']:
            return 9  # AMD64
        elif arch in ['ia64']:
            return 6  # IA64
        else:
            return 0  # x86 or other

    @staticmethod
    def read_registry_value(key_path: str, value_name: str) -> str:
        """跨平台读取注册表值"""
        if WINDOWS_AVAILABLE:
            try:
                # Windows系统，使用真实的注册表
                system_arch = CrossPlatformRegistry.get_system_info()
                sam_desired = winreg.KEY_WOW64_64KEY if system_arch in (9, 6) else winreg.KEY_WOW64_32KEY
                
                if "Windows NT/CurrentVersion" in key_path:
                    hkey = winreg.HKEY_LOCAL_MACHINE
                    subkey = "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion"
                elif "Cryptography" in key_path:
                    hkey = winreg.HKEY_LOCAL_MACHINE
                    subkey = "SOFTWARE\\Microsoft\\Cryptography"
                elif "ETSKey" in key_path:
                    hkey = winreg.HKEY_LOCAL_MACHINE
                    subkey = "SOFTWARE\\ETSKey"
                else:
                    return ""
                
                key_handle = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ | sam_desired)
                value, regtype = winreg.QueryValueEx(key_handle, value_name)
                winreg.CloseKey(key_handle)
                
                if regtype == winreg.REG_SZ:
                    return str(value)
                else:
                    return ""
            except Exception as e:
                logger.error(f"读取Windows注册表失败: {e}")
                # 回退到模拟值
                return CrossPlatformRegistry._get_mock_value(value_name)
        else:
            # 非Windows系统，使用模拟值
            return CrossPlatformRegistry._get_mock_value(value_name)
    
    @staticmethod
    def _get_mock_value(value_name: str) -> str:
        """获取模拟的注册表值"""
        return MOCK_REGISTRY_VALUES.get(value_name, "")

# 定义跨平台的SYSTEM_INFO结构体
class CrossPlatformSystemInfo:
    """跨平台系统信息类"""
    
    def __init__(self):
        self.wProcessorArchitecture = CrossPlatformRegistry.get_system_info()

def calculate_md5(data):
    """计算字符串的MD5哈希值"""
    md5_hash = hashlib.md5(data.encode('utf-8')).hexdigest().upper()
    return md5_hash[8:24]  # 取中间16个字符

def get_active_network_interface_advanced():
    """
    高级网络接口检测（使用psutil和netifaces）
    """
    try:
        if not PSUTIL_AVAILABLE:
            return ""
        
        # 创建一个UDP socket连接到外部服务器
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("114.114.114.114", 53))
            local_ip = s.getsockname()[0]
        
        # 使用psutil查找对应IP地址的网络接口
        for interface_name, interface_addresses in psutil.net_if_addrs().items():
            for address in interface_addresses:
                if address.family == socket.AF_INET and address.address == local_ip:
                    # 找到对应的MAC地址
                    for addr in interface_addresses:
                        if hasattr(psutil, 'AF_LINK') and addr.family == psutil.AF_LINK:  # MAC地址
                            mac = addr.address.upper().replace(":", "-")
                            if mac != "00-00-00-00-00-00" and not mac.startswith("00-00-00"):
                                return mac
        
        # 如果上述方法失败，尝试使用netifaces库
        if NETIFACES_AVAILABLE:
            try:
                gateways = netifaces.gateways()
                if 'default' in gateways and netifaces.AF_INET in gateways['default']:
                    default_gateway = gateways['default'][netifaces.AF_INET]
                    interface_name = default_gateway[1]
                    
                    interface_info = netifaces.ifaddresses(interface_name)
                    if netifaces.AF_LINK in interface_info:
                        mac = interface_info[netifaces.AF_LINK][0]['addr'].upper().replace(":", "-")
                        if mac != "00-00-00-00-00-00" and not mac.startswith("00-00-00"):
                            return mac
            except Exception as e:
                logger.error(f"netifaces获取MAC地址失败: {e}")
        
        return ""
    except Exception as e:
        logger.error(f"高级网络接口检测失败: {e}")
        return ""

def get_active_network_interface_basic():
    """
    基础网络接口检测（跨平台兼容）
    """
    try:
        # 方法1：通过socket连接获取本地IP，然后查找对应的MAC
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("114.114.114.114", 53))
            local_ip = s.getsockname()[0]
        
        system_name = platform.system()
        
        if system_name == "Windows":
            # Windows系统使用ipconfig
            try:
                output = subprocess.check_output("ipconfig /all", shell=True, text=True)
                return parse_windows_ipconfig(output, local_ip)
            except:
                return get_fallback_mac_windows()
        
        elif system_name == "Darwin":  # macOS
            try:
                # 使用ifconfig获取MAC地址
                output = subprocess.check_output("ifconfig", shell=True, text=True)
                return parse_unix_ifconfig(output, local_ip)
            except:
                return get_fallback_mac_unix()
        
        elif system_name == "Linux":
            try:
                # 先尝试ip命令
                output = subprocess.check_output("ip addr show", shell=True, text=True)
                mac = parse_linux_ip_addr(output, local_ip)
                if mac:
                    return mac
                
                # 回退到ifconfig
                output = subprocess.check_output("ifconfig", shell=True, text=True)
                return parse_unix_ifconfig(output, local_ip)
            except:
                return get_fallback_mac_unix()
        
        else:
            # 其他系统，使用通用方法
            return get_fallback_mac_generic()
            
    except Exception as e:
        logger.error(f"基础网络接口检测失败: {e}")
        return get_fallback_mac_generic()

def parse_windows_ipconfig(output: str, target_ip: str) -> str:
    """解析Windows ipconfig输出"""
    try:
        lines = output.split('\n')
        current_adapter = ""
        found_ip = False
        
        for line in lines:
            line = line.strip()
            
            # 检测适配器名称
            if "适配器" in line or "adapter" in line.lower():
                current_adapter = line
                found_ip = False
                continue
            
            # 检测IP地址
            if target_ip in line and ("IPv4" in line or "IP Address" in line):
                found_ip = True
                continue
            
            # 如果找到了目标IP，寻找物理地址
            if found_ip and ("物理地址" in line or "Physical Address" in line):
                patterns = [
                    r"物理地址[\. ]*: ([\w-]+)",
                    r"Physical Address[\. ]*: ([\w-]+)"
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        mac = match.group(1).upper()
                        if mac != "00-00-00-00-00-00" and not mac.startswith("00-00-00"):
                            return mac
        
        return ""
    except Exception as e:
        logger.error(f"解析Windows ipconfig输出失败: {e}")
        return ""

def parse_unix_ifconfig(output: str, target_ip: str) -> str:
    """解析Unix系统ifconfig输出"""
    try:
        # 分割为各个接口
        interfaces = re.split(r'\n(?=\w)', output)
        
        for interface in interfaces:
            if target_ip in interface:
                # 查找MAC地址
                mac_patterns = [
                    r'ether\s+([a-fA-F0-9:]{17})',
                    r'HWaddr\s+([a-fA-F0-9:]{17})',
                    r'link/ether\s+([a-fA-F0-9:]{17})'
                ]
                
                for pattern in mac_patterns:
                    match = re.search(pattern, interface)
                    if match:
                        mac = match.group(1).upper().replace(":", "-")
                        if mac != "00-00-00-00-00-00" and not mac.startswith("00-00-00"):
                            return mac
        
        return ""
    except Exception as e:
        logger.error(f"解析Unix ifconfig输出失败: {e}")
        return ""

def parse_linux_ip_addr(output: str, target_ip: str) -> str:
    """解析Linux ip addr输出"""
    try:
        lines = output.split('\n')
        current_interface = ""
        found_ip = False
        
        for line in lines:
            line = line.strip()
            
            # 检测接口名称
            if re.match(r'^\d+:', line):
                current_interface = line
                found_ip = False
                continue
            
            # 检测IP地址
            if f"inet {target_ip}" in line:
                found_ip = True
                continue
            
            # 如果找到了目标IP，寻找MAC地址
            if found_ip and "link/ether" in line:
                match = re.search(r'link/ether\s+([a-fA-F0-9:]{17})', line)
                if match:
                    mac = match.group(1).upper().replace(":", "-")
                    if mac != "00-00-00-00-00-00" and not mac.startswith("00-00-00"):
                        return mac
        
        return ""
    except Exception as e:
        logger.error(f"解析Linux ip addr输出失败: {e}")
        return ""

def get_fallback_mac_windows() -> str:
    """Windows系统回退MAC获取方法"""
    try:
        output = subprocess.check_output("getmac /v /fo csv", shell=True, text=True)
        lines = output.strip().split('\n')[1:]  # 跳过标题行
        
        for line in lines:
            if '"Physical"' in line or '"物理"' in line:
                parts = line.split(',')
                if len(parts) >= 3:
                    mac = parts[2].strip('"').upper()
                    if mac != "00-00-00-00-00-00" and not mac.startswith("00-00-00"):
                        return mac.replace(":", "-")
        
        return ""
    except:
        return get_fallback_mac_generic()

def get_fallback_mac_unix() -> str:
    """Unix系统回退MAC获取方法"""
    try:
        # 尝试读取/sys/class/net目录
        if os.path.exists('/sys/class/net'):
            for interface in os.listdir('/sys/class/net'):
                if interface.startswith('lo'):  # 跳过回环接口
                    continue
                
                addr_file = f'/sys/class/net/{interface}/address'
                if os.path.exists(addr_file):
                    with open(addr_file, 'r') as f:
                        mac = f.read().strip().upper().replace(":", "-")
                        if mac != "00-00-00-00-00-00" and not mac.startswith("00-00-00"):
                            return mac
        
        return get_fallback_mac_generic()
    except:
        return get_fallback_mac_generic()

def get_fallback_mac_generic() -> str:
    """通用回退MAC获取方法"""
    try:
        # 使用uuid.getnode()获取MAC地址
        mac_int = uuid.getnode()
        mac_hex = format(mac_int, '012x')
        mac = '-'.join([mac_hex[i:i+2] for i in range(0, 12, 2)]).upper()
        
        if mac != "00-00-00-00-00-00" and not mac.startswith("00-00-00"):
            return mac
        
        # 如果还是失败，生成一个基于系统信息的伪MAC地址
        system_info = f"{platform.node()}{platform.system()}{platform.release()}"
        mac_hash = hashlib.md5(system_info.encode()).hexdigest()[:12]
        mac = '-'.join([mac_hash[i:i+2] for i in range(0, 12, 2)]).upper()
        
        # 确保第一个字节的最低位为0（表示单播地址）
        first_byte = int(mac[:2], 16)
        first_byte &= 0xFE  # 清除最低位
        first_byte |= 0x02  # 设置本地管理位
        mac = f"{first_byte:02X}" + mac[2:]
        
        return mac
    except:
        # 最终回退：返回一个固定的MAC地址
        return "02-00-00-00-00-01"

# def get_mac_address():
#     """
#     跨平台获取MAC地址
#     """
#     try:
#         # 首先尝试高级方法（使用第三方库）
#         if PSUTIL_AVAILABLE or NETIFACES_AVAILABLE:
#             mac = get_active_network_interface_advanced()
#             if mac:
#                 return mac
        
#         # 回退到基础方法（使用系统命令）
#         mac = get_active_network_interface_basic()
#         if mac:
#             return mac
        
#         # 最终回退
#         return get_fallback_mac_generic()
        
#     except Exception as e:
#         logger.error(f"获取MAC地址失败: {e}")
#         return get_fallback_mac_generic()

#debug
def get_mac_address():
    return getmac.get_mac_address().replace(":", "-")

def get_computer_name():
    """跨平台获取计算机名"""
    try:
        if WINDOWS_AVAILABLE and 'COMPUTERNAME' in os.environ:
            return os.environ['COMPUTERNAME']
        
        # 使用模拟值或系统方法
        computer_name = MOCK_REGISTRY_VALUES.get("ComputerName", "")
        if computer_name:
            return computer_name
        
        # 尝试其他方法
        return platform.node() or socket.gethostname() or "UNKNOWN"
    except:
        return "UNKNOWN"

def generate_machine_code():
    """生成机器码"""
    data = ""
    
    # 读取模拟或真实的注册表值
    data += CrossPlatformRegistry.read_registry_value("Windows NT/CurrentVersion", "ProductId")
    data += CrossPlatformRegistry.read_registry_value("Cryptography", "MachineGuid")
    data += CrossPlatformRegistry.read_registry_value("ETSKey", "InstallDate")
    
    # 获取MAC地址
    mac_address = get_mac_address()
    
    # 计算数据的MD5
    data_md5 = calculate_md5(data)
    
    # 计算MAC地址的MD5
    mac_md5 = calculate_md5(mac_address)
    
    # 组合机器码
    machine_code = data_md5 + "|" + mac_md5
    
    return machine_code

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
                    "device_code": generate_machine_code(),
                    "device_name": get_computer_name(),
                    "version": version,
                    "local_ip": "127.0.0.1",
                    "system": system,
                    "global_client_version": global_client_version,
                    "sign_response": sign_response,
                }
            }]
            
            response = self.send_request(f"{API_BASE_URL}/user/login", body_data)
            self.token = response[0]["body"]["token"]
            logger.info("登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {e}")
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
    
    def get_homework_list(self, limit: str = "10", system: str = "4", sign_response: int = 1, 
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


def process_homework(homework: Dict) -> bool:
    """
    处理单个作业
    
    Args:
        homework: 作业数据
        
    Returns:
        处理是否成功
    """
    try:
        filename = f"answer/{homework['name']}_answer.txt"
        
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


def hide_temp_directory():
    """隐藏临时目录（仅Windows系统有效）"""
    try:
        if WINDOWS_AVAILABLE and win32api and win32con:
            win32api.SetFileAttributes('./temp', win32con.FILE_ATTRIBUTE_HIDDEN)
    except Exception as e:
        logger.error(f"隐藏临时目录失败: {e}")


def show_system_info():
    """显示系统信息"""
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    print(f"Python版本: {platform.python_version()}")
    print(f"计算机名: {get_computer_name()}")
    
    # 显示可用的库
    libs = []
    if WINDOWS_AVAILABLE:
        libs.append("Windows API")
    if PSUTIL_AVAILABLE:
        libs.append("psutil")
    if NETIFACES_AVAILABLE:
        libs.append("netifaces")
    
    print(f"可用库: {', '.join(libs) if libs else '基础库'}")
    print("-" * 50)


def main():
    """主函数"""
    print("欢迎使用作业答案生成器v2.0(跨平台版本)")
    print("支持Windows、macOS、Linux等多种操作系统")
    print("ets.exe cracked by leitianshuo1337")
    print("This program -> Copyright(©) 2025 leitianshuo1337, All Rights Reserved")
    print("ets.exe -> Copyright(©) 2019 ETS100, All Rights Reserved")
    print("=" * 60)
    
    # 显示系统信息
    show_system_info()
    
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
    
    # 显示机器码信息
    machine_code = generate_machine_code()
    mac_address = get_mac_address()
    print(f"当前机器码: {machine_code}")
    print(f"检测到的活跃MAC地址: {mac_address}")
    
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
        os.makedirs("./answer", exist_ok=True)
        hide_temp_directory()
        
        if choice == 0:
            # 处理所有作业
            for homework in homework_list:
                process_homework(homework)
        else:
            # 处理选中的作业
            selected_homework = homework_list[choice - 1]
            process_homework(selected_homework)
        
        print("答案生成完毕,请查看answer目录下的txt文件")
    except Exception as e:
        logger.error(f"处理作业时出错: {e}")
        print("处理作业时发生错误")
    finally:
        # 清理临时文件
        if not DEBUG_MODE and os.path.exists("./temp"):
            shutil.rmtree("./temp")


def test_hwid():
    """测试硬件ID生成功能"""
    print("测试硬件ID生成功能...")
    print("=" * 50)
    
    show_system_info()
    
    print("正在生成机器码...")
    
    # 显示注册表值
    print("注册表值:")
    print(f"  ProductId: {CrossPlatformRegistry.read_registry_value('Windows NT/CurrentVersion', 'ProductId')}")
    print(f"  MachineGuid: {CrossPlatformRegistry.read_registry_value('Cryptography', 'MachineGuid')}")
    print(f"  InstallDate: {CrossPlatformRegistry.read_registry_value('ETSKey', 'InstallDate')}")
    print()
    
    # 获取详细的MAC地址信息
    mac_address = get_mac_address()
    print(f"检测到的活跃MAC地址: {mac_address}")
    
    machine_code = generate_machine_code()
    
    if not machine_code:
        print("生成机器码失败!")
        return False
    
    print(f"生成的机器码: {machine_code}")
    
    # 分析机器码组成
    parts = machine_code.split("|")
    if len(parts) == 2:
        print(f"数据MD5: {parts[0]}")
        print(f"MAC MD5: {parts[1]}")
    
    return True


def test_network():
    """测试网络连接功能"""
    print("测试网络连接功能...")
    print("=" * 50)
    
    try:
        # 测试基本网络连接
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(5)
            s.connect(("114.114.114.114", 53))
            local_ip = s.getsockname()[0]
            print(f"本地IP地址: {local_ip}")
        
        # 测试API连接
        print("测试API连接...")
        response = requests.get("https://api.ets100.com", timeout=10)
        print(f"API连接状态: {response.status_code}")
        
        # 测试CDN连接
        print("测试CDN连接...")
        response = requests.get("https://cdn.subject.ets100.com", timeout=10)
        print(f"CDN连接状态: {response.status_code}")
        
        print("网络连接测试完成")
        return True
        
    except Exception as e:
        print(f"网络连接测试失败: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    try:
        # 检查命令行参数
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if arg == "--test-hwid":
                test_hwid()
            elif arg == "--test-network":
                test_network()
            elif arg == "--system-info":
                show_system_info()
            elif arg == "--help":
                print("可用参数:")
                print("  --test-hwid     测试硬件ID生成")
                print("  --test-network  测试网络连接")
                print("  --system-info   显示系统信息")
                print("  --help          显示帮助信息")
            else:
                print(f"未知参数: {arg}")
                print("使用 --help 查看可用参数")
        else:
            main()
        
        # 跨平台的暂停
        if platform.system() == "Windows":
            input("\n按任意键退出...")
        else:
            input("\n按回车键退出...")
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")
        print("如需详细信息，请查看日志")
        
        if platform.system() == "Windows":
            input("\n按任意键退出...")
        else:
            input("\n按回车键退出...")