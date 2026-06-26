"""
评分路由模块
用户评分、评分记录
"""
from flask import Blueprint, request, jsonify
from app.services.neo4j_service import Neo4jService
from app.services.recommend_service import RecommendService
from app.utils.auth import login_required
from app.config import Config

rating_bp = Blueprint("rating", __name__)


@rating_bp.route("/add", methods=["POST"])
@login_required
def add_rating():
    """添加或更新评分"""
    current = request.current_user
    data = request.get_json() or {}
    movie_id = data.get("movieId")
    rating = data.get("rating")

    if movie_id is None or rating is None:
        return jsonify({"code": 400, "msg": "movieId和rating不能为空"})

    rating = float(rating)
    if rating < 0.5 or rating > 5.0:
        return jsonify({"code": 400, "msg": "评分范围为0.5-5.0"})

    # 验证电影是否存在
    movie = Neo4jService.get_movie_detail(int(movie_id))
    if not movie:
        return jsonify({"code": 404, "msg": "电影不存在"})

    Neo4jService.add_or_update_rating(current["user_id"], int(movie_id), rating)
    # 新评分后清除推荐缓存，下次推荐会重新计算
    RecommendService.clear_cache()
    return jsonify({"code": 200, "msg": "评分成功"})


@rating_bp.route("/status", methods=["GET"])
@login_required
def get_rating_status():
    """获取当前用户对某部电影的评分"""
    current = request.current_user
    movie_id = request.args.get("movieId", type=int)
    if not movie_id:
        return jsonify({"code": 400, "msg": "movieId不能为空"})
    result = Neo4jService.get_user_movie_rating(current["user_id"], movie_id)
    return jsonify({"code": 200, "msg": "ok", "data": result})


@rating_bp.route("/my", methods=["GET"])
@login_required
def my_ratings():
    """获取我的评分记录"""
    current = request.current_user
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("pageSize", Config.DEFAULT_PAGE_SIZE, type=int)

    result = Neo4jService.get_user_ratings(current["user_id"], page, page_size)
    return jsonify({"code": 200, "msg": "ok", "data": result})


@rating_bp.route("/delete", methods=["DELETE"])
@login_required
def delete_rating():
    """删除评分"""
    current = request.current_user
    movie_id = request.args.get("movieId", type=int)
    if not movie_id:
        return jsonify({"code": 400, "msg": "movieId不能为空"})

    Neo4jService.delete_rating(current["user_id"], movie_id)
    return jsonify({"code": 200, "msg": "删除成功"})
