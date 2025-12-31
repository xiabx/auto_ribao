import re
import time
import json
import urllib.request
import os
import sys
import ssl
import socket
import getpass
import platform
from datetime import datetime
from playwright.sync_api import sync_playwright
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from config_loader import config
from db_manager import get_plans_by_date
from logger import logger

# --- 配置区域 (从 config.yaml 加载) ---

# 1. 钉钉机器人 Webhook
DINGTALK_WEBHOOK = config['dingtalk']['webhook']

# 2. 腾讯云 COS 配置
COS_SECRET_ID = config['cos']['secret_id']
COS_SECRET_KEY = config['cos']['secret_key']
COS_REGION = config['cos']['region']
COS_BUCKET = config['cos']['bucket']

# 3. 其他配置
TARGET_URL = config['app']['target_url']

# BASE_DIR 设置为项目根目录 (src 的上一级)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IMG_LOG_DIR = os.path.join(BASE_DIR, config['app']['img_log_dir'])
COOKIE_FILE = os.path.join(BASE_DIR, 'cookie.json')

# --- 配置结束 ---

def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_host_ip():
    """获取本机IP"""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        if s:
            s.close()
    return ip


def upload_to_cos_and_get_url(local_file_path):
    """
    上传图片到腾讯云COS并获取带签名的临时URL
    """
    try:
        # 1. 初始化 COS 客户端
        cos_config = CosConfig(Region=COS_REGION, SecretId=COS_SECRET_ID, SecretKey=COS_SECRET_KEY)
        client = CosS3Client(cos_config)

        # 2. 生成云端文件名 (使用日期分类)
        file_name = os.path.basename(local_file_path)
        date_folder = datetime.now().strftime("%Y%m%d")
        object_key = f"daily_reports/{date_folder}/{file_name}"

        logger.info(f"正在上传截图至腾讯云 COS: {object_key}...")

        # 3. 上传文件
        client.upload_file(
            Bucket=COS_BUCKET,
            LocalFilePath=local_file_path,
            Key=object_key
        )

        # 4. 生成预签名 URL (有效期 3600 秒)
        presigned_url = client.get_presigned_url(
            Method='GET',
            Bucket=COS_BUCKET,
            Key=object_key,
            Expired=3600
        )

        logger.info("云端签名链接生成成功")
        return presigned_url

    except Exception as e:
        logger.error(f"COS 上传失败: {e}", exc_info=True)
        return None


def send_dingtalk_notification(title, content, image_url=None):
    """
    发送钉钉Markdown通知，支持图片
    """
    if not DINGTALK_WEBHOOK:
        logger.warning("未配置钉钉Webhook")
        return

    # 如果有图片链接，添加到 Markdown 内容中
    final_text = content
    if image_url:
        final_text += f"\n\n![截图]({image_url})\n> 截图链接有效期1小时"

    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": final_text
        }
    }

    try:
        headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(
            url=DINGTALK_WEBHOOK,
            data=json.dumps(data).encode("utf-8"),
            headers=headers
        )
        
        # 创建一个不验证 SSL 证书的上下文
        context = ssl._create_unverified_context()
        
        with urllib.request.urlopen(req, context=context) as resp:
            result = resp.read().decode('utf-8')
            logger.info(f"钉钉通知发送结果: {result}")
    except Exception as e:
        logger.error(f"发送钉钉通知失败: {e}", exc_info=True)


