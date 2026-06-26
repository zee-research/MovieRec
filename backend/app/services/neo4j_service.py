"""
Neo4j图数据库服务模块
负责知识图谱的连接、数据导入、查询操作

知识图谱节点设计：
- User: 用户节点 (userId, username, password_hash, role, created_at)
- Movie: 电影节点 (movieId, title, clean_title, year, genres)
- Genre: 类型节点 (genreId, name)

知识图谱关系设计：
- (User)-[:RATED {rating, rating_normalized, date_str}]->(Movie)  用户评分关系
- (Movie)-[:BELONGS_TO]->(Genre)  电影类型关系
"""
import os
import pandas as pd
from neo4j import GraphDatabase
from app.config import Config


class Neo4jService:
    """Neo4j数据库操作服务"""

    _driver = None

    @classmethod
    def get_driver(cls):
        """获取Neo4j驱动（单例）"""
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(
                Config.NEO4J_URI,
                auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
            )
        return cls._driver

    @classmethod
    def close(cls):
        """关闭连接"""
        if cls._driver:
            cls._driver.close()
            cls._driver = None

    @classmethod
    def verify_connection(cls):
        """验证Neo4j连接是否正常"""
        try:
            driver = cls.get_driver()
            with driver.session() as session:
                session.run("RETURN 1")
            print("[INFO] Neo4j连接成功")
            return True
        except Exception as e:
            print(f"[ERROR] Neo4j连接失败: {e}")
            return False

    @classmethod
    def run_query(cls, query, parameters=None):
        """执行Cypher查询并返回结果"""
        driver = cls.get_driver()
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    @classmethod
    def run_write(cls, query, parameters=None):
        """执行Cypher写入操作"""
        driver = cls.get_driver()
        with driver.session() as session:
            session.run(query, parameters or {})

    # ==================== 初始化与数据导入 ====================

    @classmethod
    def create_constraints(cls):
        """创建唯一性约束和索引（兼容Neo4j 3.5）"""
        statements = [
            "CREATE CONSTRAINT ON (u:User) ASSERT u.userId IS UNIQUE",
            "CREATE CONSTRAINT ON (m:Movie) ASSERT m.movieId IS UNIQUE",
            "CREATE CONSTRAINT ON (g:Genre) ASSERT g.genreId IS UNIQUE",
            "CREATE INDEX ON :User(username)",
            "CREATE INDEX ON :Movie(title)",
            "CREATE INDEX ON :Genre(name)",
        ]
        for cypher in statements:
            try:
                cls.run_write(cypher)
            except Exception:
                pass  # 约束/索引已存在时忽略
        print("[INFO] Neo4j约束和索引创建完成")

    @classmethod
    def check_data_imported(cls):
        """检查数据是否已导入"""
        result = cls.run_query("MATCH (m:Movie) RETURN count(m) AS cnt")
        return result[0]["cnt"] > 0 if result else False

    @classmethod
    def import_genres(cls):
        """导入电影类型节点"""
        csv_path = os.path.join(Config.PROCESSED_DATA_DIR, "genres.csv")
        if not os.path.exists(csv_path):
            return
        genres = pd.read_csv(csv_path)
        for _, row in genres.iterrows():
            cls.run_write(
                "MERGE (g:Genre {genreId: $genreId}) SET g.name = $name",
                {"genreId": int(row["genreId"]), "name": row["genreName"]}
            )
        print(f"[INFO] 导入 {len(genres)} 个类型节点")

    @classmethod
    def import_movies(cls):
        """导入电影节点"""
        csv_path = os.path.join(Config.PROCESSED_DATA_DIR, "movies_cleaned.csv")
        if not os.path.exists(csv_path):
            return
        movies = pd.read_csv(csv_path)
        batch_size = 500
        for i in range(0, len(movies), batch_size):
            batch = movies.iloc[i:i + batch_size]
            records = []
            for _, row in batch.iterrows():
                records.append({
                    "movieId": int(row["movieId"]),
                    "title": str(row["title"]),
                    "clean_title": str(row["clean_title"]),
                    "year": int(row["year"]),
                    "genres": str(row["genres"])
                })
            cls.run_write(
                """UNWIND $records AS r
                MERGE (m:Movie {movieId: r.movieId})
                SET m.title = r.title, m.clean_title = r.clean_title,
                    m.year = r.year, m.genres = r.genres""",
                {"records": records}
            )
        print(f"[INFO] 导入 {len(movies)} 个电影节点")

    @classmethod
    def import_movie_genre_relations(cls):
        """导入电影-类型关系"""
        csv_path = os.path.join(Config.PROCESSED_DATA_DIR, "movie_genre.csv")
        if not os.path.exists(csv_path):
            return
        relations = pd.read_csv(csv_path)
        batch_size = 1000
        for i in range(0, len(relations), batch_size):
            batch = relations.iloc[i:i + batch_size]
            records = []
            for _, row in batch.iterrows():
                records.append({
                    "movieId": int(row["movieId"]),
                    "genreId": int(row["genreId"])
                })
            cls.run_write(
                """UNWIND $records AS r
                MATCH (m:Movie {movieId: r.movieId})
                MATCH (g:Genre {genreId: r.genreId})
                MERGE (m)-[:BELONGS_TO]->(g)""",
                {"records": records}
            )
        print(f"[INFO] 导入 {len(relations)} 条电影-类型关系")

    @classmethod
    def import_ratings(cls):
        """导入评分关系"""
        csv_path = os.path.join(Config.PROCESSED_DATA_DIR, "ratings_cleaned.csv")
        if not os.path.exists(csv_path):
            return
        ratings = pd.read_csv(csv_path)
        # 创建用户节点
        user_ids = ratings["userId"].unique()
        batch_size = 200
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size].tolist()
            cls.run_write(
                """UNWIND $userIds AS uid
                MERGE (u:User {userId: uid})
                ON CREATE SET u.username = 'user' + toString(uid),
                              u.role = 'user', u.created_at = timestamp()""",
                {"userIds": [int(uid) for uid in batch]}
            )
        print(f"[INFO] 导入 {len(user_ids)} 个用户节点")
        # 导入评分关系
        batch_size = 2000
        total = len(ratings)
        for i in range(0, total, batch_size):
            batch = ratings.iloc[i:i + batch_size]
            records = []
            for _, row in batch.iterrows():
                records.append({
                    "userId": int(row["userId"]),
                    "movieId": int(row["movieId"]),
                    "rating": float(row["rating"]),
                    "rating_normalized": float(row["rating_normalized"]),
                    "date_str": str(row["date_str"])
                })
            cls.run_write(
                """UNWIND $records AS r
                MATCH (u:User {userId: r.userId})
                MATCH (m:Movie {movieId: r.movieId})
                MERGE (u)-[rel:RATED]->(m)
                SET rel.rating = r.rating,
                    rel.rating_normalized = r.rating_normalized,
                    rel.date_str = r.date_str""",
                {"records": records}
            )
            pct = min((i + batch_size) * 100 // total, 100)
            print(f"\r[INFO] 评分导入进度: {pct}%", end="", flush=True)
        print(f"\n[INFO] 导入 {total} 条评分关系")

    @classmethod
    def import_all_data(cls):
        """执行全量数据导入"""
        if cls.check_data_imported():
            print("[INFO] Neo4j中已存在电影数据，跳过导入")
            return
        print("[INFO] 开始导入知识图谱数据...")
        cls.create_constraints()
        cls.import_genres()
        cls.import_movies()
        cls.import_movie_genre_relations()
        cls.import_ratings()
        print("[INFO] 知识图谱数据导入完成")

    # ==================== 查询操作 ====================

    @classmethod
    def get_statistics(cls):
        """获取知识图谱统计数据"""
        result = cls.run_query("""
            MATCH (m:Movie) WITH count(m) AS movieCount
            MATCH (u:User) WITH movieCount, count(u) AS userCount
            MATCH (g:Genre) WITH movieCount, userCount, count(g) AS genreCount
            MATCH ()-[r:RATED]->() WITH movieCount, userCount, genreCount, round(avg(r.rating) * 10) / 10.0 AS avgRating
            RETURN movieCount, userCount, genreCount, avgRating
        """)
        return result[0] if result else {}

    @classmethod
    def get_rating_distribution(cls):
        """获取评分分布"""
        return cls.run_query("""
            MATCH ()-[r:RATED]->()
            RETURN r.rating AS rating, count(r) AS count
            ORDER BY rating
        """)

    @classmethod
    def get_genre_movie_count(cls):
        """获取各类型电影数量"""
        return cls.run_query("""
            MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre)
            RETURN g.name AS genre, count(m) AS count
            ORDER BY count DESC
        """)

    @classmethod
    def get_movies_paginated(cls, page=1, page_size=10, keyword="", genre=""):
        """分页查询电影列表"""
        skip = (page - 1) * page_size
        where_clauses = []
        params = {"skip": skip, "limit": page_size}
        if keyword:
            where_clauses.append("(m.title CONTAINS $keyword OR m.clean_title CONTAINS $keyword)")
            params["keyword"] = keyword
        if genre:
            where_clauses.append("(m)-[:BELONGS_TO]->(:Genre {name: $genre})")
            params["genre"] = genre
        where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        count_result = cls.run_query(f"MATCH (m:Movie) {where_str} RETURN count(m) AS total", params)
        total = count_result[0]["total"] if count_result else 0

        data = cls.run_query(f"""
            MATCH (m:Movie) {where_str}
            OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
            WITH m, collect(g.name) AS genreNames
            OPTIONAL MATCH ()-[r:RATED]->(m)
            WITH m, genreNames, avg(r.rating) AS avgRating, count(r) AS ratingCount
            RETURN m.movieId AS movieId, m.title AS title, m.clean_title AS clean_title,
                   m.year AS year, m.genres AS genres, genreNames,
                   round(coalesce(avgRating, 0) * 100) / 100 AS avgRating, ratingCount
            ORDER BY ratingCount DESC
            SKIP $skip LIMIT $limit
        """, params)
        return {"total": total, "list": data, "page": page, "page_size": page_size}

    @classmethod
    def get_movie_detail(cls, movie_id):
        """获取电影详情"""
        result = cls.run_query("""
            MATCH (m:Movie {movieId: $movieId})
            OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
            WITH m, collect(g.name) AS genreNames
            OPTIONAL MATCH ()-[r:RATED]->(m)
            WITH m, genreNames, avg(r.rating) AS avgRating, count(r) AS ratingCount
            RETURN m.movieId AS movieId, m.title AS title, m.clean_title AS clean_title,
                   m.year AS year, m.genres AS genres, genreNames,
                   round(coalesce(avgRating, 0) * 100) / 100 AS avgRating, ratingCount
        """, {"movieId": movie_id})
        return result[0] if result else None

    @classmethod
    def get_movie_knowledge_graph(cls, movie_id, limit=30):
        """获取电影关联的知识图谱数据（用于可视化）"""
        nodes = []
        links = []
        # 电影节点及其类型关系
        movie_genre = cls.run_query("""
            MATCH (m:Movie {movieId: $movieId})-[:BELONGS_TO]->(g:Genre)
            RETURN m.movieId AS movieId, m.title AS title,
                   g.genreId AS genreId, g.name AS genreName
        """, {"movieId": movie_id})
        if not movie_genre:
            return {"nodes": [], "links": []}

        movie_title = movie_genre[0]["title"]
        nodes.append({"id": f"movie_{movie_id}", "name": movie_title, "type": "movie"})
        genre_ids_added = set()
        for row in movie_genre:
            gid = f"genre_{row['genreId']}"
            if gid not in genre_ids_added:
                nodes.append({"id": gid, "name": row["genreName"], "type": "genre"})
                genre_ids_added.add(gid)
            links.append({"source": f"movie_{movie_id}", "target": gid, "relation": "BELONGS_TO"})

        # 评分过该电影的用户（限制数量）
        user_ratings = cls.run_query("""
            MATCH (u:User)-[r:RATED]->(m:Movie {movieId: $movieId})
            RETURN u.userId AS userId, u.username AS username, r.rating AS rating
            ORDER BY r.rating DESC LIMIT $limit
        """, {"movieId": movie_id, "limit": limit})
        for row in user_ratings:
            uid = f"user_{row['userId']}"
            nodes.append({"id": uid, "name": row["username"], "type": "user"})
            links.append({"source": uid, "target": f"movie_{movie_id}",
                          "relation": "RATED", "rating": row["rating"]})
        return {"nodes": nodes, "links": links}

    @classmethod
    def get_global_knowledge_graph(cls, limit_movies=50, limit_users=30):
        """获取全局知识图谱（限制规模，用于总览可视化）"""
        nodes = []
        links = []
        node_ids = set()
        # 热门电影及其类型
        data = cls.run_query("""
            MATCH (m:Movie)<-[r:RATED]-()
            WITH m, count(r) AS cnt ORDER BY cnt DESC LIMIT $limit
            MATCH (m)-[:BELONGS_TO]->(g:Genre)
            RETURN m.movieId AS movieId, m.title AS title,
                   g.genreId AS genreId, g.name AS genreName
        """, {"limit": limit_movies})
        for row in data:
            mid = f"movie_{row['movieId']}"
            gid = f"genre_{row['genreId']}"
            if mid not in node_ids:
                nodes.append({"id": mid, "name": row["title"], "type": "movie"})
                node_ids.add(mid)
            if gid not in node_ids:
                nodes.append({"id": gid, "name": row["genreName"], "type": "genre"})
                node_ids.add(gid)
            links.append({"source": mid, "target": gid, "relation": "BELONGS_TO"})

        # 部分用户评分关系
        movie_ids = [int(n["id"].replace("movie_", "")) for n in nodes if n["type"] == "movie"]
        if movie_ids:
            user_data = cls.run_query("""
                MATCH (u:User)-[r:RATED]->(m:Movie)
                WHERE m.movieId IN $movieIds
                WITH u, m, r ORDER BY r.rating DESC
                WITH u, collect({movieId: m.movieId, rating: r.rating})[0..3] AS top_ratings
                LIMIT $limit
                UNWIND top_ratings AS tr
                RETURN u.userId AS userId, u.username AS username,
                       tr.movieId AS movieId, tr.rating AS rating
            """, {"movieIds": movie_ids, "limit": limit_users})
            for row in user_data:
                uid = f"user_{row['userId']}"
                mid = f"movie_{row['movieId']}"
                if uid not in node_ids:
                    nodes.append({"id": uid, "name": row["username"], "type": "user"})
                    node_ids.add(uid)
                if mid in node_ids:
                    links.append({"source": uid, "target": mid,
                                  "relation": "RATED", "rating": row["rating"]})
        return {"nodes": nodes, "links": links}

    @classmethod
    def get_all_genres(cls):
        """获取所有电影类型"""
        return cls.run_query("MATCH (g:Genre) RETURN g.genreId AS genreId, g.name AS name ORDER BY g.name")

    @classmethod
    def get_hot_movies(cls, limit=10):
        """获取热门电影（按评分人数排序）"""
        return cls.run_query("""
            MATCH (m:Movie)<-[r:RATED]-()
            WITH m, avg(r.rating) AS avgRating, count(r) AS ratingCount
            WHERE ratingCount > 10
            RETURN m.movieId AS movieId, m.title AS title, m.clean_title AS clean_title,
                   m.year AS year, m.genres AS genres,
                   round(avgRating * 100) / 100 AS avgRating, ratingCount
            ORDER BY ratingCount DESC LIMIT $limit
        """, {"limit": limit})

    # ==================== 用户管理 ====================

    @classmethod
    def find_user_by_username(cls, username):
        """根据用户名查找用户"""
        result = cls.run_query(
            "MATCH (u:User {username: $username}) RETURN u.userId AS userId, u.username AS username, "
            "u.password_hash AS password_hash, u.role AS role, u.created_at AS created_at",
            {"username": username}
        )
        return result[0] if result else None

    @classmethod
    def find_user_by_id(cls, user_id):
        """根据ID查找用户"""
        result = cls.run_query(
            "MATCH (u:User {userId: $userId}) RETURN u.userId AS userId, u.username AS username, "
            "u.password_hash AS password_hash, u.role AS role, u.created_at AS created_at",
            {"userId": user_id}
        )
        return result[0] if result else None

    @classmethod
    def get_next_user_id(cls):
        """获取下一个可用的用户ID"""
        result = cls.run_query("MATCH (u:User) RETURN max(u.userId) AS maxId")
        max_id = result[0]["maxId"] if result and result[0]["maxId"] else 0
        return max_id + 1

    @classmethod
    def create_user(cls, username, password_hash, role="user"):
        """创建用户"""
        user_id = cls.get_next_user_id()
        cls.run_write(
            """CREATE (u:User {userId: $userId, username: $username,
               password_hash: $password_hash, role: $role, created_at: timestamp()})""",
            {"userId": user_id, "username": username, "password_hash": password_hash, "role": role}
        )
        return user_id

    @classmethod
    def update_user_password(cls, user_id, password_hash):
        """更新用户密码"""
        cls.run_write(
            "MATCH (u:User {userId: $userId}) SET u.password_hash = $password_hash",
            {"userId": user_id, "password_hash": password_hash}
        )

    @classmethod
    def update_user_info(cls, user_id, username=None):
        """更新用户信息"""
        if username:
            cls.run_write(
                "MATCH (u:User {userId: $userId}) SET u.username = $username",
                {"userId": user_id, "username": username}
            )

    @classmethod
    def get_users_paginated(cls, page=1, page_size=10, keyword=""):
        """分页查询用户列表"""
        skip = (page - 1) * page_size
        params = {"skip": skip, "limit": page_size}
        where_str = ""
        if keyword:
            where_str = "WHERE u.username CONTAINS $keyword"
            params["keyword"] = keyword

        count_result = cls.run_query(f"MATCH (u:User) {where_str} RETURN count(u) AS total", params)
        total = count_result[0]["total"] if count_result else 0

        data = cls.run_query(f"""
            MATCH (u:User) {where_str}
            OPTIONAL MATCH (u)-[r:RATED]->()
            WITH u, count(r) AS ratingCount
            RETURN u.userId AS userId, u.username AS username, u.role AS role,
                   u.created_at AS created_at, ratingCount
            ORDER BY u.userId
            SKIP $skip LIMIT $limit
        """, params)
        return {"total": total, "list": data, "page": page, "page_size": page_size}

    @classmethod
    def delete_user(cls, user_id):
        """删除用户及其关系"""
        cls.run_write("MATCH (u:User {userId: $userId}) DETACH DELETE u", {"userId": user_id})

    # ==================== 评分管理 ====================

    @classmethod
    def add_or_update_rating(cls, user_id, movie_id, rating):
        """添加或更新评分"""
        import datetime as dt
        from app.config import Config
        now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        normalized = (rating - 0.5) / 4.5
        cls.run_write(
            """MATCH (u:User {userId: $userId})
            MATCH (m:Movie {movieId: $movieId})
            MERGE (u)-[r:RATED]->(m)
            SET r.rating = $rating, r.rating_normalized = $normalized, r.date_str = $date_str""",
            {"userId": user_id, "movieId": movie_id, "rating": rating,
             "normalized": normalized, "date_str": now_str}
        )

    @classmethod
    def get_user_movie_rating(cls, user_id, movie_id):
        """获取用户对某部电影的评分"""
        result = cls.run_query(
            "MATCH (u:User {userId: $userId})-[r:RATED]->(m:Movie {movieId: $movieId}) "
            "RETURN r.rating AS rating, r.date_str AS date_str",
            {"userId": user_id, "movieId": movie_id}
        )
        return result[0] if result else None

    @classmethod
    def get_user_ratings(cls, user_id, page=1, page_size=10):
        """获取用户的评分记录"""
        skip = (page - 1) * page_size
        params = {"userId": user_id, "skip": skip, "limit": page_size}

        count_result = cls.run_query(
            "MATCH (u:User {userId: $userId})-[r:RATED]->() RETURN count(r) AS total", params)
        total = count_result[0]["total"] if count_result else 0

        data = cls.run_query("""
            MATCH (u:User {userId: $userId})-[r:RATED]->(m:Movie)
            RETURN m.movieId AS movieId, m.title AS title, m.year AS year,
                   m.genres AS genres, r.rating AS rating, r.date_str AS date_str
            ORDER BY r.date_str DESC
            SKIP $skip LIMIT $limit
        """, params)
        return {"total": total, "list": data, "page": page, "page_size": page_size}

    @classmethod
    def get_ratings_paginated(cls, page=1, page_size=10, username="", movie_title=""):
        """分页查询所有评分（管理员用）"""
        skip = (page - 1) * page_size
        where_clauses = []
        params = {"skip": skip, "limit": page_size}
        if username:
            where_clauses.append("u.username CONTAINS $username")
            params["username"] = username
        if movie_title:
            where_clauses.append("m.title CONTAINS $movie_title")
            params["movie_title"] = movie_title
        where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        count_result = cls.run_query(
            f"MATCH (u:User)-[r:RATED]->(m:Movie) {where_str} RETURN count(r) AS total", params)
        total = count_result[0]["total"] if count_result else 0

        data = cls.run_query(f"""
            MATCH (u:User)-[r:RATED]->(m:Movie) {where_str}
            RETURN u.userId AS userId, u.username AS username,
                   m.movieId AS movieId, m.title AS title,
                   r.rating AS rating, r.date_str AS date_str
            ORDER BY r.date_str DESC
            SKIP $skip LIMIT $limit
        """, params)
        return {"total": total, "list": data, "page": page, "page_size": page_size}

    @classmethod
    def delete_rating(cls, user_id, movie_id):
        """删除评分"""
        cls.run_write(
            "MATCH (u:User {userId: $userId})-[r:RATED]->(m:Movie {movieId: $movieId}) DELETE r",
            {"userId": user_id, "movieId": movie_id}
        )

    @classmethod
    def get_user_rated_movie_ids(cls, user_id):
        """获取用户已评分的电影ID列表"""
        result = cls.run_query(
            "MATCH (u:User {userId: $userId})-[:RATED]->(m:Movie) RETURN m.movieId AS movieId",
            {"userId": user_id}
        )
        return [r["movieId"] for r in result]

    # ==================== 知识图谱路径查询（推荐用） ====================

    @classmethod
    def get_similar_movies_by_genre(cls, movie_id, limit=10):
        """通过知识图谱路径查找相同类型的电影"""
        return cls.run_query("""
            MATCH (m1:Movie {movieId: $movieId})-[:BELONGS_TO]->(g:Genre)<-[:BELONGS_TO]-(m2:Movie)
            WHERE m1 <> m2
            WITH m2, count(g) AS commonGenres
            OPTIONAL MATCH ()-[r:RATED]->(m2)
            WITH m2, commonGenres, avg(r.rating) AS avgRating, count(r) AS ratingCount
            RETURN m2.movieId AS movieId, m2.title AS title, m2.year AS year,
                   m2.genres AS genres, commonGenres,
                   round(coalesce(avgRating, 0) * 100) / 100 AS avgRating, ratingCount
            ORDER BY commonGenres DESC, avgRating DESC
            LIMIT $limit
        """, {"movieId": movie_id, "limit": limit})

    @classmethod
    def get_all_movie_kg_features(cls):
        """批量获取所有电影的知识图谱特征（avgRating, genreCount, ratingCount）"""
        return cls.run_query("""
            MATCH (m:Movie)
            OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
            WITH m, count(g) AS genreCount
            OPTIONAL MATCH ()-[r:RATED]->(m)
            WITH m, genreCount, avg(r.rating) AS avgRating, count(r) AS ratingCount
            RETURN m.movieId AS movieId,
                   round(coalesce(avgRating, 0) * 100) / 100 AS avgRating,
                   genreCount, toInteger(ratingCount) AS ratingCount
        """)

    @classmethod
    def get_kg_path_recommendations(cls, user_id, limit=20):
        """知识图谱路径推荐：通过用户高评分电影的类型路径发现新电影"""
        rated_ids = cls.get_user_rated_movie_ids(user_id)
        if not rated_ids:
            return []
        return cls.run_query("""
            MATCH (u:User {userId: $userId})-[r:RATED]->(m1:Movie)-[:BELONGS_TO]->(g:Genre)<-[:BELONGS_TO]-(m2:Movie)
            WHERE r.rating >= 3.0 AND NOT m2.movieId IN $ratedIds
            WITH m2, count(DISTINCT g) AS pathScore, collect(DISTINCT g.name) AS viaGenres
            OPTIONAL MATCH ()-[r2:RATED]->(m2)
            WITH m2, pathScore, viaGenres, avg(r2.rating) AS avgRating, count(r2) AS ratingCount
            RETURN m2.movieId AS movieId, m2.title AS title, m2.year AS year,
                   m2.genres AS genres, pathScore, viaGenres,
                   round(coalesce(avgRating, 0) * 100) / 100 AS avgRating, ratingCount
            ORDER BY pathScore DESC, avgRating DESC
            LIMIT $limit
        """, {"userId": user_id, "ratedIds": rated_ids, "limit": limit})
