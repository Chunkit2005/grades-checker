# app.py (Final Polished Version)
from flask import Flask, request, jsonify, render_template, session
import requests
import os
import time
import re
from score_logic import (
    get_dynamic_token, login, fetch_all_grades, get_user_name,
    fetch_academic_info, save_credentials, load_credentials,
    get_hashed_password_for_storage
)
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=30)

# --- 数据处理辅助函数 ---
def process_single_course_list(raw_course_list):
    processed_list = []
    if not isinstance(raw_course_list, list): return processed_list
    for grade in raw_course_list:
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
                except ValueError: display_score = None
        term_display_name = f"{grade.get('academicYearCode', '')}学年 {grade.get('termName', '')}季学期"
        processed_list.append({
            'courseName': grade.get('courseName', '未知课程'), 'courseScore': display_score,
            'credit': grade.get('credit', 'N/A'), 'gradePoint': grade.get('gradePointScore', 'N/A'),
            'levelName': grade.get('gradeName', 'N/A'), 'examTypeName': grade.get('examTypeCode', 'N/A'),
            'operatetime': grade.get('operatingTime', 'N/A'), 'isValidScore': is_valid_score,
            'termDisplayName': term_display_name
        })
    return processed_list

def process_grades_data(raw_grades_data):
    if not raw_grades_data or not isinstance(raw_grades_data, dict) or 'lnList' not in raw_grades_data: return []
    all_courses = []
    for course_group in raw_grades_data.get('lnList', []):
        all_courses.extend(process_single_course_list(course_group.get('cjList', [])))
    grouped_by_term = {}
    for course in all_courses:
        term_name = course.pop('termDisplayName')
        if term_name not in grouped_by_term: grouped_by_term[term_name] = []
        grouped_by_term[term_name].append(course)
    return [{'termName': name, 'list': courses} for name, courses in grouped_by_term.items()]

def get_sort_key(term_name):
    match = re.search(r'(\d{4})-\d{4}', term_name)
    start_year = int(match.group(1)) if match else 9999
    season_order = 1 if '秋' in term_name else 2 if '春' in term_name else 3
    return (start_year, season_order)

def add_academic_labels(sorted_grades):
    if not sorted_grades: return []
    first_term_name = sorted_grades[0]['termName']
    match = re.search(r'(\d{4})', first_term_name)
    base_year = int(match.group(1)) if match else None
    if base_year is None: return sorted_grades
    year_map = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五'}
    for term_data in sorted_grades:
        term_name = term_data['termName']
        term_match = re.search(r'(\d{4})', term_name)
        term_year = int(term_match.group(1)) if term_match else base_year
        academic_year_num = term_year - base_year + 1
        year_char = year_map.get(academic_year_num, str(academic_year_num))
        season_char = '上' if '秋' in term_name else '下' if '春' in term_name else ''
        if season_char: term_data['termLabel'] = f"大{year_char}{season_char}"
    return sorted_grades

# [MODIFIED] 状态计算函数，现在接收 academic_info
def calculate_current_term_stats(current_term_grades, academic_info):
    stats = {"passed": 0, "announced": 0, "total": 0}
    if academic_info:
        stats["total"] = academic_info.get("course_count", 0)

    if not current_term_grades or not current_term_grades[0]['list']:
        return stats
    
    current_courses = current_term_grades[0]['list']
    passed_count = 0
    announced_count = 0
    for course in current_courses:
        if course['isValidScore']:
            announced_count += 1
            if float(course['courseScore']) >= 60:
                passed_count += 1
    stats["passed"] = passed_count
    stats["announced"] = announced_count
    # 如果 academic_info 中没有课程总数，则使用当前学期已公布的课程数作为总数
    if stats["total"] == 0:
        stats["total"] = len(current_courses)
    return stats

# --- 路由 ---
@app.route('/')
def index():
    return render_template('index.html')

def get_full_data(s):
    user_name = get_user_name(s)
    academic_info = fetch_academic_info(s) # 获取学业信息
    raw_all_grades = fetch_all_grades(s)
    all_grades_by_term = process_grades_data(raw_all_grades)
    
    if not all_grades_by_term: return {"success": False}

    all_grades_by_term.sort(key=lambda x: get_sort_key(x['termName']))
    labeled_grades = add_academic_labels(all_grades_by_term)
    labeled_grades.reverse() # 最新的在前
    
    if labeled_grades:
        labeled_grades[0]['isCurrent'] = True # [NEW] 为当前学期添加标志

    current_term_grades = [labeled_grades[0]] if labeled_grades else []
    current_term_stats = calculate_current_term_stats(current_term_grades, academic_info)

    return {
        "success": True, "all_grades": labeled_grades, "user_name": user_name,
        "overall_gpa": academic_info.get("gpa", "N/A"), "current_stats": current_term_stats,
    }

# ... (文件余下部分，所有路由函数，都保持原样，无需修改) ...
@app.route('/api/auto_login_and_grades', methods=['POST'])
def api_auto_login_and_grades():
    s = requests.Session()
    username_saved, _ = load_credentials()
    if 'cookies' in session: s.cookies.update(session['cookies'])
    user_name_check = get_user_name(s)
    if user_name_check != "同学":
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
    if not all([username, password_raw]): return jsonify({"success": False, "message": "缺少学号或密码。"}), 400
    s = requests.Session()
    dynamic_token = get_dynamic_token(s)
    if not dynamic_token: return jsonify({"success": False, "message": "获取Token失败，请重试。"}), 401
    if login(s, username, password_raw, dynamic_token):
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
        else: return jsonify({"success": False, "message": "登录成功，但获取成绩失败。"}), 401
    else: return jsonify({"success": False, "message": "登录失败，请检查学号、密码或验证码。"}), 401

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
