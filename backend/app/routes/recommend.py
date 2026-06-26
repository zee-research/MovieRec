"""
推荐路由模块
协同过滤、SVD矩阵分解、知识图谱路径推荐、混合推荐
"""
from flask import Blueprint, request, jsonify
from app.services.recommend_service import RecommendService
from app.services.neo4j_service import Neo4jService
from app.utils.auth import login_required

recommend_bp = Blueprint("recommend", __name__)


@recommend_bp.route("/collaborative", methods=["GET"])
@login_required
def collaborative_recommend():
    """基于用户的协同过滤推荐"""
    current = request.current_user
    user_id = current["user_id"]
    top_n = request.args.get("topN", 20, type=int)

    try:
        results = RecommendService.collaborative_filtering_recommend(user_id, top_n)
        return jsonify({"code": 200, "msg": "ok", "data": results})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"推荐失败: {str(e)}"})


@recommend_bp.route("/svd", methods=["GET"])
@login_required
def svd_recommend():
    """基于SVD矩阵分解的推荐"""
    current = request.current_user
    user_id = current["user_id"]
    top_n = request.args.get("topN", 20, type=int)

    try:
        results = RecommendService.svd_recommend(user_id, top_n)
        return jsonify({"code": 200, "msg": "ok", "data": results})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"推荐失败: {str(e)}"})


@recommend_bp.route("/knowledge", methods=["GET"])
@login_required
def knowledge_recommend():
    """基于知识图谱路径的推荐"""
    current = request.current_user
    user_id = current["user_id"]
    top_n = request.args.get("topN", 20, type=int)

    try:
        results = Neo4jService.get_kg_path_recommendations(user_id, top_n)
        return jsonify({"code": 200, "msg": "ok", "data": results})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"推荐失败: {str(e)}"})


@recommend_bp.route("/hybrid", methods=["GET"])
@login_required
def hybrid_recommend():
    """混合推荐（综合多种算法）"""
    current = request.current_user
    user_id = current["user_id"]
    top_n = request.args.get("topN", 20, type=int)

    try:
        results = RecommendService.hybrid_recommend(user_id, top_n)
        return jsonify({"code": 200, "msg": "ok", "data": results})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"推荐失败: {str(e)}"})
