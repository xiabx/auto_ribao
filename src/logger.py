import logging
import os
from logging.handlers import TimedRotatingFileHandler
from config_loader import config

# 获取当前文件所在目录的上一级目录 (项目根目录)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 获取日志目录配置，默认为 'log'
log_dir_name = config['app'].get('log_dir', 'log')
LOG_DIR = os.path.join(BASE_DIR, log_dir_name)

# 确保日志目录存在
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def setup_logger(name):
    """
    配置并返回一个 logger 实例
    日志将同时输出到控制台和文件
    文件按天轮转保存
    """
    logger = logging.getLogger(name)
    
    # 如果 logger 已经有 handler，说明已经配置过，直接返回
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)

    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. 文件 Handler (按天轮转)
    log_file = os.path.join(LOG_DIR, 'app.log')
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=30,  # 保留30天
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 默认 logger
logger = setup_logger('ribao')