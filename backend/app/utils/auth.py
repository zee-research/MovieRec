"""
认证工具模块
JWT令牌生成与验证、密码加密
"""
import jwt
import datetime
from functools import wraps
from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.config import Config


def hash_password(password):
    """密码加密"""
    return generate_password_hash(password)


def verify_password(password, password_hash):
    """验证密码"""
    return check_password_hash(password_hash, password)


def generate_token(user_id, username, role):
    """生成JWT令牌"""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def decode_token(token):
    """解析JWT令牌"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token[7:]

        if not token:
            return jsonify({"code": 401, "msg": "请先登录"}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({"code": 401, "msg": "登录已过期，请重新登录"}), 401

        request.current_user = payload
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token[7:]

        if not token:
            return jsonify({"code": 401, "msg": "请先登录"}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({"code": 401, "msg": "登录已过期，请重新登录"}), 401

        if payload.get("role") != "admin":
            return jsonify({"code": 403, "msg": "无管理员权限"}), 403

        request.current_user = payload
        return f(*args, **kwargs)
    return decorated
