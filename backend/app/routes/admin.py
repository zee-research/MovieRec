"""
管理员路由模块
用户管理、评分管理、系统统计、知识图谱数据、模型评估
"""
import json
import threading
from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.services.neo4j_service import Neo4jService
from app.services.recommend_service import RecommendService
from app.utils.auth import admin_required, hash_password, decode_token
from app.config import Config

admin_bp = Blueprint("admin", __name__)

# ==================== 后台评估任务状态 ====================
_eval_lock = threading.Lock()
_eval_state = {
    "running": False,
    "results": [],     # 已完成的模型评估结果
    "total": 4,        # 总模型数
    "done": False,      # 是否全部完成
}


# ==================== 统计 ====================

@admin_bp.route("/statistics", methods=["GET"])
@admin_required
def get_statistics():
    """获取知识图谱统计信息"""
    stats = Neo4jService.get_statistics()
    return jsonify({"code": 200, "msg": "ok", "data": stats})


@admin_bp.route("/rating-distribution", methods=["GET"])
@admin_required
def get_rating_distribution():
    """获取评分分布"""
    data = Neo4jService.get_rating_distribution()
    return jsonify({"code": 200, "msg": "ok", "data": data})


@admin_bp.route("/genre-stats", methods=["GET"])
@admin_required
def get_genre_stats():
    """获取各类型电影数量"""
    data = Neo4jService.get_genre_movie_count()
    return jsonify({"code": 200, "msg": "ok", "data": data})


# ==================== 用户管理 ====================

@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    """分页查询用户列表"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("pageSize", Config.DEFAULT_PAGE_SIZE, type=int)
    keyword = request.args.get("keyword", "").strip()

    result = Neo4jService.get_users_paginated(page, page_size, keyword)
    return jsonify({"code": 200, "msg": "ok", "data": result})


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """删除用户"""
    user = Neo4jService.find_user_by_id(user_id)
    if not user:
        return jsonify({"code": 404, "msg": "用户不存在"})
    if user.get("role") == "admin":
        return jsonify({"code": 400, "msg": "不能删除管理员账户"})

    Neo4jService.delete_user(user_id)
    return jsonify({"code": 200, "msg": "删除成功"})


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["PUT"])
@admin_required
def reset_user_password(user_id):
    """重置用户密码"""
    user = Neo4jService.find_user_by_id(user_id)
    if not user:
        return jsonify({"code": 404, "msg": "用户不存在"})

    Neo4jService.update_user_password(user_id, hash_password(Config.RESET_PASSWORD))
    return jsonify({"code": 200, "msg": f"密码已重置为 {Config.RESET_PASSWORD}"})


# ==================== 评分管理 ====================

@admin_bp.route("/ratings", methods=["GET"])
@admin_required
def get_ratings():
    """分页查询所有评分"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("pageSize", Config.DEFAULT_PAGE_SIZE, type=int)
    username = request.args.get("username", "").strip()
    movie_title = request.args.get("movieTitle", "").strip()

    result = Neo4jService.get_ratings_paginated(page, page_size, username, movie_title)
    return jsonify({"code": 200, "msg": "ok", "data": result})


@admin_bp.route("/ratings/delete", methods=["DELETE"])
@admin_required
def admin_delete_rating():
    """管理员删除评分"""
    user_id = request.args.get("userId", type=int)
    movie_id = request.args.get("movieId", type=int)
    if not user_id or not movie_id:
        return jsonify({"code": 400, "msg": "userId和movieId不能为空"})

    Neo4jService.delete_rating(user_id, movie_id)
    return jsonify({"code": 200, "msg": "删除成功"})


# ==================== 模型评估 ====================

def _run_evaluate_background(app):
    """后台线程：逐个评估模型，结果实时写入 _eval_state"""
    evaluators = [
        ("协同过滤", RecommendService.evaluate_collaborative_filtering),
        ("SVD矩阵分解", RecommendService.evaluate_svd),
        ("知识图谱路径", RecommendService.evaluate_kg),
        ("混合推荐模型", RecommendService.evaluate_fusion),
    ]
    with app.app_context():
        for name, func in evaluators:
            try:
                result = func()
                print(f"[INFO] {name}评估完成: {result}")
            except Exception as e:
                print(f"[WARN] {name}评估失败: {e}")
                result = {"method": name, "rmse": None, "mae": None, "coverage": None, "error": str(e)}
            with _eval_lock:
                _eval_state["results"].append(result)
        with _eval_lock:
            _eval_state["done"] = True
            _eval_state["running"] = False


@admin_bp.route("/model/evaluate-start", methods=["POST"])
@admin_required
def start_evaluate():
    """启动后台评估任务（不阻塞请求）"""
    with _eval_lock:
        if _eval_state["running"]:
            return jsonify({"code": 200, "msg": "评估任务已在运行中", "data": {"alreadyRunning": True}})
        _eval_state["running"] = True
        _eval_state["results"] = []
        _eval_state["done"] = False

    from flask import current_app
    app = current_app._get_current_object()
    t = threading.Thread(target=_run_evaluate_background, args=(app,), daemon=True)
    t.start()
    return jsonify({"code": 200, "msg": "评估任务已启动"})


@admin_bp.route("/model/evaluate-progress", methods=["GET"])
@admin_required
def get_evaluate_progress():
    """轮询获取评估进度和已完成的结果"""
    with _eval_lock:
        return jsonify({
            "code": 200,
            "msg": "ok",
            "data": {
                "running": _eval_state["running"],
                "done": _eval_state["done"],
                "total": _eval_state["total"],
                "completed": len(_eval_state["results"]),
                "results": list(_eval_state["results"]),
            }
        })
