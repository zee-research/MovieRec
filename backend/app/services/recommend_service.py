"""
推荐算法服务模块
包含协同过滤、矩阵分解(SVD)、知识图谱路径推荐、混合推荐模型、模型评估
"""
import os
import pickle
import numpy as np
import pandas as pd
from scipy.sparse.linalg import svds
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from app.config import Config
from app.services.neo4j_service import Neo4jService


class RecommendService:
    """推荐算法服务"""

    # 缓存：避免重复加载和计算
    _ratings_df = None
    _user_item_matrix = None
    _user_similarity = None
    _svd_predictions = None
    _user_id_map = None
    _movie_id_map = None
    _user_id_reverse = None
    _movie_id_reverse = None

    # 混合推荐模型缓存
    _fusion_model = None
    _fusion_scaler = None
    _fusion_svd_U = None
    _fusion_svd_Vt = None
    _fusion_svd_sigma = None
    _fusion_user_means = None
    _fusion_movie_stats = None
    _fusion_user_stats = None
    _kg_movie_features = None  # {movieId: {avgRating, genreCount, ratingCount}}

    @classmethod
    def load_ratings(cls):
        """加载评分数据"""
        if cls._ratings_df is not None:
            return cls._ratings_df
        csv_path = os.path.join(Config.PROCESSED_DATA_DIR, "ratings_cleaned.csv")
        cls._ratings_df = pd.read_csv(csv_path)
        print(f"[INFO] 加载评分数据: {len(cls._ratings_df)} 条")
        return cls._ratings_df

    @classmethod
    def build_user_item_matrix(cls):
        """构建用户-电影评分矩阵"""
        if cls._user_item_matrix is not None:
            return cls._user_item_matrix, cls._user_id_map, cls._movie_id_map

        ratings = cls.load_ratings()
        # 创建用户和电影的索引映射
        user_ids = sorted(ratings["userId"].unique())
        movie_ids = sorted(ratings["movieId"].unique())
        cls._user_id_map = {uid: idx for idx, uid in enumerate(user_ids)}
        cls._movie_id_map = {mid: idx for idx, mid in enumerate(movie_ids)}
        cls._user_id_reverse = {idx: uid for uid, idx in cls._user_id_map.items()}
        cls._movie_id_reverse = {idx: mid for mid, idx in cls._movie_id_map.items()}

        # 构建稀疏矩阵
        rows = ratings["userId"].map(cls._user_id_map).values
        cols = ratings["movieId"].map(cls._movie_id_map).values
        vals = ratings["rating"].values
        cls._user_item_matrix = csr_matrix(
            (vals, (rows, cols)),
            shape=(len(user_ids), len(movie_ids))
        )
        print(f"[INFO] 用户-电影矩阵: {cls._user_item_matrix.shape}")
        return cls._user_item_matrix, cls._user_id_map, cls._movie_id_map

    # ==================== 协同过滤推荐 ====================

    @classmethod
    def compute_user_similarity(cls):
        """计算用户相似度矩阵（基于余弦相似度）"""
        if cls._user_similarity is not None:
            return cls._user_similarity
        matrix, _, _ = cls.build_user_item_matrix()
        # 计算用户间余弦相似度
        cls._user_similarity = cosine_similarity(matrix)
        print(f"[INFO] 用户相似度矩阵: {cls._user_similarity.shape}")
        return cls._user_similarity

    @classmethod
    def collaborative_filtering_recommend(cls, user_id, top_n=20):
        """
        基于用户的协同过滤推荐
        找到相似用户喜欢但目标用户未看过的电影
        如果用户不在训练矩阵中，回退到基于知识图谱+热门电影推荐
        """
        matrix, user_map, movie_map = cls.build_user_item_matrix()
        if user_id not in user_map:
            return cls._fallback_recommend(user_id, top_n, "collaborative")

        user_sim = cls.compute_user_similarity()
        user_idx = user_map[user_id]

        # 获取相似度最高的前20个用户
        sim_scores = user_sim[user_idx]
        similar_users = np.argsort(sim_scores)[::-1][1:21]

        # 目标用户已评分的电影
        user_rated = set(matrix[user_idx].nonzero()[1])

        # 从相似用户的评分中推荐
        movie_scores = {}
        dense_matrix = matrix.toarray()
        for sim_user_idx in similar_users:
            sim_score = sim_scores[sim_user_idx]
            if sim_score <= 0:
                continue
            sim_user_ratings = dense_matrix[sim_user_idx]
            for movie_idx in range(len(sim_user_ratings)):
                if movie_idx not in user_rated and sim_user_ratings[movie_idx] > 0:
                    if movie_idx not in movie_scores:
                        movie_scores[movie_idx] = 0
                    movie_scores[movie_idx] += sim_score * sim_user_ratings[movie_idx]

        # 排序取top_n
        sorted_movies = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        results = []
        for movie_idx, score in sorted_movies:
            movie_id = cls._movie_id_reverse[movie_idx]
            item = {"movieId": int(movie_id), "score": round(float(score), 4), "method": "collaborative"}
            detail = Neo4jService.get_movie_detail(int(movie_id))
            if detail:
                item.update({"title": detail.get("title"), "genres": detail.get("genres"),
                             "genreNames": detail.get("genreNames", []),
                             "avgRating": detail.get("avgRating", 0), "year": detail.get("year")})
            results.append(item)
        return results

    # ==================== 矩阵分解推荐(SVD) ====================

    @classmethod
    def compute_svd(cls, k=50):
        """SVD矩阵分解，预测用户对所有电影的评分"""
        if cls._svd_predictions is not None:
            return cls._svd_predictions

        matrix, _, _ = cls.build_user_item_matrix()
        dense = matrix.toarray().astype(float)

        # 计算每个用户的评分均值
        user_means = np.true_divide(dense.sum(axis=1), (dense != 0).sum(axis=1) + 1e-9)
        # 去均值化
        dense_demeaned = dense.copy()
        for i in range(dense.shape[0]):
            mask = dense[i] != 0
            dense_demeaned[i, mask] -= user_means[i]

        # SVD分解（k为潜在因子数）
        k = min(k, min(dense_demeaned.shape) - 1)
        U, sigma, Vt = svds(csr_matrix(dense_demeaned), k=k)

        # 重建评分矩阵
        sigma_diag = np.diag(sigma)
        predicted = np.dot(np.dot(U, sigma_diag), Vt) + user_means.reshape(-1, 1)
        # 限制评分范围
        predicted = np.clip(predicted, 0.5, 5.0)
        cls._svd_predictions = predicted
        print(f"[INFO] SVD分解完成, k={k}")
        return cls._svd_predictions

    @classmethod
    def svd_recommend(cls, user_id, top_n=20):
        """基于SVD的推荐"""
        predictions = cls.compute_svd()
        matrix, user_map, movie_map = cls.build_user_item_matrix()

        if user_id not in user_map:
            return cls._fallback_recommend(user_id, top_n, "svd")

        user_idx = user_map[user_id]
        user_pred = predictions[user_idx]
        # 已评分电影
        user_rated = set(matrix[user_idx].nonzero()[1])

        # 推荐未评分且预测评分高的电影
        movie_scores = []
        for movie_idx in range(len(user_pred)):
            if movie_idx not in user_rated:
                movie_scores.append((movie_idx, user_pred[movie_idx]))

        sorted_movies = sorted(movie_scores, key=lambda x: x[1], reverse=True)[:top_n]
        results = []
        for movie_idx, pred_rating in sorted_movies:
            movie_id = cls._movie_id_reverse[movie_idx]
            item = {
                "movieId": int(movie_id),
                "score": round(float(pred_rating), 4),
                "method": "svd"
            }
            detail = Neo4jService.get_movie_detail(int(movie_id))
            if detail:
                item.update({"title": detail.get("title"), "genres": detail.get("genres"),
                             "genreNames": detail.get("genreNames", []),
                             "avgRating": detail.get("avgRating", 0), "year": detail.get("year")})
            results.append(item)
        return results

    # ==================== 知识图谱路径推荐 ====================

    @classmethod
    def kg_path_recommend(cls, user_id, top_n=20):
        """基于Neo4j知识图谱路径的推荐"""
        results = Neo4jService.get_kg_path_recommendations(user_id, limit=top_n)
        recommendations = []
        for r in results:
            recommendations.append({
                "movieId": r["movieId"],
                "score": round(float(r.get("pathScore", 0)) * 0.5 + float(r.get("avgRating", 0)) * 0.5, 4),
                "method": "knowledge_graph",
                "viaGenres": r.get("viaGenres", [])
            })
        return recommendations

    # ==================== 混合推荐模型 ====================
    # 采用特征级混合：从 CF/SVD/KG 三源提取多维特征向量，
    # 通过 GradientBoostingRegressor 学习非线性混合权重，
    # 实现模型层面的混合推荐（而非简单结果加权）

    @classmethod
    def _compute_movie_stats(cls, dense_matrix):
        """计算每部电影的统计特征：均分、评分数、评分标准差"""
        if cls._fusion_movie_stats is not None:
            return cls._fusion_movie_stats
        n_movies = dense_matrix.shape[1]
        stats = {}
        for j in range(n_movies):
            col = dense_matrix[:, j]
            mask = col > 0
            cnt = mask.sum()
            if cnt > 0:
                stats[j] = {
                    "avg": float(col[mask].mean()),
                    "count": int(cnt),
                    "std": float(col[mask].std()) if cnt > 1 else 0.0
                }
            else:
                stats[j] = {"avg": 0.0, "count": 0, "std": 0.0}
        cls._fusion_movie_stats = stats
        return stats

    @classmethod
    def _compute_user_stats(cls, dense_matrix):
        """计算每个用户的统计特征：均分、评分数、评分标准差"""
        if cls._fusion_user_stats is not None:
            return cls._fusion_user_stats
        n_users = dense_matrix.shape[0]
        stats = {}
        for i in range(n_users):
            row = dense_matrix[i]
            mask = row > 0
            cnt = mask.sum()
            if cnt > 0:
                stats[i] = {
                    "avg": float(row[mask].mean()),
                    "count": int(cnt),
                    "std": float(row[mask].std()) if cnt > 1 else 0.0
                }
            else:
                stats[i] = {"avg": 0.0, "count": 0, "std": 0.0}
        cls._fusion_user_stats = stats
        return stats

    @classmethod
    def _build_kg_features(cls):
        """从Neo4j批量获取所有电影的知识图谱特征，缓存为 {movieId: {...}}"""
        if cls._kg_movie_features is not None:
            return cls._kg_movie_features
        print("[INFO] 从Neo4j加载电影知识图谱特征...")
        try:
            rows = Neo4jService.get_all_movie_kg_features()
            features = {}
            for r in rows:
                features[r["movieId"]] = {
                    "avgRating": float(r.get("avgRating", 0)),
                    "genreCount": int(r.get("genreCount", 0)),
                    "ratingCount": int(r.get("ratingCount", 0)),
                }
            cls._kg_movie_features = features
            print(f"[INFO] 知识图谱特征加载完成: {len(features)} 部电影")
        except Exception as e:
            print(f"[WARN] 知识图谱特征加载失败: {e}")
            cls._kg_movie_features = {}
        return cls._kg_movie_features

    @classmethod
    def _extract_features(cls, user_idx, movie_idx, dense_matrix, user_sim,
                          svd_pred, user_stats, movie_stats,
                          U=None, Vt=None, kg_features=None, movie_id=None):
        """
        为 (user, movie) 对提取混合特征向量（12维）：
        [0]  cf_score        - 协同过滤预测分（相似用户加权平均）
        [1]  cf_confidence   - CF 置信度（参与预测的相似用户数占比）
        [2]  svd_score       - SVD 预测评分
        [3]  svd_user_norm   - 用户隐向量的范数（活跃度）
        [4]  svd_movie_norm  - 电影隐向量的范数（特征强度）
        [5]  user_avg        - 用户历史评分均值
        [6]  user_count      - 用户评分总数（log变换）
        [7]  movie_avg       - 电影全局均分
        [8]  movie_count     - 电影评分总数（log变换）
        [9]  kg_avg_rating   - 知识图谱中电影的全局平均评分
        [10] kg_genre_count  - 知识图谱中电影所属类型数量
        [11] kg_rating_count - 知识图谱中电影的评分数量（log变换）
        """
        features = np.zeros(12, dtype=float)

        # --- CF特征 ---
        sim_scores = user_sim[user_idx]
        top_k = 20
        top_users = np.argsort(sim_scores)[::-1][1:top_k + 1]
        num, den = 0.0, 0.0
        active_count = 0
        for su_idx in top_users:
            if dense_matrix[su_idx, movie_idx] > 0:
                num += sim_scores[su_idx] * dense_matrix[su_idx, movie_idx]
                den += abs(sim_scores[su_idx])
                active_count += 1
        features[0] = num / den if den > 0 else 0.0  # cf_score
        features[1] = active_count / top_k            # cf_confidence

        # --- SVD特征 ---
        features[2] = svd_pred[user_idx, movie_idx] if svd_pred is not None else 0.0
        if U is not None and Vt is not None:
            if user_idx < U.shape[0]:
                features[3] = float(np.linalg.norm(U[user_idx]))
            if movie_idx < Vt.shape[1]:
                features[4] = float(np.linalg.norm(Vt[:, movie_idx]))

        # --- 用户/电影统计特征 ---
        u_stat = user_stats.get(user_idx, {"avg": 0.0, "count": 0})
        m_stat = movie_stats.get(movie_idx, {"avg": 0.0, "count": 0})
        features[5] = u_stat["avg"]
        features[6] = np.log1p(u_stat["count"])
        features[7] = m_stat["avg"]
        features[8] = np.log1p(m_stat["count"])

        # --- 知识图谱特征 ---
        if kg_features and movie_id is not None:
            kg = kg_features.get(movie_id, {})
            features[9] = kg.get("avgRating", 0.0)
            features[10] = kg.get("genreCount", 0)
            features[11] = np.log1p(kg.get("ratingCount", 0))

        return features

    @classmethod
    def _train_fusion_model(cls):
        """
        训练混合推荐模型：
        1. 从训练集构建矩阵 & SVD分解
        2. 从Neo4j加载知识图谱电影特征
        3. 为每个 (user, movie, rating) 样本提取12维特征（CF+SVD+统计+KG）
        4. 训练 GradientBoostingRegressor 学习最优混合策略
        """
        if cls._fusion_model is not None:
            return cls._fusion_model, cls._fusion_scaler

        print("[INFO] 开始训练混合推荐模型...")
        train_df = cls._load_train_data()

        # 构建训练矩阵
        user_ids = sorted(train_df["userId"].unique())
        movie_ids = sorted(train_df["movieId"].unique())
        user_map = {uid: idx for idx, uid in enumerate(user_ids)}
        movie_map = {mid: idx for idx, mid in enumerate(movie_ids)}
        movie_reverse = {idx: mid for mid, idx in movie_map.items()}

        rows = train_df["userId"].map(user_map).dropna().astype(int).values
        cols = train_df["movieId"].map(movie_map).dropna().astype(int).values
        vals = train_df["rating"].values[:len(rows)]
        train_matrix = csr_matrix((vals, (rows, cols)),
                                  shape=(len(user_ids), len(movie_ids)))
        dense = train_matrix.toarray().astype(float)

        # 用户相似度
        user_sim = cosine_similarity(train_matrix)

        # SVD分解
        user_means = np.true_divide(dense.sum(axis=1),
                                    (dense != 0).sum(axis=1) + 1e-9)
        dense_demeaned = dense.copy()
        for i in range(dense.shape[0]):
            mask = dense[i] != 0
            dense_demeaned[i, mask] -= user_means[i]
        k = min(50, min(dense_demeaned.shape) - 1)
        U, sigma, Vt = svds(csr_matrix(dense_demeaned), k=k)
        svd_pred = np.dot(np.dot(U, np.diag(sigma)), Vt) + user_means.reshape(-1, 1)
        svd_pred = np.clip(svd_pred, 0.5, 5.0)

        # 缓存SVD分量
        cls._fusion_svd_U = U
        cls._fusion_svd_Vt = Vt
        cls._fusion_svd_sigma = sigma
        cls._fusion_user_means = user_means

        # 统计特征
        user_stats = cls._compute_user_stats(dense)
        movie_stats = cls._compute_movie_stats(dense)

        # 知识图谱特征
        kg_features = cls._build_kg_features()

        # 提取特征（采样训练以加速，最多10万样本）
        sample_size = min(len(train_df), 100000)
        sample_df = train_df.sample(n=sample_size, random_state=42)

        X_list, y_list = [], []
        for _, row in sample_df.iterrows():
            uid, mid, rating = int(row["userId"]), int(row["movieId"]), float(row["rating"])
            if uid not in user_map or mid not in movie_map:
                continue
            u_idx = user_map[uid]
            m_idx = movie_map[mid]
            feat = cls._extract_features(
                u_idx, m_idx, dense, user_sim, svd_pred,
                user_stats, movie_stats, U, Vt,
                kg_features=kg_features, movie_id=mid
            )
            X_list.append(feat)
            y_list.append(rating)

        X = np.array(X_list)
        y = np.array(y_list)

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 训练 GBRT 混合模型
        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42
        )
        model.fit(X_scaled, y)

        cls._fusion_model = model
        cls._fusion_scaler = scaler
        feature_names = ["CF评分", "CF置信度", "SVD评分", "用户隐向量范数",
                         "电影隐向量范数", "用户均分", "用户评分数",
                         "电影均分", "电影评分数", "KG平均评分", "KG类型数", "KG评分数"]
        print(f"[INFO] 混合模型训练完成, 特征数={X.shape[1]}, 样本数={X.shape[0]}")
        for name, imp in zip(feature_names, model.feature_importances_):
            print(f"  {name}: {imp:.4f}")

        # 缓存训练时的映射，供推荐使用
        cls._fusion_train_user_map = user_map
        cls._fusion_train_movie_map = movie_map
        cls._fusion_train_movie_reverse = movie_reverse
        cls._fusion_train_dense = dense
        cls._fusion_train_user_sim = user_sim
        cls._fusion_train_svd_pred = svd_pred

        return model, scaler

    @classmethod
    def hybrid_recommend(cls, user_id, top_n=20):
        """
        混合推荐模型（模型层面混合，非结果加权）：
        从 CF、SVD、KG 三个来源提取多维特征向量（12维），
        通过训练好的 GradientBoostingRegressor 预测评分，
        按预测分排序推荐。模型自动学习各来源最优组合权重。
        """
        model, scaler = cls._train_fusion_model()

        matrix, user_map, movie_map = cls.build_user_item_matrix()

        if user_id not in user_map:
            return cls._fallback_recommend(user_id, top_n, "hybrid")

        user_idx = user_map[user_id]
        dense = matrix.toarray().astype(float)
        user_sim = cls.compute_user_similarity()
        svd_pred = cls.compute_svd()
        kg_features = cls._build_kg_features()

        # 获取KG路径推荐（用于补充推荐来源标记）
        try:
            kg_results = cls.kg_path_recommend(user_id, top_n=top_n * 3)
            kg_map = {r["movieId"]: r.get("viaGenres", []) for r in kg_results}
        except Exception:
            kg_map = {}

        user_stats = cls._compute_user_stats(dense)
        movie_stats = cls._compute_movie_stats(dense)

        # 用户已评分电影
        user_rated = set(matrix[user_idx].nonzero()[1])

        # 对所有未评分电影提取特征并预测
        candidates = []
        batch_features = []
        batch_movie_idxs = []
        for movie_idx in range(dense.shape[1]):
            if movie_idx in user_rated:
                continue
            movie_id = cls._movie_id_reverse[movie_idx]
            feat = cls._extract_features(
                user_idx, movie_idx, dense, user_sim, svd_pred,
                user_stats, movie_stats,
                cls._fusion_svd_U, cls._fusion_svd_Vt,
                kg_features=kg_features, movie_id=movie_id
            )
            batch_features.append(feat)
            batch_movie_idxs.append(movie_idx)

        if not batch_features:
            return []

        X_batch = scaler.transform(np.array(batch_features))
        pred_scores = model.predict(X_batch)

        # 组合候选
        for i, movie_idx in enumerate(batch_movie_idxs):
            candidates.append((movie_idx, float(pred_scores[i])))

        # 排序取top_n
        sorted_movies = sorted(candidates, key=lambda x: x[1], reverse=True)[:top_n]

        # 获取电影详情
        results = []
        for movie_idx, score in sorted_movies:
            movie_id = cls._movie_id_reverse[movie_idx]
            detail = Neo4jService.get_movie_detail(int(movie_id))
            if detail:
                detail["hybridScore"] = round(score, 4)
                # 标记哪些推荐来源参与了此推荐
                methods = ["collaborative", "svd", "knowledge_graph"]
                detail["methods"] = methods
                detail["viaGenres"] = kg_map.get(movie_id, [])
                results.append(detail)
        return results

    @classmethod
    def clear_cache(cls):
        """清除缓存（新评分后需要重新计算）"""
        cls._ratings_df = None
        cls._user_item_matrix = None
        cls._user_similarity = None
        cls._svd_predictions = None
        cls._user_id_map = None
        cls._movie_id_map = None
        cls._user_id_reverse = None
        cls._movie_id_reverse = None
        # 混合模型缓存
        cls._fusion_model = None
        cls._fusion_scaler = None
        cls._fusion_svd_U = None
        cls._fusion_svd_Vt = None
        cls._fusion_svd_sigma = None
        cls._fusion_user_means = None
        cls._fusion_movie_stats = None
        cls._fusion_user_stats = None
        cls._kg_movie_features = None

    @classmethod
    def _fallback_recommend(cls, user_id, top_n, method_label):
        """
        回退推荐：当用户不在训练矩阵中时，
        优先使用知识图谱路径推荐，不足部分用热门电影补充
        """
        results = []
        seen_ids = set()

        # 先尝试知识图谱推荐
        try:
            kg_recs = Neo4jService.get_kg_path_recommendations(user_id, limit=top_n)
            for r in kg_recs:
                mid = r["movieId"]
                if mid not in seen_ids:
                    results.append({
                        "movieId": int(mid),
                        "score": round(float(r.get("avgRating", 0)), 4),
                        "method": method_label,
                        "note": "基于知识图谱回退推荐"
                    })
                    seen_ids.add(mid)
        except Exception as e:
            print(f"[WARN] 回退KG推荐失败: {e}")

        # 热门电影补充
        if len(results) < top_n:
            try:
                rated_ids = set(Neo4jService.get_user_rated_movie_ids(user_id))
                hot_movies = Neo4jService.get_hot_movies(limit=top_n * 2)
                for m in hot_movies:
                    mid = m["movieId"]
                    if mid not in seen_ids and mid not in rated_ids:
                        results.append({
                            "movieId": int(mid),
                            "score": round(float(m.get("avgRating", 0)), 4),
                            "method": method_label,
                            "note": "热门电影补充推荐"
                        })
                        seen_ids.add(mid)
                    if len(results) >= top_n:
                        break
            except Exception as e:
                print(f"[WARN] 回退热门推荐失败: {e}")

        # 为每个推荐结果补充电影详细信息
        enriched = []
        for r in results[:top_n]:
            detail = Neo4jService.get_movie_detail(r["movieId"])
            if detail:
                r.update({
                    "title": detail.get("title"),
                    "genres": detail.get("genres"),
                    "genreNames": detail.get("genreNames", []),
                    "avgRating": detail.get("avgRating", 0),
                    "year": detail.get("year"),
                })
            enriched.append(r)
        return enriched

    # ==================== 模型评估 ====================

    @classmethod
    def _load_test_data(cls):
        """加载测试集数据"""
        csv_path = os.path.join(Config.PROCESSED_DATA_DIR, "test.csv")
        return pd.read_csv(csv_path)

    @classmethod
    def _load_train_data(cls):
        """加载训练集数据"""
        csv_path = os.path.join(Config.PROCESSED_DATA_DIR, "train.csv")
        return pd.read_csv(csv_path)

    @classmethod
    def evaluate_collaborative_filtering(cls):
        """
        评估协同过滤模型
        在测试集上计算RMSE、MAE，并统计推荐覆盖率
        """
        test_df = cls._load_test_data()
        train_df = cls._load_train_data()

        # 用训练集构建用户-电影矩阵
        user_ids = sorted(train_df["userId"].unique())
        movie_ids = sorted(set(train_df["movieId"].unique()) | set(test_df["movieId"].unique()))
        user_map = {uid: idx for idx, uid in enumerate(user_ids)}
        movie_map = {mid: idx for idx, mid in enumerate(movie_ids)}

        rows = train_df["userId"].map(user_map).dropna().astype(int).values
        cols = train_df["movieId"].map(movie_map).dropna().astype(int).values
        vals = train_df["rating"].values[:len(rows)]
        train_matrix = csr_matrix((vals, (rows, cols)), shape=(len(user_ids), len(movie_ids)))

        # 计算用户相似度
        user_sim = cosine_similarity(train_matrix)
        dense_train = train_matrix.toarray()

        # 在测试集上预测
        predictions = []
        actuals = []
        recommended_movies = set()

        for _, row in test_df.iterrows():
            uid, mid, actual = int(row["userId"]), int(row["movieId"]), float(row["rating"])
            if uid not in user_map or mid not in movie_map:
                continue
            u_idx = user_map[uid]
            m_idx = movie_map[mid]

            # 基于相似用户的加权平均预测
            sim_scores = user_sim[u_idx]
            top_users = np.argsort(sim_scores)[::-1][1:21]
            num, den = 0.0, 0.0
            for su_idx in top_users:
                if dense_train[su_idx, m_idx] > 0:
                    num += sim_scores[su_idx] * dense_train[su_idx, m_idx]
                    den += abs(sim_scores[su_idx])
            pred = num / den if den > 0 else 3.0  # 默认预测值3.0
            pred = np.clip(pred, 0.5, 5.0)

            predictions.append(pred)
            actuals.append(actual)
            recommended_movies.add(mid)

        predictions = np.array(predictions)
        actuals = np.array(actuals)

        # 计算指标
        rmse = float(np.sqrt(np.mean((predictions - actuals) ** 2)))
        mae = float(np.mean(np.abs(predictions - actuals)))
        all_movies = set(movie_map.keys())
        coverage = len(recommended_movies) / len(all_movies) * 100 if all_movies else 0

        return {
            "method": "协同过滤",
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "coverage": round(coverage, 2),
            "testSamples": len(actuals)
        }

    @classmethod
    def evaluate_svd(cls):
        """
        评估SVD矩阵分解模型
        在测试集上计算RMSE、MAE，并统计推荐覆盖率
        """
        test_df = cls._load_test_data()
        train_df = cls._load_train_data()

        # 用训练集构建矩阵
        user_ids = sorted(train_df["userId"].unique())
        movie_ids = sorted(set(train_df["movieId"].unique()) | set(test_df["movieId"].unique()))
        user_map = {uid: idx for idx, uid in enumerate(user_ids)}
        movie_map = {mid: idx for idx, mid in enumerate(movie_ids)}

        rows = train_df["userId"].map(user_map).dropna().astype(int).values
        cols = train_df["movieId"].map(movie_map).dropna().astype(int).values
        vals = train_df["rating"].values[:len(rows)]
        train_matrix = csr_matrix((vals, (rows, cols)), shape=(len(user_ids), len(movie_ids)))
        dense = train_matrix.toarray().astype(float)

        # SVD分解
        user_means = np.true_divide(dense.sum(axis=1), (dense != 0).sum(axis=1) + 1e-9)
        dense_demeaned = dense.copy()
        for i in range(dense.shape[0]):
            mask = dense[i] != 0
            dense_demeaned[i, mask] -= user_means[i]

        k = min(50, min(dense_demeaned.shape) - 1)
        U, sigma, Vt = svds(csr_matrix(dense_demeaned), k=k)
        predicted_matrix = np.dot(np.dot(U, np.diag(sigma)), Vt) + user_means.reshape(-1, 1)
        predicted_matrix = np.clip(predicted_matrix, 0.5, 5.0)

        # 在测试集上评估
        predictions = []
        actuals = []
        recommended_movies = set()

        for _, row in test_df.iterrows():
            uid, mid, actual = int(row["userId"]), int(row["movieId"]), float(row["rating"])
            if uid not in user_map or mid not in movie_map:
                continue
            pred = predicted_matrix[user_map[uid], movie_map[mid]]
            predictions.append(pred)
            actuals.append(actual)
            recommended_movies.add(mid)

        predictions = np.array(predictions)
        actuals = np.array(actuals)

        rmse = float(np.sqrt(np.mean((predictions - actuals) ** 2)))
        mae = float(np.mean(np.abs(predictions - actuals)))
        all_movies = set(movie_map.keys())
        coverage = len(recommended_movies) / len(all_movies) * 100 if all_movies else 0

        return {
            "method": "SVD矩阵分解",
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "coverage": round(coverage, 2),
            "testSamples": len(actuals)
        }

    @classmethod
    def evaluate_fusion(cls):
        """
        评估混合推荐模型（加权融合）
        对测试集每条样本分别获取 CF、SVD、KG 三个预测分，
        按权重加权求和作为混合预测分，再计算 RMSE、MAE、Coverage。
        权重：CF 0.3 / SVD 0.4 / KG 0.3
        """
        W_CF, W_SVD, W_KG = 0.3, 0.4, 0.3

        test_df = cls._load_test_data()
        train_df = cls._load_train_data()

        # ---------- 构建训练矩阵 ----------
        user_ids = sorted(train_df["userId"].unique())
        movie_ids = sorted(set(train_df["movieId"].unique()) | set(test_df["movieId"].unique()))
        user_map = {uid: idx for idx, uid in enumerate(user_ids)}
        movie_map = {mid: idx for idx, mid in enumerate(movie_ids)}

        rows = train_df["userId"].map(user_map).dropna().astype(int).values
        cols = train_df["movieId"].map(movie_map).dropna().astype(int).values
        vals = train_df["rating"].values[:len(rows)]
        train_matrix = csr_matrix((vals, (rows, cols)),
                                  shape=(len(user_ids), len(movie_ids)))
        dense = train_matrix.toarray().astype(float)

        # ---------- CF：用户相似度 ----------
        user_sim = cosine_similarity(train_matrix)

        # ---------- SVD：矩阵分解预测 ----------
        user_means = np.true_divide(dense.sum(axis=1),
                                    (dense != 0).sum(axis=1) + 1e-9)
        dense_demeaned = dense.copy()
        for i in range(dense.shape[0]):
            mask = dense[i] != 0
            dense_demeaned[i, mask] -= user_means[i]
        k = min(50, min(dense_demeaned.shape) - 1)
        U, sigma, Vt = svds(csr_matrix(dense_demeaned), k=k)
        svd_pred = np.dot(np.dot(U, np.diag(sigma)), Vt) + user_means.reshape(-1, 1)
        svd_pred = np.clip(svd_pred, 0.5, 5.0)

        # ---------- KG：知识图谱电影均分映射 ----------
        kg_features = cls._build_kg_features()  # {movieId: {avgRating, ...}}

        # ---------- 在测试集上加权融合预测 ----------
        predictions, actuals = [], []
        recommended_movies = set()

        for _, row in test_df.iterrows():
            uid, mid, actual = int(row["userId"]), int(row["movieId"]), float(row["rating"])
            if uid not in user_map or mid not in movie_map:
                continue
            u_idx = user_map[uid]
            m_idx = movie_map[mid]

            # ---- CF 预测 ----
            sim_scores = user_sim[u_idx]
            top_users = np.argsort(sim_scores)[::-1][1:21]
            num, den = 0.0, 0.0
            for su_idx in top_users:
                if dense[su_idx, m_idx] > 0:
                    num += sim_scores[su_idx] * dense[su_idx, m_idx]
                    den += abs(sim_scores[su_idx])
            cf_pred = num / den if den > 0 else 3.0

            # ---- SVD 预测 ----
            svd_val = svd_pred[u_idx, m_idx]

            # ---- KG 预测（电影全局均分） ----
            kg_info = kg_features.get(mid, {})
            kg_val = kg_info.get("avgRating", 0.0)

            # ---- 加权融合 ----
            if kg_val > 0:
                pred = W_CF * cf_pred + W_SVD * svd_val + W_KG * kg_val
            else:
                # KG 无数据时，仅用 CF 和 SVD 重新归一化权重
                w_total = W_CF + W_SVD
                pred = (W_CF / w_total) * cf_pred + (W_SVD / w_total) * svd_val

            pred = np.clip(pred, 0.5, 5.0)
            predictions.append(pred)
            actuals.append(actual)
            recommended_movies.add(mid)

        predictions = np.array(predictions)
        actuals = np.array(actuals)

        rmse = float(np.sqrt(np.mean((predictions - actuals) ** 2)))
        mae = float(np.mean(np.abs(predictions - actuals)))
        all_movies = set(movie_map.keys())
        coverage = len(recommended_movies) / len(all_movies) * 100 if all_movies else 0

        return {
            "method": "混合推荐模型",
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "coverage": round(coverage, 2),
            "testSamples": len(actuals),
            "weights": {"CF": W_CF, "SVD": W_SVD, "KG": W_KG}
        }

    @classmethod
    def evaluate_all_models(cls):
        """
        评估所有推荐模型，返回对比结果
        包含协同过滤、SVD、混合模型、知识图谱的RMSE/MAE/Coverage指标
        """
        results = []
        try:
            cf_eval = cls.evaluate_collaborative_filtering()
            results.append(cf_eval)
            print(f"[INFO] 协同过滤评估: RMSE={cf_eval['rmse']}, MAE={cf_eval['mae']}, Coverage={cf_eval['coverage']}%")
        except Exception as e:
            print(f"[WARN] 协同过滤评估失败: {e}")
            results.append({"method": "协同过滤", "rmse": None, "mae": None, "coverage": None, "error": str(e)})

        try:
            svd_eval = cls.evaluate_svd()
            results.append(svd_eval)
            print(f"[INFO] SVD评估: RMSE={svd_eval['rmse']}, MAE={svd_eval['mae']}, Coverage={svd_eval['coverage']}%")
        except Exception as e:
            print(f"[WARN] SVD评估失败: {e}")
            results.append({"method": "SVD矩阵分解", "rmse": None, "mae": None, "coverage": None, "error": str(e)})

        try:
            kg_eval = cls.evaluate_kg()
            results.append(kg_eval)
            print(f"[INFO] 知识图谱评估: RMSE={kg_eval.get('rmse')}, MAE={kg_eval.get('mae')}, Coverage={kg_eval.get('coverage')}%")
        except Exception as e:
            print(f"[WARN] 知识图谱评估失败: {e}")
            results.append({"method": "知识图谱路径", "rmse": None, "mae": None, "coverage": None, "error": str(e)})

        # 混合推荐模型评估（最后计算，加权融合 CF/SVD/KG）
        try:
            fusion_eval = cls.evaluate_fusion()
            results.append(fusion_eval)
            print(f"[INFO] 混合模型评估: RMSE={fusion_eval['rmse']}, MAE={fusion_eval['mae']}, Coverage={fusion_eval['coverage']}%")
        except Exception as e:
            print(f"[WARN] 混合模型评估失败: {e}")
            results.append({"method": "混合推荐模型", "rmse": None, "mae": None, "coverage": None, "error": str(e)})

        return results

    @classmethod
    def evaluate_kg(cls):
        """
        评估知识图谱路径推荐模型
        用avgRating作为预测评分计算RMSE/MAE，并统计推荐覆盖率
        """
        test_df = cls._load_test_data()
        all_movies = set(test_df["movieId"].unique())
        all_users = test_df["userId"].unique()
        sample_users = all_users[:min(300, len(all_users))]

        # 为每个采样用户获取KG推荐，构建电影级别的avgRating映射
        kg_movies = set()
        kg_movie_rating = {}  # {movieId: avgRating} 电影级别映射
        for uid in sample_users:
            recs = Neo4jService.get_kg_path_recommendations(int(uid), limit=200)
            for r in recs:
                mid = r["movieId"]
                kg_movies.add(mid)
                avg = float(r.get("avgRating", 0))
                if avg > 0:
                    kg_movie_rating[mid] = avg

        # 在测试集上计算RMSE/MAE（电影级别匹配：只要电影被KG覆盖就可评估）
        predictions = []
        actuals = []
        for _, row in test_df.iterrows():
            mid, actual = int(row["movieId"]), float(row["rating"])
            if mid in kg_movie_rating:
                predictions.append(kg_movie_rating[mid])
                actuals.append(actual)

        kg_rmse = None
        kg_mae = None
        if len(predictions) > 0:
            predictions = np.array(predictions)
            actuals = np.array(actuals)
            kg_rmse = round(float(np.sqrt(np.mean((predictions - actuals) ** 2))), 4)
            kg_mae = round(float(np.mean(np.abs(predictions - actuals))), 4)

        kg_coverage = len(kg_movies & all_movies) / len(all_movies) * 100 if all_movies else 0
        return {
            "method": "知识图谱路径",
            "rmse": kg_rmse,
            "mae": kg_mae,
            "coverage": round(kg_coverage, 2),
            "testSamples": len(predictions)
        }
