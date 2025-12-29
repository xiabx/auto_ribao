import time
import schedule
import threading
from datetime import datetime
from config_loader import config
from handler import run as run_handler
from workday_utils import get_holiday_info
from logger import logger

# --- 全局变量与锁 ---
# 用于线程安全地修改 schedule
schedule_lock = threading.Lock()
# 用于线程安全地读写当前任务时间，避免Web服务和调度线程的竞争
_current_schedule_time_lock = threading.Lock()
# 存储当前任务时间的全局变量
_current_schedule_time = None

def job():
    # 检查今天是否为工作日
    today_str = datetime.now().strftime("%Y-%m-%d")
    holiday_info = get_holiday_info(today_str)
    
    if holiday_info:
        logger.info(f"今天是 {holiday_info}，跳过定时任务。")
        return

    logger.info("开始执行定时任务...")
    try:
        run_handler()
    except Exception as e:
        logger.error(f"定时任务执行失败: {e}", exc_info=True)

def get_current_schedule_time():
    """获取当前定时任务的执行时间"""
    with _current_schedule_time_lock:
        return _current_schedule_time

def update_schedule_time(new_time_str):
    """
    更新定时任务的执行时间
    :param new_time_str: "HH:MM" 格式的时间字符串
    """
    global _current_schedule_time
    with schedule_lock:
        try:
            # 验证时间格式
            datetime.strptime(new_time_str, "%H:%M")
            
            # 清除所有旧任务
            schedule.clear()
            
            # 添加新任务
            schedule.every().day.at(new_time_str).do(job)
            
            # 更新全局时间变量
            with _current_schedule_time_lock:
                _current_schedule_time = new_time_str
                
            logger.info(f"定时任务时间已更新为: 每天 {new_time_str}")
            return True, f"更新成功，新任务时间为 {new_time_str}"
        except ValueError:
            logger.error(f"更新失败: 无效的时间格式 {new_time_str}")
            return False, f"无效的时间格式: {new_time_str}"

def start_scheduler():
    global _current_schedule_time
    time_str = config.get('scheduler', {}).get('time', '18:00')
    
    try:
        # 验证时间格式是否正确
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        logger.error(f"配置文件中的时间格式错误: {time_str}，请使用 HH:MM 格式。将使用默认时间 18:00")
        time_str = "18:00"
    
    # 初始化定时任务
    with schedule_lock:
        schedule.every().day.at(time_str).do(job)
    
    # 初始化全局时间变量
    with _current_schedule_time_lock:
        _current_schedule_time = time_str
        
    logger.info(f"定时任务已设置: 每天 {_current_schedule_time} 执行 (仅工作日)")

    while True:
        with schedule_lock:
            schedule.run_pending()
        # 降低休眠时间以提高响应性，同时避免CPU空转
        time.sleep(1)

if __name__ == "__main__":
    logger.info("启动定时任务调度器...")
    start_scheduler()