def run(is_api_call=False):
    """
    执行日报填写任务
    :param is_api_call: 是否为 API 调用，如果是，则返回执行结果字典
    :return: 如果 is_api_call 为 True，返回 {"success": bool, "message": str}
    """
    # --- 调试信息：记录执行环境 ---
    try:
        logger.info("=" * 40)
        logger.info("🚀 任务开始执行 (Environment Debug)")
        logger.info(f"📅 当前系统时间: {datetime.now()}")
        logger.info(f"🆔 进程 PID: {os.getpid()}")
        logger.info(f"👤 运行用户: {getpass.getuser()}")
        logger.info(f"📂 工作目录: {os.getcwd()}")
        logger.info(f"📜 启动脚本: {sys.argv[0]}")
        logger.info("=" * 40)
    except Exception as e:
        logger.error(f"记录调试信息失败: {e}")
    # ---------------------------

    # 1. 检查今天是否有日报计划
    today_str = datetime.now().strftime("%Y-%m-%d")
    plans = get_plans_by_date(today_str)
    
    if not plans:
        msg = f"今天 ({today_str}) 没有找到日报计划，发送提醒..."
        logger.warning(msg)
        
        # 获取调试信息用于通知
        server_ip = get_host_ip()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        os_info = f"{platform.system()} {platform.release()}"
        
        send_dingtalk_notification(
            "⚠️ 日报未填写提醒",
            f"## ⚠️ 今日 ({today_str}) 尚未生成日报计划\n\n"
            f"请尽快登录系统生成今日日报，以便自动填写。\n\n"
            f"--- \n"
            f"**调试信息**:\n"
            f"- IP: {server_ip}\n"
            f"- OS: {os_info}\n"
            f"- Time: {current_time}\n"
            f"- Script: {os.path.basename(sys.argv[0])}"
        )
        if is_api_call:
            return {"success": False, "message": msg}
        return

    # 2. 检查 Cookie 文件是否存在
    if not os.path.exists(COOKIE_FILE):
        msg = f"认证失败: 未找到 Cookie 文件 ({COOKIE_FILE})"
        logger.error(msg)
        send_dingtalk_notification(
            "❌ 日报填写失败",
            f"## ❌ 认证失败\n\n**原因**: 未在项目根目录找到 `cookie.json` 文件。\n\n**解决方法**: 请在本地运行 `python script/get_cookie.py` 脚本生成该文件，并上传到服务器。"
        )
        if is_api_call:
            return {"success": False, "message": msg}
        return

    # 获取第一条计划（假设每天合并为一条）
    today_plan = plans[0]
    todo_content = today_plan['todo']
    progress_content = today_plan['progress'] or "正常推进中"

    # 确保图片日志目录存在
    if not os.path.exists(IMG_LOG_DIR):
        os.makedirs(IMG_LOG_DIR)

    # 强制移除 DISPLAY 环境变量，防止 Xshell 触发 Xmanager 弹窗
    if 'DISPLAY' in os.environ:
        logger.info("检测到 DISPLAY 环境变量，正在移除以避免 X11 转发干扰...")
        del os.environ['DISPLAY']

    # 使用 sync_playwright 上下文管理器
    with sync_playwright() as p:
        browser = None
        try:
            logger.info("启动浏览器...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--start-maximized", 
                    "--disable-gpu",
                    "--lang=zh-CN" # 强制设置浏览器语言为中文
                ]
            )
            
            # 创建上下文并注入 Cookie
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN', # 设置上下文语言环境
                timezone_id='Asia/Shanghai' # 设置时区
            )
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                context.add_cookies(cookies)
            logger.info("Cookie 注入成功")

            page = context.new_page()
            screenshot_path = ""

            logger.info(f"正在打开页面: {TARGET_URL}")
            # 增加超时时间到 60秒
            page.goto(TARGET_URL, timeout=60000)
            page.wait_for_load_state("domcontentloaded")

            # 等待1秒，确保页面完全加载
            time.sleep(1)

            # 1. 点击“添加记录”按钮
            logger.info("点击“添加记录”按钮")
            iframe = page.frame_locator("#wiki-notable-iframe")
            iframe.get_by_role("button", name="添加记录").click()
            time.sleep(1)

            logger.info("选择“需支持”")
            iframe.locator("div").filter(has_text=re.compile(r"^需支持$")).click()

            # 按20下backspace
            logger.info("清除旧内容")
            for _ in range(15):
                iframe.get_by_role("textbox").nth(4).press("Backspace")
                time.sleep(0.1)
            time.sleep(1)

            logger.info(f"填写今日内容: {todo_content[:20]}...")
            iframe.get_by_role("textbox").nth(4).fill(todo_content)
            time.sleep(1)

            logger.info("点击下一个输入框")
            iframe.locator(
                "div:nth-child(3) > .field > .sc-dx7zg8-0 > .sc-dx7zg8-3 > .sc-ryhpjr-0 > .sc-elxj4z-0 > .sc-elxj4z-1 > .content > div > .sc-dABzDS").click()
            time.sleep(1)

            logger.info(f"填写迭代事项: {progress_content[:20]}...")
            iframe.get_by_role("textbox").nth(5).fill(progress_content)
            time.sleep(1)

            logger.info("提交记录")
            iframe.locator(".sc-1gu97lr-4 > button:nth-child(6)").click()
            time.sleep(1)

            logger.info("✅ 日报自动填写成功！")
            screenshot_name = f"daily_report_success_{get_timestamp()}.png"
            screenshot_path = os.path.join(IMG_LOG_DIR, screenshot_name)
            page.screenshot(path=screenshot_path)
            logger.info(f"截图已保存: {screenshot_path}")

            # # --- 保存最新的 Cookie ---
            # try:
            #     updated_cookies = context.cookies()
            #     with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            #         json.dump(updated_cookies, f, ensure_ascii=False, indent=4)
            #     logger.info(f"Cookies 已更新并保存至 {COOKIE_FILE}")
            # except Exception as cookie_err:
            #     logger.error(f"保存 Cookie 失败: {cookie_err}")
            # # ---------------------------

            # --- 核心：上传图片并发送通知 ---
            image_url = upload_to_cos_and_get_url(screenshot_path)
            
            server_ip = get_host_ip()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            os_info = f"{platform.system()} {platform.release()}"

            send_dingtalk_notification(
                "日报填写成功",
                f"## ✅ 日报填写成功\n\n"
                f"**服务器IP**: {server_ip}\n"
                f"**操作系统**: {os_info}\n"
                f"**执行时间**: {current_time}\n\n"
                f"**状态**: 已归档至腾讯云\n\n"
                f"**内容摘要**:\n{todo_content}",
                image_url
            )
            
            if is_api_call:
                return {"success": True, "message": "日报填写成功"}

        except Exception as e:
            logger.error(f"❌ 发生错误: {e}", exc_info=True)
            
            image_url = None
            if 'page' in locals():
                try:
                    screenshot_name = f"daily_report_error_{get_timestamp()}.png"
                    screenshot_path = os.path.join(IMG_LOG_DIR, screenshot_name)
                    page.screenshot(path=screenshot_path)
                    image_url = upload_to_cos_and_get_url(screenshot_path)
                except Exception as screenshot_error:
                    logger.error(f"截图失败: {screenshot_error}")

            server_ip = get_host_ip()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            os_info = f"{platform.system()} {platform.release()}"

            send_dingtalk_notification(
                "日报填写失败",
                f"## ❌ 日报填写失败\n\n"
                f"**服务器IP**: {server_ip}\n"
                f"**操作系统**: {os_info}\n"
                f"**执行时间**: {current_time}\n\n"
                f"**错误信息**: {str(e)}",
                image_url
            )
            
            if is_api_call:
                return {"success": False, "message": f"执行失败: {str(e)}"}

        finally:
            if browser:
                time.sleep(2)
                try:
                    browser.close()
                    logger.info("浏览器已关闭")
                except Exception as e:
                    logger.warning(f"关闭浏览器时出错 (可能已关闭): {e}")

if __name__ == "__main__":
    run()