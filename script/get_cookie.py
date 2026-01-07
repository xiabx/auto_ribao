import time
import os
from playwright.sync_api import sync_playwright
from config_loader import config

# --- 配置 ---
# 目标登录页面
LOGIN_URL = config['app']['target_url']
# 浏览器数据保存路径 (项目根目录/browser_data)
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'browser_data')


def get_cookie():
    # 确保目录存在
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

    print(f"浏览器数据将保存至: {USER_DATA_DIR}")

    with sync_playwright() as p:
        # 使用 launch_persistent_context 启动持久化上下文
        # 这会自动保存 Cookies、Local Storage 等信息到指定目录
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,  # 有界面，方便手动登录
            args=["--start-maximized", "--disable-gpu", "--lang=zh-CN"],
            viewport=None # 禁用默认视口大小，允许最大化
        )
        
        page = context.pages[0] if context.pages else context.new_page()

        print(f"正在打开登录页面: {LOGIN_URL}")
        page.goto(LOGIN_URL)

        print("\n" + "=" * 50)
        print("请在打开的浏览器窗口中手动完成登录操作。")
        print("登录成功后，不要关闭浏览器，回到这里按 Enter 键继续...")
        print("=" * 50 + "\n")

        input("登录完成后请按 Enter 键...")

        # 持久化上下文会自动保存状态，无需手动 dump cookies
        print(f"✅ 登录状态已保存到: {USER_DATA_DIR}")
        print("现在你可以关闭浏览器窗口了。")

        context.close()


if __name__ == "__main__":
    # 将工作目录切换到 src，以便能正确导入 config_loader
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
    get_cookie()
