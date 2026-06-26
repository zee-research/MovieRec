"""
知识图谱路由模块
图谱可视化数据接口
"""
from flask import Blueprint, request, jsonify
from app.services.neo4j_service import Neo4jService

graph_bp = Blueprint("graph", __name__)


@graph_bp.route("/movie/<int:movie_id>", methods=["GET"])
def get_movie_graph(movie_id):
    """获取电影关联的知识图谱（用于可视化）"""
    limit = request.args.get("limit", 30, type=int)
    data = Neo4jService.get_movie_knowledge_graph(movie_id, limit)
    return jsonify({"code": 200, "msg": "ok", "data": data})


@graph_bp.route("/global", methods=["GET"])
def get_global_graph():
    """获取全局知识图谱概览（限制规模）"""
    limit_movies = request.args.get("limitMovies", 50, type=int)
    limit_users = request.args.get("limitUsers", 30, type=int)
    data = Neo4jService.get_global_knowledge_graph(limit_movies, limit_users)
    return jsonify({"code": 200, "msg": "ok", "data": data})
