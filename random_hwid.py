# -*- coding: utf-8 -*-
# 宝贝这个模块用于生成随机机器码喵~
# 与原 hwid.py 保持相同的函数签名，方便替换使用喵~

import uuid


def generate_machine_code():
    """生成随机机器码
    
    格式：{16位随机大写字母数字}|{16位随机大写字母数字}
    与原 hwid.py 生成的格式保持一致喵~
    
    Returns:
        str: 随机生成的机器码，格式为 XXXXXXXXXXXXXXXX|XXXXXXXXXXXXXXXX
    """
    # 使用 uuid4 生成两个随机的 16 位字符串，并转换为大写
    random_part1 = uuid.uuid4().hex[:16].upper()
    random_part2 = uuid.uuid4().hex[:16].upper()
    
    # 组合成与原格式一致的机器码
    machine_code = f"{random_part1}|{random_part2}"
    
    return machine_code


# 保留原函数的函数签名，方便直接替换使用喵~
__all__ = ['generate_machine_code']