from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Blueprint
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import threading
from datetime import datetime, timedelta
from ai_planner import generate_plan
from config_loader import config
from functools import wraps
from workday_utils import get_holiday_info, get_holidays_in_range
from db_manager import get_all_plans, update_plan, delete_plan, get_plans_by_date, add_or_update_plan, clear_plans_by_date_range, clear_all_plans
from scheduler import start_scheduler, get_current_schedule_time, update_schedule_time
from logger import logger
from handler import run as run_handler

# 获取当前文件所在目录 (src)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 模板目录在上一级 (项目根目录) 的 templates 文件夹
TEMPLATE_DIR = os.path.join(os.path.dirname(BASE_DIR), 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# === 安全配置 ===
# 设置 secret_key 用于 session 加密
app.secret_key = os.urandom(24)
# 设置 session 有效期为 30 分钟
app.permanent_session_lifetime = timedelta(minutes=30)

# 用户配置 (从 config.yaml 加载)
users = {
    config['security']['admin_user']: generate_password_hash(config['security']['admin_password'])
}

# 创建 Blueprint，设置 URL 前缀
bp = Blueprint('auto_ribao', __name__, url_prefix='/auto_ribao')

# === 登录验证装饰器 ===
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # 如果是 API 请求，返回 401 状态码
            if request.path.startswith('/auto_ribao/api/') or request.path.startswith('/api/'):
                return jsonify({"error": "未登录"}), 401
            return redirect(url_for('auto_ribao.login'))
        return f(*args, **kwargs)
    return decorated_function

# === 路由 (全部挂载到 Blueprint) ===

@bp.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('auto_ribao.index'))
    return render_template('login.html')

@bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username in users and check_password_hash(users.get(username), password):
        session.permanent = True
        session['user'] = username
        logger.info(f"用户 {username} 登录成功")
        return jsonify({"message": "登录成功"})
    
    logger.warning(f"用户 {username} 登录失败: 密码错误或用户不存在")
    return jsonify({"error": "用户名或密码错误"}), 401

@bp.route('/logout')
def logout():
    username = session.get('user')
    session.pop('user', None)
    logger.info(f"用户 {username} 退出登录")
    return redirect(url_for('auto_ribao.login'))

@bp.route('/')
@login_required
def index():
    return render_template('index.html')

@bp.route('/api/generate_plan', methods=['POST'])
@login_required
def api_generate_plan():
    data = request.json
    requirement = data.get('requirement')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    mode = data.get('mode', 'overwrite') # 获取生成模式
    
    user = session.get('user')
    logger.info(f"用户 {user} 请求生成计划预览: {start_date} 至 {end_date}, 模式: {mode}")
    
    if not requirement or not start_date or not end_date:
        logger.warning("生成计划失败: 缺少必要参数")
        return jsonify({"error": "缺少必要参数"}), 400
        
    if len(requirement) > 2000:
        logger.warning("生成计划失败: 需求描述过长")
        return jsonify({"error": "需求描述过长"}), 400

    try:
        # save_db=False 表示只生成不保存
        plan, days_count = generate_plan(requirement, start_date, end_date, mode, save_db=False)
        if plan:
            logger.info(f"计划预览生成成功，共 {days_count} 天")
            return jsonify({
                "message": "计划生成成功", 
                "plan": plan,
                "days_count": days_count
            })
        else:
            logger.error("计划生成失败: AI 返回空结果")
            return jsonify({"error": "计划生成失败: AI 返回空结果"}), 500
    except Exception as e:
        logger.error(f"生成计划时发生异常: {e}", exc_info=True)
        return jsonify({"error": f"系统错误: {str(e)}"}), 500

