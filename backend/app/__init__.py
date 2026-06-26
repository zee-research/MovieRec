"""
Flask应用工厂模块
"""
from flask import Flask
from flask_cors import CORS
from app.config import Config


def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # 启用CORS跨域
    CORS(app, supports_credentials=True)

    # 注册路由蓝图
    from app.routes import register_routes
    register_routes(app)
    # 初始化管理员账户
    _init_admin()

    return app


def _init_admin():
    """确保管理员账户存在，已存在则重置密码"""
    try:
        from app.services.neo4j_service import Neo4jService
        from app.utils.auth import hash_password

        password_hash = hash_password(Config.ADMIN_DEFAULT_PASSWORD)
        admin = Neo4jService.find_user_by_username(Config.ADMIN_USERNAME)
        if not admin:
            Neo4jService.create_user(Config.ADMIN_USERNAME, password_hash, role="admin")
            print(f"[INFO] 管理员账户已创建: {Config.ADMIN_USERNAME} / {Config.ADMIN_DEFAULT_PASSWORD}")
        else:
            # 已存在则重置密码为默认密码
            Neo4jService.update_user_password(admin["userId"], password_hash)
            print(f"[INFO] 管理员密码已重置为: {Config.ADMIN_DEFAULT_PASSWORD}")
    except Exception as e:
        print(f"[WARN] 管理员账户初始化跳过: {e}")

