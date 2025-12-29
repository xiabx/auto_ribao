# Auto Ribao (工作日报自动生成器)

这是一个基于 Python + Flask + Playwright 的自动化工具，旨在帮助用户自动生成、管理并提交工作日报。它结合了 AI 生成计划、Web 可视化管理、自动化填报以及钉钉通知等功能，极大地简化了日常汇报流程。

## ✨ 主要功能

*   **🤖 AI 智能生成**: 输入简要需求，自动生成详细的每日工作计划和进度描述。
*   **📅 可视化日历管理**: 提供直观的 Web 界面（基于 Vue + Element UI），可在日历上查看、编辑、删除每日计划。
*   **⚡ 自动化填报**: 使用 Playwright 模拟浏览器操作，自动登录目标系统并填写日报。
*   **🔔 钉钉通知**: 填报完成后自动发送钉钉通知，包含执行结果和截图（支持腾讯云 COS 图床）。
*   **🏖️ 节假日自动跳过**: 集成中国节假日数据，自动识别工作日，避免在假期执行任务。
*   **🍪 Cookie 持久化**: 支持 Cookie 自动更新与保存，延长登录有效期，减少手动干预。
*   **⏰ 定时任务**: 内置调度器，可自定义每日执行时间。

## 🛠️ 技术栈

*   **后端**: Python, Flask
*   **前端**: HTML, Vue.js, Element UI
*   **自动化**: Playwright
*   **存储**: JSON (本地数据), 腾讯云 COS (图片存储)
*   **通知**: 钉钉 Webhook

## 🚀 快速开始

### 1. 环境准备

确保已安装 Python 3.8+。

### 2. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器内核
playwright install chromium
```

### 3. 配置文件

在 `src` 目录下创建 `config.yaml` 文件（如果不存在），并参考以下格式进行配置：

```yaml
app:
  target_url: "https://your-target-system-url.com"  # 日报系统地址
  img_log_dir: "logs/images"                        # 截图保存目录
  port: 5001                                        # Web 服务端口

dingtalk:
  webhook: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN" # 钉钉机器人 Webhook

cos:
  secret_id: "YOUR_COS_SECRET_ID"       # 腾讯云 COS SecretId
  secret_key: "YOUR_COS_SECRET_KEY"     # 腾讯云 COS SecretKey
  region: "ap-shanghai"                 # COS 区域
  bucket: "your-bucket-name"            # COS Bucket 名称

security:
  admin_user: "admin"                   # Web 管理后台用户名
  admin_password: "password"            # Web 管理后台密码

scheduler:
  time: "18:00"                         # 每日自动执行时间
```

### 4. 获取登录 Cookie

首次使用前，需要手动登录一次以获取 Cookie：

```bash
python script/get_cookie.py
```
按照提示在弹出的浏览器中登录，登录成功后按回车键，Cookie 将自动保存到 `cookie.json`。

### 5. 启动服务

```bash
# 启动 Web 服务和定时任务
python src/app.py
```

启动后，访问 `http://127.0.0.1:5001/auto_ribao/` 进入管理后台。

## 📖 使用指南

1.  **登录后台**: 使用配置文件中设置的账号密码登录。
2.  **生成计划**:
    *   点击页面顶部的表单，输入“总需求描述”和“起止日期”。
    *   点击“生成计划”，AI 将自动规划每天的工作内容。
    *   在预览弹窗中确认或修改内容，选择“覆盖”或“追加”模式保存。
3.  **管理计划**:
    *   在日历视图中点击具体日期，可以查看、编辑或删除当天的计划。
    *   支持清除指定范围的计划。
4.  **自动执行**:
    *   系统会根据设置的时间（默认 18:00）自动检查当天是否有计划。
    *   如果有计划，将自动启动浏览器进行填报。
    *   执行结果会推送到钉钉群。
5.  **手动触发**: (开发调试用) 可以直接运行 `python src/handler.py` 立即触发一次填报。

## 📂 项目结构

```
auto-ribao/
├── src/
│   ├── app.py              # Flask Web 应用入口
│   ├── handler.py          # 自动化填报核心逻辑
│   ├── ai_planner.py       # AI 计划生成逻辑
│   ├── scheduler.py        # 定时任务调度
│   ├── db_manager.py       # 数据存储管理 (JSON)
│   └── ...
├── templates/              # 前端 HTML 模板
├── script/                 # 辅助脚本 (获取Cookie等)
├── logs/                   # 日志和截图目录
├── cookie.json             # 保存的登录凭证
├── requirements.txt        # 项目依赖
└── README.md               # 项目说明文档
```

## ⚠️ 注意事项

*   请确保服务器/运行环境能够访问目标日报系统。
*   若目标系统有复杂的验证码，可能需要人工辅助或额外的验证码识别服务。
*   Cookie 有效期取决于目标系统，建议定期检查或关注钉钉的失效提醒。

## 📝 License

MIT License
