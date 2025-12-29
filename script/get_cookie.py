import time
import json
import os
from playwright.sync_api import sync_playwright
from config_loader import config

# --- 配置 ---
# 目标登录页面，通常是主页或登录页
LOGIN_URL = config['app']['target_url']
# Cookie 保存路径 (项目根目录)
COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cookie.json')


def get_cookie():
    with sync_playwright() as p:
        # 启动一个带界面的浏览器，方便手动登录
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"正在打开登录页面: {LOGIN_URL}")
        page.goto(LOGIN_URL)

        print("\n" + "=" * 50)
        print("请在打开的浏览器窗口中手动完成登录操作。")
        print("登录成功后，不要关闭浏览器，回到这里按 Enter 键继续...")
        print("=" * 50 + "\n")

        input("登录完成后请按 Enter 键...")

        # 获取并保存 Cookie
        cookies = context.cookies()
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=4)

        print(f"✅ Cookie 已成功保存到: {COOKIE_FILE}")
        print("现在你可以关闭浏览器窗口了。")

        browser.close()


if __name__ == "__main__":
    # 将工作目录切换到 src，以便能正确导入 config_loader
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
    get_cookie()
