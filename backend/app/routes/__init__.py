"""
路由注册模块
"""
from flask import jsonify


def register_routes(app):
    """注册所有路由蓝图"""

    # 健康检查
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({"code": 200, "msg": "服务运行正常", "data": None})

    # 用户模块：注册、登录、个人信息
    from app.routes.user import user_bp
    app.register_blueprint(user_bp, url_prefix="/api/user")

    # 电影模块：列表、详情、类型、热门
    from app.routes.movie import movie_bp
    app.register_blueprint(movie_bp, url_prefix="/api/movie")

    # 评分模块：添加评分、我的评分
    from app.routes.rating import rating_bp
    app.register_blueprint(rating_bp, url_prefix="/api/rating")

    # 推荐模块：协同过滤、SVD、知识图谱、混合推荐
    from app.routes.recommend import recommend_bp
    app.register_blueprint(recommend_bp, url_prefix="/api/recommend")

    # 知识图谱可视化
    from app.routes.graph import graph_bp
    app.register_blueprint(graph_bp, url_prefix="/api/graph")

    # 管理员模块：用户管理、评分管理、统计
    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
