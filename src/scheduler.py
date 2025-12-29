import time
import schedule
import threading
from datetime import datetime
from config_loader import config
from handler import run as run_handler
from workday_utils import get_holiday_info
from logger import logger

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

def start_scheduler():
    time_str = config.get('scheduler', {}).get('time', '18:00')
    
    try:
        # 验证时间格式是否正确
        datetime.strptime(time_str, "%H:%M")
        
        logger.info(f"设置定时任务: 每天 {time_str} 执行 (仅工作日)")
        schedule.every().day.at(time_str).do(job)
            
    except ValueError:
        logger.error(f"时间格式错误: {time_str}，请使用 HH:MM 格式。默认每天 18:00 执行")
        schedule.every().day.at("18:00").do(job)
    except Exception as e:
        logger.error(f"设置定时任务失败: {e}")
        return

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    logger.info("启动定时任务调度器...")
    start_scheduler()