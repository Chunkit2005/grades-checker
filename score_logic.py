# score_logic.py (Complete Updated Version)
import requests
import hashlib
import json
import os
from PIL import Image
from bs4 import BeautifulSoup
import re
import base64
import time
import random

# --- DdddOcr 导入 ---
import ddddocr

# --- 配置信息 ---
CREDENTIALS_FILE = "user_credentials.json"
BASE_URL = "https://jwxs.tiangong.edu.cn"
LOGIN_PAGE_URL = f"{BASE_URL}/login"
LOGIN_URL = f"{BASE_URL}/j_spring_security_check"
CAPTCHA_URL = f"{BASE_URL}/img/captcha.jpg"
GRADES_INDEX_PAGE_URL = f"{BASE_URL}/student/integratedQuery/scoreQuery/thisTermScores/index"
USER_INDEX_PAGE_URL = f"{BASE_URL}/index"
ACADEMIC_INFO_URL = f"{BASE_URL}/main/academicInfo" # --- 获取GPA和课程数的API URL ---

# --- MD5 加密函数（从JavaScript代码转换而来）---
def hex_md5(s, ver=None):
    s_utf8 = s.encode('utf-8')
    if ver == "1.8":
        salted_s = s_utf8
    else:
        salted_s = s_utf8 + "{Urp602019}".encode('utf-8')
    return hashlib.md5(salted_s).hexdigest()

def get_hashed_password_for_login(raw_password):
    """用于登录请求的密码哈希"""
    first_hash = hex_md5(raw_password)
    second_hash = hex_md5(raw_password, "1.8")
    return f"{first_hash}*{second_hash}"

def get_hashed_password_for_storage(raw_password):
    """用于本地存储的密码哈希，避免明文存储"""
    return hashlib.sha256(raw_password.encode('utf-8')).hexdigest()

# --- 用户凭证管理函数 ---
def save_credentials(username, hashed_password_for_storage):
    data = {
        "username": username,
        "hashed_password_for_storage": hashed_password_for_storage
    }
    try:
        save_path = os.path.join(os.path.dirname(__file__), CREDENTIALS_FILE)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        print(f"[{time.strftime('%H:%M:%S')}] 登录信息已保存到 {save_path}")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 保存登录信息失败: {e}")

def load_credentials():
    load_path = os.path.join(os.path.dirname(__file__), CREDENTIALS_FILE)
    if os.path.exists(load_path):
        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"[{time.strftime('%H:%M:%S')}] 从 {load_path} 加载登录信息成功。")
            return data.get("username"), data.get("hashed_password_for_storage")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 加载登录信息失败，文件可能已损坏: {e}")
            os.remove(load_path)
            return None, None
    return None, None

# --- DdddOcr 客户端初始化 ---
_ddddocr_client = None
def get_ddddocr_client():
    global _ddddocr_client
    if _ddddocr_client is None:
        _ddddocr_client = ddddocr.DdddOcr()
        _ddddocr_client.set_ranges("abcdefghijklmnopqrstuvwxyz0123456789")
        print(f"[{time.strftime('%H:%M:%S')}] DdddOcr 客户端已初始化。")
    return _ddddocr_client

def recognize_captcha_with_ddddocr(image_bytes):
    try:
        ocr_client = get_ddddocr_client()
        recognized_code = ocr_client.classification(image_bytes)
        if recognized_code:
            print(f"[{time.strftime('%H:%M:%S')}] DdddOcr 识别成功，结果: {recognized_code}")
            return recognized_code
        return None
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%M')}] 调用 DdddOcr 识别验证码时发生错误: {e}")
        return None

# --- 验证码获取函数 ---
def get_captcha_code(session, max_retries=5):
    for attempt in range(1, max_retries + 1):
        print(f"[{time.strftime('%H:%M:%S')}] 尝试识别验证码 (第 {attempt} 次)...")
        try:
            captcha_response = session.get(CAPTCHA_URL, stream=True, timeout=5)
            captcha_response.raise_for_status()
            image_bytes = captcha_response.content
            recognized_code = recognize_captcha_with_ddddocr(image_bytes)
            if recognized_code and 3 <= len(recognized_code) <= 6:
                return recognized_code
        except requests.exceptions.RequestException as e:
            print(f"[{time.strftime('%H:%M:%S')}] 下载验证码失败: {e}")
        if attempt < max_retries:
            time.sleep(random.uniform(1, 2))
    print(f"[{time.strftime('%H:%M:%S')}] 验证码识别最终失败。")
    return None

