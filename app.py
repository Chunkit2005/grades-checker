# app.py (Complete Updated Version)
from flask import Flask, request, jsonify, render_template, session
import requests
import os
import time
from score_logic import (
    get_dynamic_token, login, fetch_grades, get_user_name,
    fetch_academic_info, save_credentials, load_credentials,
    get_hashed_password_for_storage, BASE_URL
)
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=30)

# --- 辅助函数：处理原始成绩数据 ---
def process_grade_data(raw_grade_list):
    processed_list = []
    if not raw_grade_list: return processed_list
    for grade in raw_grade_list:
        course_score_raw = grade.get('courseScore')
        is_valid_score = False
        display_score = None
        if course_score_raw is not None:
            cleaned_score = str(course_score_raw).strip()
            if cleaned_score:
                try:
                    float(cleaned_score)
                    display_score = cleaned_score
                    is_valid_score = True
                except ValueError:
                    display_score = None
        processed_list.append({
            'courseName': grade.get('courseName', '未知课程'), 'courseScore': display_score,
            'credit': grade.get('credit', 'N/A'), 'gradePoint': grade.get('gradePoint', 'N/A'),
            'levelName': grade.get('levelName', 'N/A'), 'examTypeName': grade.get('examTypeName', 'N/A'),
            'operatetime': grade.get('operatetime', 'N/A'), 'isValidScore': is_valid_score
        })
    return processed_list

def process_all_terms_grades(raw_grades_data):
    if not raw_grades_data: return []
    processed_grades = []
    for term_data in raw_grades_data:
        # --- 修改：将“未知学期”替换为“当前学期” ---
        term_name = term_data.get('termName', '当前学期')
        if term_name == '未知学期':
            term_name = '当前学期'
            
        processed_grades.append({
            'termName': term_name,
            'list': process_grade_data(term_data.get('list', []))
        })
    return processed_grades

# --- 路由 ---
@app.route('/')
def index():
    return render_template('index.html')

def get_full_data(s):
    """辅助函数，用于获取所有数据（姓名，成绩，学业信息）"""
    user_name = get_user_name(s)
    raw_grades = fetch_grades(s)
    academic_info = fetch_academic_info(s) # 调用新函数
    
    if raw_grades:
        processed_grades = process_all_terms_grades(raw_grades)
        return {
            "success": True,
            "grades": processed_grades,
            "user_name": user_name,
            "overall_gpa": academic_info.get("gpa", "N/A"),
            "course_count": academic_info.get("course_count", 0)
        }
    return {"success": False}

@app.route('/api/auto_login_and_grades', methods=['POST'])
def api_auto_login_and_grades():
    s = requests.Session()
    username_saved, _ = load_credentials()

    if 'cookies' in session:
        s.cookies.update(session['cookies'])

    user_name_check = get_user_name(s)
    if user_name_check != "同学":
        print(f"[{time.strftime('%H:%M:%S')}] 现有会话有效，用户: {user_name_check}。")
        full_data = get_full_data(s)
        if full_data["success"]:
            full_data["username"] = username_saved
            return jsonify(full_data), 200

    message = "会话已过期，请手动登录。" if username_saved else "请登录。"
    return jsonify({"success": False, "message": message, "username_saved": username_saved}), 401

@app.route('/api/manual_login_and_get_grades', methods=['POST'])
def api_manual_login_and_get_grades():
    data = request.get_json()
    username, password_raw = data.get('username'), data.get('password')
    if not all([username, password_raw]):
        return jsonify({"success": False, "message": "缺少学号或密码。"}), 400

    s = requests.Session()
    print(f"[{time.strftime('%H:%M:%S')}] 尝试手动登录账号: {username}...")
    dynamic_token = get_dynamic_token(s)
    if not dynamic_token:
        return jsonify({"success": False, "message": "获取Token失败，请重试。"}), 401

    if login(s, username, password_raw, dynamic_token):
        print(f"[{time.strftime('%H:%M:%S')}] 手动登录成功！获取数据...")
        full_data = get_full_data(s)
        if full_data["success"]:
            session['cookies'] = s.cookies.get_dict()
            session.permanent = True
            if data.get('save_info', False):
                save_credentials(username, get_hashed_password_for_storage(password_raw))
            else:
                credentials_file_path = os.path.join(os.path.dirname(__file__), "user_credentials.json")
                if os.path.exists(credentials_file_path): os.remove(credentials_file_path)
            
            full_data["username"] = username
            return jsonify(full_data), 200
        else:
            return jsonify({"success": False, "message": "登录成功，但获取成绩失败。"}), 401
    else:
        return jsonify({"success": False, "message": "登录失败，请检查学号、密码或验证码。"}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    credentials_file_path = os.path.join(os.path.dirname(__file__), "user_credentials.json")
    if os.path.exists(credentials_file_path):
        try: os.remove(credentials_file_path)
        except Exception as e: print(f"清除凭证失败: {e}")
    return jsonify({"success": True, "message": "已成功退出登录。"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
