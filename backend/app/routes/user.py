"""
用户路由模块
注册、登录、个人信息、修改密码
"""
from flask import Blueprint, request, jsonify
from app.services.neo4j_service import Neo4jService
from app.utils.auth import (
    hash_password, verify_password, generate_token,
    login_required, admin_required
)
from app.config import Config

user_bp = Blueprint("user", __name__)


@user_bp.route("/register", methods=["POST"])
def register():
    """用户注册"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"code": 400, "msg": "用户名和密码不能为空"})

    if len(username) < 2 or len(username) > 20:
        return jsonify({"code": 400, "msg": "用户名长度需2-20个字符"})

    if len(password) < 6:
        return jsonify({"code": 400, "msg": "密码长度不少于6位"})

    # 检查用户名是否已存在
    existing = Neo4jService.find_user_by_username(username)
    if existing:
        return jsonify({"code": 400, "msg": "用户名已存在"})

    password_hash = hash_password(password)
    user_id = Neo4jService.create_user(username, password_hash, role="user")
    token = generate_token(user_id, username, "user")

    return jsonify({
        "code": 200,
        "msg": "注册成功",
        "data": {
            "userId": user_id,
            "username": username,
            "role": "user",
            "token": token
        }
    })


@user_bp.route("/login", methods=["POST"])
def login():
    """用户登录"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"code": 400, "msg": "用户名和密码不能为空"})

    user = Neo4jService.find_user_by_username(username)
    if not user:
        return jsonify({"code": 400, "msg": "用户不存在"})

    if not user.get("password_hash"):
        return jsonify({"code": 400, "msg": "账户未设置密码，请联系管理员"})

    if not verify_password(password, user["password_hash"]):
        return jsonify({"code": 400, "msg": "密码错误"})

    token = generate_token(user["userId"], user["username"], user.get("role", "user"))

    return jsonify({
        "code": 200,
        "msg": "登录成功",
        "data": {
            "userId": user["userId"],
            "username": user["username"],
            "role": user.get("role", "user"),
            "token": token
        }
    })


@user_bp.route("/info", methods=["GET"])
@login_required
def get_user_info():
    """获取当前用户信息"""
    current = request.current_user
    user = Neo4jService.find_user_by_id(current["user_id"])
    if not user:
        return jsonify({"code": 404, "msg": "用户不存在"})

    return jsonify({
        "code": 200,
        "msg": "ok",
        "data": {
            "userId": user["userId"],
            "username": user["username"],
            "role": user.get("role", "user"),
            "created_at": str(user.get("created_at", ""))
        }
    })


@user_bp.route("/password", methods=["PUT"])
@login_required
def change_password():
    """修改密码"""
    current = request.current_user
    data = request.get_json() or {}
    old_password = data.get("oldPassword", "").strip()
    new_password = data.get("newPassword", "").strip()

    if not old_password or not new_password:
        return jsonify({"code": 400, "msg": "旧密码和新密码不能为空"})

    if len(new_password) < 6:
        return jsonify({"code": 400, "msg": "新密码长度不少于6位"})

    user = Neo4jService.find_user_by_id(current["user_id"])
    if not user:
        return jsonify({"code": 404, "msg": "用户不存在"})

    if not verify_password(old_password, user["password_hash"]):
        return jsonify({"code": 400, "msg": "旧密码错误"})

    Neo4jService.update_user_password(user["userId"], hash_password(new_password))
    return jsonify({"code": 200, "msg": "密码修改成功"})