# --- 登录函数 ---
def login(session, username, raw_password, dynamic_token, max_retries=5):
    hashed_password_for_login = get_hashed_password_for_login(raw_password)
    for attempt in range(1, max_retries + 1):
        print(f"\n[{time.strftime('%H:%M:%S')}] 尝试登录 (第 {attempt} 次)...")
        captcha_code = get_captcha_code(session)
        if not captcha_code: return False
        login_data = {"tokenValue": dynamic_token, "j_username": username, "j_password": hashed_password_for_login, "j_captcha": captcha_code}
        try:
            response = session.post(LOGIN_URL, data=login_data, allow_redirects=False, timeout=10)
            response.raise_for_status()
            if response.status_code == 302 and "/index" in response.headers.get("location", ""):
                print(f"[{time.strftime('%H:%M:%S')}] 登录成功！")
                return True
            else:
                error_message = "验证码或密码错误" if "验证码输入错误" in response.text or "用户名或密码错误" in response.text else "未知登录错误"
                print(f"[{time.strftime('%H:%M:%S')}] 登录失败: {error_message}")
                if "验证码" in error_message:
                    new_token = get_dynamic_token(session)
                    if new_token: dynamic_token = new_token
                time.sleep(random.uniform(2, 4))
        except requests.exceptions.RequestException as e:
            print(f"[{time.strftime('%H:%M:%S')}] 登录请求失败: {e}")
            time.sleep(random.uniform(2, 4))
    print(f"[{time.strftime('%H:%M:%S')}] 登录最终失败。")
    return False

# --- 获取动态 Token 函数 ---
def get_dynamic_token(session):
    print(f"[{time.strftime('%H:%M:%S')}] 正在获取动态tokenValue...")
    try:
        response = session.get(LOGIN_PAGE_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        token_input = soup.find('input', {'name': 'tokenValue'})
        if token_input and 'value' in token_input.attrs:
            token = token_input['value']
            print(f"[{time.strftime('%H:%M:%S')}] 成功获取动态tokenValue: {token}")
            return token
        return None
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取登录页面失败: {e}")
        return None

# --- 获取用户姓名函数 ---
def get_user_name(session_obj):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] 尝试获取用户姓名...")
        response = session_obj.get(USER_INDEX_PAGE_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        user_info_span = soup.find('span', class_='user-info')
        if user_info_span:
            user_name = user_info_span.get_text(strip=True).replace("欢迎您，", "").strip()
            if user_name:
                print(f"[{time.strftime('%H:%M:%S')}] 成功获取用户姓名: {user_name}")
                return user_name
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 解析用户姓名失败: {e}")
    return "同学"

# --- [修改后] 获取学业信息函数 ---
def fetch_academic_info(session_obj, max_retries=5, delay=2):
    """
    通过API获取学业信息（GPA和课程总数），并加入重试机制以应对数据延迟。
    """
    print(f"[{time.strftime('%H:%M:%S')}] 尝试从API {ACADEMIC_INFO_URL} 获取学业信息...")
    for attempt in range(max_retries):
        try:
            response = session_obj.get(ACADEMIC_INFO_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list) and data:
                info = data[0]
                gpa = info.get("gpa")
                course_count = info.get("courseNum_bxqyxd")

                # 只要获取到数据就返回，即使GPA是0，让后端决定如何处理
                if gpa is not None and course_count is not None:
                    result = {"gpa": str(gpa), "course_count": int(course_count)}
                    print(f"[{time.strftime('%H:%M:%S')}] 成功获取学业信息: {result}")
                    return result
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] API返回数据不完整。将在 {delay} 秒后重试...")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] API返回数据格式不正确或为空。将在 {delay} 秒后重试...")

        except (requests.exceptions.RequestException, json.JSONDecodeError, IndexError, KeyError) as e:
            print(f"[{time.strftime('%H:%M:%S')}] 获取或解析学业信息失败: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(delay)
            
    print(f"[{time.strftime('%H:%M:%S')}] 达到最大重试次数，未能获取到有效的学业信息。")
    return {"gpa": "N/A", "course_count": 0} # 所有尝试失败后返回默认值

# --- 获取成绩数据函数 ---
def fetch_grades(session):
    print(f"[{time.strftime('%H:%M:%S')}] 正在访问成绩页面以获取动态API路径...")
    try:
        response_grades_page = session.get(GRADES_INDEX_PAGE_URL, timeout=15)
        response_grades_page.raise_for_status()
        soup = BeautifulSoup(response_grades_page.text, 'html.parser')
        match = re.search(r'scoreQuery/(.*?)/thisTermScores/data', response_grades_page.text)
        if not match:
            print(f"[{time.strftime('%H:%M:%S')}] 未能获取动态API路径段。")
            return None
        dynamic_path_segment = match.group(1)
        dynamic_grades_api_url = f"{BASE_URL}/student/integratedQuery/scoreQuery/{dynamic_path_segment}/thisTermScores/data"
        print(f"[{time.strftime('%H:%M:%S')}] 构建动态成绩API URL: {dynamic_grades_api_url}")
        headers = { "Referer": GRADES_INDEX_PAGE_URL, "X-Requested-With": "XMLHttpRequest" }
        response_grades_data = session.get(dynamic_grades_api_url, headers=headers, timeout=15)
        response_grades_data.raise_for_status()
        grades_data = response_grades_data.json()
        print(f"[{time.strftime('%H:%M:%S')}] 成绩获取成功。")
        return grades_data
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取成绩数据时发生错误: {e}")
        return None
