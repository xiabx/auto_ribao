import sqlite3
import os
import re
from config_loader import config

# 数据库文件位于项目根目录
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config['app'].get('db_file', 'work_plan.db'))

def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建 work_plans 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            todo TEXT NOT NULL,
            progress TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_next_sequence_number(text):
    """
    从文本中分析当前最大的序号，返回下一个序号
    例如文本包含 "1. xxx\n2. yyy"，则返回 3
    如果文本没有序号，则返回 1
    """
    if not text:
        return 1
    
    # 匹配行首的数字序号，如 "1. ", "2. "
    # 增加 \s* 以兼容缩进的情况
    matches = re.findall(r'(?:^|\n)\s*(\d+)\.', text)
    if matches:
        numbers = [int(n) for n in matches]
        return max(numbers) + 1
    else:
        # 如果没有序号，但有内容，假设它是第1条，返回2
        return 2 if text.strip() else 1

def format_todo_item(todo_text, start_seq=1):
    """
    格式化
    """
    lines = todo_text.strip().split('\n')
    formatted_lines = []
    current_seq = start_seq
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 清理已有的序号或列表符，以便重新编号
        # 去除开头的 "1. ", "1、" 等
        line = re.sub(r'^\d+[\.\、]\s*', '', line)
        # 去除开头的 "- ", "* "
        line = re.sub(r'^[-*]\s+', '', line)
        
        formatted_lines.append(f"{current_seq}. {line}")
        current_seq += 1
        
    return "\n".join(formatted_lines)

def add_or_update_plan(date, todo, progress, mode='overwrite'):
    """
    添加或更新计划
    :param mode: 'overwrite' (覆盖/新增) 或 'append' (追加)
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 查询当天是否已有记录
    cursor.execute('SELECT id, todo, progress FROM work_plans WHERE date = ? ORDER BY id ASC LIMIT 1', (date,))
    row = cursor.fetchone()
    
    if row:
        plan_id, old_todo, old_progress = row
        
        if mode == 'overwrite':
            # 覆盖模式：直接更新
            formatted_todo = format_todo_item(todo, 1)
            cursor.execute('''
                UPDATE work_plans 
                SET todo = ?, progress = ?
                WHERE id = ?
            ''', (formatted_todo, progress, plan_id))
            
            # 删除多余记录
            cursor.execute('DELETE FROM work_plans WHERE date = ? AND id != ?', (date, plan_id))
            
        elif mode == 'append':
            # 追加模式
            next_seq = get_next_sequence_number(old_todo)
            
            # 格式化新内容，使其序号接续
            formatted_new_todo = format_todo_item(todo, next_seq)
            
            # 确保换行追加
            new_todo = f"{old_todo}\n{formatted_new_todo}"
            new_progress = f"{old_progress}\n{progress}" if old_progress else progress
            
            cursor.execute('''
                UPDATE work_plans 
                SET todo = ?, progress = ?
                WHERE id = ?
            ''', (new_todo, new_progress, plan_id))
            
    else:
        # 没有记录，直接新增
        formatted_todo = format_todo_item(todo, 1)
        cursor.execute('''
            INSERT INTO work_plans (date, todo, progress)
            VALUES (?, ?, ?)
        ''', (date, formatted_todo, progress))
        
    conn.commit()
    conn.close()

def clear_plans_by_date_range(start_date, end_date):
    """清除指定日期范围内的所有计划"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM work_plans WHERE date >= ? AND date <= ?', (start_date, end_date))
    
    conn.commit()
    conn.close()

def clear_all_plans():
    """清除所有计划"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM work_plans')
    
    conn.commit()
    conn.close()

def get_plans_by_date(date):
    """获取指定日期的所有计划"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM work_plans 
        WHERE date = ? 
        ORDER BY id ASC
    ''', (date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_all_plans():
    """获取所有计划，按日期排序"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM work_plans 
        ORDER BY date ASC, id ASC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def update_plan(plan_id, todo, progress):
    """更新指定 ID 的计划"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE work_plans 
        SET todo = ?, progress = ?
        WHERE id = ?
    ''', (todo, progress, plan_id))
    
    conn.commit()
    conn.close()

def delete_plan(plan_id):
    """删除指定 ID 的计划"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM work_plans WHERE id = ?', (plan_id,))
    
    conn.commit()
    conn.close()

# 初始化数据库
init_db()