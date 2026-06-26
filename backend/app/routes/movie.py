"""
电影路由模块
电影列表、详情、类型、热门电影
"""
from flask import Blueprint, request, jsonify
from app.services.neo4j_service import Neo4jService
from app.utils.auth import login_required
from app.config import Config

movie_bp = Blueprint("movie", __name__)


@movie_bp.route("/list", methods=["GET"])
def get_movie_list():
    """分页查询电影列表"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("pageSize", Config.DEFAULT_PAGE_SIZE, type=int)
    keyword = request.args.get("keyword", "").strip()
    genre = request.args.get("genre", "").strip()

    result = Neo4jService.get_movies_paginated(page, page_size, keyword, genre)
    return jsonify({"code": 200, "msg": "ok", "data": result})


@movie_bp.route("/detail/<int:movie_id>", methods=["GET"])
def get_movie_detail(movie_id):
    """获取电影详情"""
    movie = Neo4jService.get_movie_detail(movie_id)
    if not movie:
        return jsonify({"code": 404, "msg": "电影不存在"})
    return jsonify({"code": 200, "msg": "ok", "data": movie})


@movie_bp.route("/genres", methods=["GET"])
def get_genres():
    """获取所有电影类型"""
    genres = Neo4jService.get_all_genres()
    return jsonify({"code": 200, "msg": "ok", "data": genres})


@movie_bp.route("/hot", methods=["GET"])
def get_hot_movies():
    """获取热门电影"""
    limit = request.args.get("limit", 10, type=int)
    movies = Neo4jService.get_hot_movies(limit)
    return jsonify({"code": 200, "msg": "ok", "data": movies})


@movie_bp.route("/similar/<int:movie_id>", methods=["GET"])
def get_similar_movies(movie_id):
    """获取相似电影（基于知识图谱类型路径）"""
    limit = request.args.get("limit", 10, type=int)
    movies = Neo4jService.get_similar_movies_by_genre(movie_id, limit)
    return jsonify({"code": 200, "msg": "ok", "data": movies})