@bp.route('/api/save_generated_plans', methods=['POST'])
@login_required
def api_save_generated_plans():
    data = request.json
    plans = data.get('plans')
    mode = data.get('mode', 'overwrite')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    user = session.get('user')
    logger.info(f"用户 {user} 确认保存计划: {len(plans) if plans else 0} 条, 模式: {mode}")

    if not plans:
        return jsonify({"error": "没有计划数据"}), 400
        
    try:
        # 如果是覆盖模式，且提供了日期范围，先清除旧数据
        if mode == 'overwrite' and start_date and end_date:
            clear_plans_by_date_range(start_date, end_date)
            logger.info(f"已清除旧计划: {start_date} - {end_date}")
            
        for item in plans:
            add_or_update_plan(item['date'], item['todo'], item['progress'], mode)
            
        logger.info("计划保存完成")
        return jsonify({"message": "计划保存成功"})
    except Exception as e:
        logger.error(f"保存计划失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/api/get_plan', methods=['GET'])
@login_required
def api_get_plan():
    try:
        plans = get_all_plans()
        return jsonify(plans)
    except Exception as e:
        logger.error(f"获取计划列表失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/api/update_day', methods=['POST'])
@login_required
def api_update_day():
    data = request.json
    plan_id = data.get('id')
    todo = data.get('todo')
    progress = data.get('progress')
    user = session.get('user')
    
    if not plan_id:
        return jsonify({"error": "缺少计划ID"}), 400
        
    try:
        update_plan(plan_id, todo, progress)
        logger.info(f"用户 {user} 更新了计划 ID {plan_id}")
        return jsonify({"message": "更新成功"})
    except Exception as e:
        logger.error(f"更新计划失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/api/delete_plan', methods=['POST'])
@login_required
def api_delete_plan():
    data = request.json
    plan_id = data.get('id')
    user = session.get('user')
    
    if not plan_id:
        return jsonify({"error": "缺少计划ID"}), 400
        
    try:
        delete_plan(plan_id)
        logger.info(f"用户 {user} 删除了计划 ID {plan_id}")
        return jsonify({"message": "删除成功"})
    except Exception as e:
        logger.error(f"删除计划失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/api/clear_plans', methods=['POST'])
@login_required
def api_clear_plans():
    data = request.json
    clear_type = data.get('type') # 'all' or 'range'
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    user = session.get('user')
    
    try:
        if clear_type == 'all':
            clear_all_plans()
            logger.info(f"用户 {user} 清除了所有计划")
            return jsonify({"message": "所有计划已清除"})
        elif clear_type == 'range':
            if not start_date or not end_date:
                return jsonify({"error": "缺少日期范围参数"}), 400
            clear_plans_by_date_range(start_date, end_date)
            logger.info(f"用户 {user} 清除了 {start_date} 至 {end_date} 的计划")
            return jsonify({"message": "指定范围内的计划已清除"})
        else:
            return jsonify({"error": "无效的清除类型"}), 400
    except Exception as e:
        logger.error(f"清除计划失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/api/check_holiday', methods=['GET'])
@login_required
def api_check_holiday():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "缺少日期参数"}), 400
    
    holiday_info = get_holiday_info(date_str)
    return jsonify({"holiday": holiday_info})

@bp.route('/api/get_holidays_batch', methods=['GET'])
@login_required
def api_get_holidays_batch():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({"error": "缺少日期范围参数"}), 400
        
    holidays = get_holidays_in_range(start_date, end_date)
    return jsonify(holidays)

@bp.route('/api/get_schedule_time', methods=['GET'])
@login_required
def api_get_schedule_time():
    time_str = get_current_schedule_time()
    
    # 如果调度器还没准备好，直接从配置读取默认值
    if not time_str:
        time_str = config.get('scheduler', {}).get('time', '18:00')
        
    return jsonify({"time": time_str})

@bp.route('/api/update_schedule_time', methods=['POST'])
@login_required
def api_update_schedule_time():
    data = request.json
    new_time = data.get('time')
    
    if not new_time:
        return jsonify({"error": "缺少时间参数"}), 400
        
    success, message = update_schedule_time(new_time)
    
    if success:
        return jsonify({"message": message})
    else:
        return jsonify({"error": message}), 400

@bp.route('/api/trigger_fill', methods=['POST'])
@login_required
def api_trigger_fill():
    user = session.get('user')
    logger.info(f"用户 {user} 手动触发日报填写任务")
    
    try:
        result = run_handler(is_api_call=True)
        if result and result.get('success'):
            return jsonify({"message": result.get('message', '执行成功')})
        else:
            return jsonify({"error": result.get('message', '执行失败') if result else '执行失败'}), 500
    except Exception as e:
        logger.error(f"手动触发任务失败: {e}", exc_info=True)
        return jsonify({"error": f"系统错误: {str(e)}"}), 500

# 注册 Blueprint
app.register_blueprint(bp)

# 添加根路由重定向 (可选，方便访问)
@app.route('/')
def root():
    return redirect(url_for('auto_ribao.index'))


# src/app.py 文件末尾

if __name__ == '__main__':
    # 1. 启动定时任务
    logger.info("正在启动 Web 服务...")

    # 启动定时任务线程
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("定时任务调度器已启动")

    # 2. 获取配置端口
    port = config['app'].get('port', 5001)  # 增加默认值防止报错

    # 3. 打印本地开发访问地址提示 (关键步骤)
    print("\n" + "=" * 50)
    print(f" 服务已启动！请通过以下地址访问:")
    print(f" 首页: http://127.0.0.1:{port}/auto_ribao/")
    print(f" 登录: http://127.0.0.1:{port}/auto_ribao/login")
    print("=" * 50 + "\n")

    logger.info(f"Web 服务监听端口: {port}")
    print("当前 SERVER_NAME 配置:", app.config.get('SERVER_NAME'))
    print("=" * 20 + " 路由表 " + "=" * 20)
    print(app.url_map)
    print("=" * 50)
    # 4. 启动 Flask
    # host='0.0.0.0' 允许局域网访问，也适配 Docker/服务器环境
    app.run(debug=False, host='0.0.0.0', port=port)