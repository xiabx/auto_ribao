import datetime
from datetime import timedelta

# 尝试导入 chinese_calendar 库用于判断法定节假日
# 如果没有安装，请运行: pip install chinesecalendar
try:
    import chinese_calendar
    HAS_CHINESE_CALENDAR = True
except ImportError:
    HAS_CHINESE_CALENDAR = False

# 简单的节假日英文到中文映射
HOLIDAY_MAP = {
    "New Year's Day": "元旦",
    "Spring Festival": "春节",
    "Tomb-sweeping Day": "清明节",
    "Labour Day": "劳动节",
    "Dragon Boat Festival": "端午节",
    "Mid-autumn Festival": "中秋节",
    "National Day": "国庆节",
    "Anti-Fascist 70th Day": "抗战胜利70周年",
    "Lantern Festival": "元宵节",
    "Laba Festival": "腊八节",
}

def get_workdays(start_date_str, end_date_str):
    """
    获取指定日期范围内的所有工作日（排除周末和法定节假日，包含调休的工作日）
    :param start_date_str: 开始日期，格式 'YYYY-MM-DD'
    :param end_date_str: 结束日期，格式 'YYYY-MM-DD'
    :return: 工作日日期字符串列表
    """
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        print("日期格式错误，请使用 YYYY-MM-DD 格式")
        return []
    
    workdays = []
    current_date = start_date
    
    while current_date <= end_date:
        is_workday = False
        
        if HAS_CHINESE_CALENDAR:
            if chinese_calendar.is_workday(current_date):
                is_workday = True
        else:
            if current_date.weekday() < 5:
                is_workday = True
                
        if is_workday:
            workdays.append(current_date.strftime("%Y-%m-%d"))
            
        current_date += timedelta(days=1)
        
    return workdays

def get_holiday_info(date_str):
    """
    获取指定日期的节假日信息
    :param date_str: 日期字符串 'YYYY-MM-DD'
    :return: 节假日名称或原因 (例如 '周末', '元旦', '春节')，如果是工作日返回 None
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    if HAS_CHINESE_CALENDAR:
        # 如果是工作日（包含调休上班），直接返回 None
        if chinese_calendar.is_workday(date_obj):
            return None
        
        # 获取节假日名称
        on_holiday, holiday_name = chinese_calendar.get_holiday_detail(date_obj)
        if on_holiday:
            if holiday_name:
                # 尝试映射中文名称
                name_str = str(holiday_name)
                return HOLIDAY_MAP.get(name_str, name_str)
            else:
                return "周末"
    else:
        # 降级方案
        if date_obj.weekday() >= 5:
            return "周末"
            
    return None

def get_holidays_in_range(start_date_str, end_date_str):
    """
    批量获取指定日期范围内的所有非工作日信息
    :param start_date_str: 开始日期 'YYYY-MM-DD'
    :param end_date_str: 结束日期 'YYYY-MM-DD'
    :return: 字典 { 'YYYY-MM-DD': '节假日名称' }
    """
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        return {}

    holidays = {}
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        if HAS_CHINESE_CALENDAR:
            if not chinese_calendar.is_workday(current_date):
                on_holiday, holiday_name = chinese_calendar.get_holiday_detail(current_date)
                if holiday_name:
                    name_str = str(holiday_name)
                    holidays[date_str] = HOLIDAY_MAP.get(name_str, name_str)
                else:
                    holidays[date_str] = "周末"
        else:
            if current_date.weekday() >= 5:
                holidays[date_str] = "周末"
                
        current_date += timedelta(days=1)
        
    return holidays

if __name__ == "__main__":
    # 测试代码
    s = "2024-04-28"
    e = "2024-05-12"
    
    print(f"计算 {s} 到 {e} 的节假日:")
    holidays = get_holidays_in_range(s, e)
    for d, name in holidays.items():
        print(f"{d}: {name}")