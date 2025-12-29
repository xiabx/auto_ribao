import json
from openai import OpenAI
from workday_utils import get_workdays  # 导入更强大的工作日计算工具
from config_loader import config
from db_manager import add_or_update_plan, clear_plans_by_date_range  # 导入数据库操作
from logger import logger

# === 配置 AI (从 config.yaml 加载) ===
AI_API_KEY = config['ai']['api_key']
AI_BASE_URL = config['ai']['base_url']
AI_MODEL = config['ai']['model']
SYSTEM_PROMPT = config['ai'].get('system_prompt', "你是一个资深技术经理，擅长拆解开发任务并编写日报。只返回 JSON 数据。")
USER_PROMPT_TEMPLATE = config['ai'].get('user_prompt_template', "")

def generate_plan(requirement, start_date, end_date, mode='overwrite', save_db=True):
    """
    调用 AI 生成每日计划
    :param mode: 'overwrite' (覆盖) 或 'append' (追加)
    :param save_db: 是否保存到数据库，默认为 True。如果为 False，则只返回生成的数据。
    """
    client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)

    # 使用 workday_utils 中的 get_workdays，支持节假日判断
    workdays = get_workdays(start_date, end_date)

    if not workdays:
        logger.warning(f"时间范围内没有工作日: {start_date} - {end_date}")
        return None, 0

    days_count = len(workdays)
    workdays_json = json.dumps(workdays)

    # 如果配置文件中没有模板，使用默认模板
    if not USER_PROMPT_TEMPLATE:
        prompt = f"""
        我是一个程序员。
        总需求：{requirement}
        时间范围：{start_date} 到 {end_date}
        工作日列表：{workdays_json} (共 {days_count} 天)

        请根据总需求，合理拆解为每天的工作内容。

        要求：
        1. 前期注重“调研、设计、搭建环境”，中期“核心开发、接口联调”，后期“测试、修复Bug、部署”。
        2. 输出必须是严格的 JSON 格式列表，不要包含 Markdown 代码块标记。
        3. 列表每一项包含三个字段：
           - "date": 日期（必须从上面的工作日列表中一一对应）
           - "todo": 今日工作内容（简练，适合日报，如果是多条内容请用换行分隔或直接返回字符串）
           - "progress": 迭代事项及进度（例如：完成用户模块开发 30%）
        """
    else:
        # 使用配置文件中的模板
        prompt = USER_PROMPT_TEMPLATE.format(
            requirement=requirement,
            start_date=start_date,
            end_date=end_date,
            workdays_json=workdays_json,
            days_count=days_count
        )

    logger.info(f"正在请求 AI 拆解任务 ({days_count} 天)...")

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        content = response.choices[0].message.content
        logger.info(f"AI 原始返回内容: {content}")

        # 清理可能存在的 markdown 标记
        content = content.replace("```json", "").replace("```", "").strip()

        plan_data = json.loads(content)

        # 预处理数据（统一格式）
        for item in plan_data:
            todo_content = item.get('todo', '')
            if isinstance(todo_content, list):
                item['todo'] = "\n".join(str(t) for t in todo_content)
            
            # 处理 progress 字段，如果是列表则转换为字符串
            progress_content = item.get('progress', '')
            if isinstance(progress_content, list):
                item['progress'] = "\n".join(str(p) for p in progress_content)

        if save_db:
            # 根据模式处理数据库
            if mode == 'overwrite':
                # 覆盖模式：先清除范围内的旧计划
                clear_plans_by_date_range(start_date, end_date)
                logger.info(f"已清除旧计划: {start_date} - {end_date}")
                
            # 统一使用 add_or_update_plan 处理
            for item in plan_data:
                add_or_update_plan(item['date'], item['todo'], item['progress'], mode)

            logger.info(f"计划已生成并保存至数据库 (模式: {mode})")
        else:
            logger.info("计划已生成 (预览模式，未入库)")

        return plan_data, days_count

    except Exception as e:
        logger.error(f"AI 生成失败: {e}", exc_info=True)
        # 抛出异常以便上层捕获并返回给前端
        raise e

# 单独运行此文件可以生成计划
if __name__ == "__main__":
    # 示例：你可以手动修改这里的需求和时间，生成一次计划并存入数据库
    req = "开发一个新的企业级CRM客户管理系统，包含前后端，使用Vue3和SpringBoot"
    s_date = "2024-05-20"
    e_date = "2024-05-31"
    generate_plan(req, s_date, e_date)