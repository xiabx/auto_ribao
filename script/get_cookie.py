import time
import json
import os
import argparse
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# 添加 src 目录到路径，以便导入 config_loader
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from config_loader import config

# --- 配置 ---
LOGIN_URL = config['app']['target_url']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DATA_DIR = os.path.join(BASE_DIR, 'browser_data')
SESSION_FILE = os.path.join(BASE_DIR, 'session_token.json')

# 统一的 User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def _inject_stealth_scripts(context):
    """
    深度伪装：注入反检测脚本，模拟真实浏览器特征
    """
    stealth_js = """
        // 隐藏 WebDriver
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // 伪装 WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel(R) Iris(R) Xe Graphics';
            return getParameter.apply(this, [parameter]);
        };

        // 伪装 Plugins
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

        // 伪装 Languages
        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
        
        window.chrome = { runtime: {} };
    """
    context.add_init_script(stealth_js)

def export_session():
    """
    [本地运行] 打开浏览器，人工登录，然后导出 Cookie 和 LocalStorage 到 JSON 文件
    """
    print(f"🚀 启动浏览器进行登录...")
    print(f"📂 浏览器数据目录: {USER_DATA_DIR}")
    
    # 确保目录存在
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

    with sync_playwright() as p:
        # 启动持久化上下文 (带界面)
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False, 
            user_agent=USER_AGENT,
            args=[
                "--start-maximized", 
                "--disable-gpu", 
                "--lang=zh-CN",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ],
            viewport=None
        )
        
        _inject_stealth_scripts(context)
        
        page = context.pages[0] if context.pages else context.new_page()

        print(f"正在打开登录页面: {LOGIN_URL}")
        page.goto(LOGIN_URL)

        print("\n" + "=" * 50)
        print("请在打开的浏览器窗口中手动完成登录操作。")
        print("⚠️ 务必勾选“记住我”或“30天免登录”等选项！")
        print("登录成功并看到主页后，回到这里按 Enter 键继续...")
        print("=" * 50 + "\n")

        input("登录完成后请按 Enter 键...")

        # 1. 获取 Cookies
        cookies = context.cookies()
        
        # 2. 获取 LocalStorage
        origins = page.evaluate("() => window.location.origin")
        local_storage = page.evaluate("() => JSON.stringify(localStorage)")
        
        session_data = {
            "cookies": cookies,
            "origins": [
                {
                    "origin": origins,
                    "localStorage": json.loads(local_storage)
                }
            ],
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 保存到通用 JSON 文件
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=4)

        print(f"✅ 会话数据已导出到: {SESSION_FILE}")
        print(f"👉 请将 {os.path.basename(SESSION_FILE)} 上传到服务器项目根目录")
        print(f"👉 然后在服务器运行: python script/get_cookie.py --import")

        context.close()

def import_session():
    """
    [服务器运行] 读取 JSON 文件，注入到服务器本地的 browser_data 中
    """
    if not os.path.exists(SESSION_FILE):
        print(f"❌ 未找到会话文件: {SESSION_FILE}")
        print("请先在本地运行此脚本生成该文件，然后上传到服务器。")
        return

    print(f"🚀 正在导入会话数据...")
    
    if 'DISPLAY' in os.environ:
        print("检测到 DISPLAY 环境变量，正在移除以避免 X11 转发干扰...")
        del os.environ['DISPLAY']
    
    with open(SESSION_FILE, 'r', encoding='utf-8') as f:
        session_data = json.load(f)

    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            user_agent=USER_AGENT,
            args=[
                "--disable-gpu", 
                "--lang=zh-CN",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ]
        )
        
        _inject_stealth_scripts(context)
        
        page = context.pages[0] if context.pages else context.new_page()

        # 1. 注入 Cookies
        if 'cookies' in session_data:
            context.add_cookies(session_data['cookies'])
            print(f"✅ 已注入 {len(session_data['cookies'])} 个 Cookie")

        # 2. 注入 LocalStorage
        if 'origins' in session_data:
            for item in session_data['origins']:
                origin = item['origin']
                storage = item['localStorage']
                
                print(f"正在注入 LocalStorage 到: {origin}")
                try:
                    page.goto(origin)
                    page.evaluate(f"""(data) => {{
                        for (const [key, value] of Object.entries(data)) {{
                            localStorage.setItem(key, value);
                        }}
                    }}""", storage)
                    print(f"✅ LocalStorage 注入成功")
                except Exception as e:
                    print(f"⚠️ 注入 LocalStorage 失败: {e}")

        print("正在验证登录状态...")
        page.goto(LOGIN_URL)
        time.sleep(3)
        
        print(f"✅ 会话导入完成！数据已保存至: {USER_DATA_DIR}")
        context.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="会话管理工具")
    parser.add_argument('--import-session', action='store_true', dest='do_import', help="导入会话数据 (在服务器运行)")
    args = parser.parse_args()

    if args.do_import:
        import_session()
    else:
        export_session()
