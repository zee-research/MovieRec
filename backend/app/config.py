"""
系统配置文件
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    """Flask应用配置"""
    # 密钥
    SECRET_KEY = os.environ.get("SECRET_KEY", "movierec-secret-key-1234")

    # JWT配置
    JWT_SECRET = os.environ.get("JWT_SECRET", "movierec-jwt-secret-1234")
    JWT_EXPIRATION_HOURS = 24

    #  数据库配置
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "123456")

    # 数据目录
    DATA_DIR = os.path.join(BASE_DIR, "data")
    PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
    RAW_DATA_DIR = os.path.join(DATA_DIR, "ml-latest-small")

    # 管理员默认账户
    ADMIN_USERNAME = "admin"
    ADMIN_DEFAULT_PASSWORD = "123456"

    # 用户重置密码
    RESET_PASSWORD = "123456"

    # 时区
    TIMEZONE = "Asia/Shanghai"

    # 分页默认值
    DEFAULT_PAGE_SIZE = 10
