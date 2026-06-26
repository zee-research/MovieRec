// ============================================================
//  MovieRec 知识图谱数据库 Schema（Neo4j 3.5 Cypher）
//  字符编码: UTF-8
//  数据库引擎: Neo4j Community 3.5.35
//  协议: bolt://localhost:7687
// ============================================================

// ====================
//  1. 唯一性约束
// ====================

// 用户节点 —— userId 全局唯一
CREATE CONSTRAINT ON (u:User) ASSERT u.userId IS UNIQUE;

// 电影节点 —— movieId 全局唯一
CREATE CONSTRAINT ON (m:Movie) ASSERT m.movieId IS UNIQUE;

// 类型节点 —— genreId 全局唯一
CREATE CONSTRAINT ON (g:Genre) ASSERT g.genreId IS UNIQUE;


// ====================
//  2. 辅助索引
// ====================

// 用户名索引（登录查询加速）
CREATE INDEX ON :User(username);

// 电影标题索引（搜索加速）
CREATE INDEX ON :Movie(title);

// 类型名称索引
CREATE INDEX ON :Genre(name);


// ====================
//  3. 节点定义 & 示例数据
// ====================

// ---------- Genre 类型节点 ----------
// 属性:
//   genreId    : INTEGER  — 类型唯一标识（自增）
//   name       : STRING   — 类型名称（如 Action, Comedy, Drama 等）
//
// 数据来源: data/processed/genres.csv（共 20 种类型）

MERGE (g:Genre {genreId: 1})  SET g.name = 'Action';
MERGE (g:Genre {genreId: 2})  SET g.name = 'Adventure';
MERGE (g:Genre {genreId: 3})  SET g.name = 'Animation';
MERGE (g:Genre {genreId: 4})  SET g.name = 'Children';
MERGE (g:Genre {genreId: 5})  SET g.name = 'Comedy';
MERGE (g:Genre {genreId: 6})  SET g.name = 'Crime';
MERGE (g:Genre {genreId: 7})  SET g.name = 'Documentary';
MERGE (g:Genre {genreId: 8})  SET g.name = 'Drama';
MERGE (g:Genre {genreId: 9})  SET g.name = 'Fantasy';
MERGE (g:Genre {genreId: 10}) SET g.name = 'Film-Noir';
MERGE (g:Genre {genreId: 11}) SET g.name = 'Horror';
MERGE (g:Genre {genreId: 12}) SET g.name = 'IMAX';
MERGE (g:Genre {genreId: 13}) SET g.name = 'Musical';
MERGE (g:Genre {genreId: 14}) SET g.name = 'Mystery';
MERGE (g:Genre {genreId: 15}) SET g.name = 'Romance';
MERGE (g:Genre {genreId: 16}) SET g.name = 'Sci-Fi';
MERGE (g:Genre {genreId: 17}) SET g.name = 'Thriller';
MERGE (g:Genre {genreId: 18}) SET g.name = 'War';
MERGE (g:Genre {genreId: 19}) SET g.name = 'Western';
MERGE (g:Genre {genreId: 20}) SET g.name = '(no genres listed)';


// ---------- Movie 电影节点 ----------
// 属性:
//   movieId     : INTEGER — 电影唯一标识（来自 MovieLens）
//   title       : STRING  — 电影标题，含年份（如 "Toy Story (1995)"）
//   clean_title : STRING  — 去年份的纯标题（如 "Toy Story"）
//   year        : INTEGER — 上映年份
//   genres      : STRING  — 管道符分隔的类型（如 "Adventure|Animation|Children|Comedy|Fantasy"）
//
// 数据来源: data/processed/movies_cleaned.csv（共 9,742 部电影）
// 示例:
MERGE (m:Movie {movieId: 1})
SET m.title = 'Toy Story (1995)',
    m.clean_title = 'Toy Story',
    m.year = 1995,
    m.genres = 'Adventure|Animation|Children|Comedy|Fantasy';

// 实际导入通过批量 UNWIND 完成（见 import_data.py）


// ---------- User 用户节点 ----------
// 属性:
//   userId        : INTEGER — 用户唯一标识（训练集用户 1-610，注册用户 611+）
//   username      : STRING  — 用户名（训练集默认 'user' + userId，注册用户自定义）
//   password_hash : STRING  — bcrypt/SHA256 密码哈希（训练集用户无此字段）
//   role          : STRING  — 角色（'user' 或 'admin'）
//   created_at    : INTEGER — 创建时间戳（毫秒级）
//
// 数据来源: data/processed/ratings_cleaned.csv 中提取的唯一 userId
// 管理员账户由系统启动时自动创建

// 训练集用户批量导入示例:
MERGE (u:User {userId: 1})
ON CREATE SET u.username = 'user1',
              u.role = 'user',
              u.created_at = timestamp();

// 管理员账户（系统自动创建）:
MERGE (u:User {userId: 611})
ON CREATE SET u.username = 'admin',
              u.password_hash = '<sha256_hash>',
              u.role = 'admin',
              u.created_at = timestamp();


// ====================
//  4. 关系定义 & 示例数据
// ====================

// ---------- BELONGS_TO 电影-类型关系 ----------
// (Movie)-[:BELONGS_TO]->(Genre)
// 无属性，表示电影属于某个类型
// 一部电影可属于多个类型（多对多）
//
// 数据来源: data/processed/movie_genre.csv

MATCH (m:Movie {movieId: 1}), (g:Genre {genreId: 2})
MERGE (m)-[:BELONGS_TO]->(g);
// Toy Story → Adventure

MATCH (m:Movie {movieId: 1}), (g:Genre {genreId: 3})
MERGE (m)-[:BELONGS_TO]->(g);
// Toy Story → Animation


// ---------- RATED 用户-评分-电影关系 ----------
// (User)-[:RATED {rating, rating_normalized, date_str}]->(Movie)
// 属性:
//   rating            : FLOAT  — 原始评分（0.5 - 5.0，步长 0.5）
//   rating_normalized : FLOAT  — 归一化评分（0.0 - 1.0），公式: (rating - 0.5) / 4.5
//   date_str          : STRING — 评分时间（格式: "YYYY-MM-DD HH:MM:SS"）
//
// 数据来源: data/processed/ratings_cleaned.csv（共 100,836 条评分）

MATCH (u:User {userId: 1}), (m:Movie {movieId: 1})
MERGE (u)-[r:RATED]->(m)
SET r.rating = 4.0,
    r.rating_normalized = 0.7778,
    r.date_str = '2000-07-30 18:45:03';


// ====================
//  5. 数据统计查询
// ====================

// 查看各节点和关系数量
MATCH (m:Movie) WITH count(m) AS movieCount
MATCH (u:User)  WITH movieCount, count(u) AS userCount
MATCH (g:Genre) WITH movieCount, userCount, count(g) AS genreCount
MATCH ()-[r:RATED]->() WITH movieCount, userCount, genreCount, count(r) AS ratingCount
MATCH ()-[b:BELONGS_TO]->() WITH movieCount, userCount, genreCount, ratingCount, count(b) AS belongsToCount
RETURN movieCount, userCount, genreCount, ratingCount, belongsToCount;

// 预期结果:
// movieCount ≈ 9742, userCount ≈ 611+, genreCount = 20
// ratingCount ≈ 100836+, belongsToCount ≈ 22084


// ====================
//  6. 常用业务查询参考
// ====================

// 6.1 热门电影 TOP10（按评分人数）
MATCH (m:Movie)<-[r:RATED]-()
WITH m, avg(r.rating) AS avgRating, count(r) AS ratingCount
WHERE ratingCount > 10
RETURN m.movieId, m.title, round(avgRating * 100) / 100 AS avgRating, ratingCount
ORDER BY ratingCount DESC LIMIT 10;

// 6.2 用户评分记录
MATCH (u:User {userId: $userId})-[r:RATED]->(m:Movie)
RETURN m.title, r.rating, r.date_str
ORDER BY r.date_str DESC;

// 6.3 知识图谱路径推荐（通过高评分电影的类型发现新电影）
MATCH (u:User {userId: $userId})-[r:RATED]->(m1:Movie)-[:BELONGS_TO]->(g:Genre)<-[:BELONGS_TO]-(m2:Movie)
WHERE r.rating >= 3.5 AND NOT (u)-[:RATED]->(m2)
WITH m2, count(DISTINCT g) AS pathScore, collect(DISTINCT g.name) AS viaGenres
RETURN m2.title, pathScore, viaGenres
ORDER BY pathScore DESC LIMIT 20;

// 6.4 电影关联知识图谱（可视化用）
MATCH (m:Movie {movieId: $movieId})-[:BELONGS_TO]->(g:Genre)
RETURN m.title, g.name;

// 6.5 评分分布统计
MATCH ()-[r:RATED]->()
RETURN r.rating AS rating, count(r) AS count
ORDER BY rating;

// 6.6 各类型电影数量
MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre)
RETURN g.name AS genre, count(m) AS count
ORDER BY count DESC;
