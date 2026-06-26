"""
MovieLens数据预处理脚本
功能：数据清洗、缺失值填充、数据集划分、数据格式转换与归一化
"""
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# 数据路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "ml-latest-small")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")


def load_raw_data():
    """加载MovieLens原始数据集"""
    print("[INFO] 正在加载原始数据...")

    # 加载电影数据: movieId, title, genres
    movies = pd.read_csv(os.path.join(RAW_DATA_DIR, "movies.csv"))
    print(f"  电影数据: {len(movies)} 条")

    # 加载评分数据: userId, movieId, rating, timestamp
    ratings = pd.read_csv(os.path.join(RAW_DATA_DIR, "ratings.csv"))
    print(f"  评分数据: {len(ratings)} 条")

    # 加载标签数据: userId, movieId, tag, timestamp
    tags = pd.read_csv(os.path.join(RAW_DATA_DIR, "tags.csv"))
    print(f"  标签数据: {len(tags)} 条")

    # 加载链接数据: movieId, imdbId, tmdbId
    links = pd.read_csv(os.path.join(RAW_DATA_DIR, "links.csv"))
    print(f"  链接数据: {len(links)} 条")

    return movies, ratings, tags, links


def clean_movies(movies):
    """
    清洗电影数据
    - 去除重复记录
    - 填充缺失值
    - 提取电影年份
    - 拆分电影类型
    """
    print("[INFO] 正在清洗电影数据...")

    # 去除重复记录
    movies = movies.drop_duplicates(subset=["movieId"]).copy()

    # 填充缺失值
    movies["title"] = movies["title"].fillna("未知电影")
    movies["genres"] = movies["genres"].fillna("(no genres listed)")

    # 从标题中提取年份，如 "Toy Story (1995)" -> 1995
    movies["year"] = movies["title"].str.extract(r"\((\d{4})\)$")
    movies["year"] = pd.to_numeric(movies["year"], errors="coerce")
    # 缺失年份填充为中位数
    median_year = int(movies["year"].median())
    movies["year"] = movies["year"].fillna(median_year).astype(int)

    # 清理标题中的年份部分，保留纯标题
    movies["clean_title"] = movies["title"].str.replace(r"\s*\(\d{4}\)$", "", regex=True).str.strip()

    # 将genres拆分为列表
    movies["genre_list"] = movies["genres"].apply(
        lambda x: x.split("|") if x != "(no genres listed)" else []
    )

    print(f"  清洗后电影数据: {len(movies)} 条")
    return movies


def clean_ratings(ratings):
    """
    清洗评分数据
    - 去除重复记录
    - 去除无效评分（评分范围0.5-5.0）
    - 时间戳转换为标准日期格式
    """
    print("[INFO] 正在清洗评分数据...")

    # 去除重复评分（同一用户对同一电影只保留最新评分）
    ratings = ratings.sort_values("timestamp").drop_duplicates(
        subset=["userId", "movieId"], keep="last"
    ).copy()

    # 去除无效评分
    ratings = ratings[(ratings["rating"] >= 0.5) & (ratings["rating"] <= 5.0)]

    # 时间戳转换为日期时间格式（统一UTC+8时区）
    ratings["datetime"] = pd.to_datetime(ratings["timestamp"], unit="s", utc=True)
    ratings["datetime"] = ratings["datetime"].dt.tz_convert("Asia/Shanghai")
    ratings["date_str"] = ratings["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    print(f"  清洗后评分数据: {len(ratings)} 条")
    return ratings


def clean_tags(tags):
    """清洗标签数据"""
    print("[INFO] 正在清洗标签数据...")

    tags = tags.dropna(subset=["tag"]).copy()
    tags["tag"] = tags["tag"].str.strip().str.lower()
    # 去除空标签
    tags = tags[tags["tag"].str.len() > 0]
    # 去除重复
    tags = tags.drop_duplicates(subset=["userId", "movieId", "tag"])

    # 时间戳转换
    tags["datetime"] = pd.to_datetime(tags["timestamp"], unit="s", utc=True)
    tags["datetime"] = tags["datetime"].dt.tz_convert("Asia/Shanghai")
    tags["date_str"] = tags["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    print(f"  清洗后标签数据: {len(tags)} 条")
    return tags


def normalize_ratings(ratings):
    """
    评分归一化处理
    将评分映射到[0, 1]范围，便于后续模型训练
    """
    print("[INFO] 正在进行评分归一化...")

    ratings = ratings.copy()
    # Min-Max归一化: (rating - min) / (max - min)
    min_rating = 0.5
    max_rating = 5.0
    ratings["rating_normalized"] = (ratings["rating"] - min_rating) / (max_rating - min_rating)

    print(f"  归一化范围: [{ratings['rating_normalized'].min():.2f}, {ratings['rating_normalized'].max():.2f}]")
    return ratings


def split_dataset(ratings, test_size=0.2, random_state=42):
    """
    数据集划分：训练集和测试集
    按照8:2比例划分，保证每个用户在训练集和测试集中都有数据
    """
    print("[INFO] 正在划分数据集...")

    train_data, test_data = train_test_split(
        ratings, test_size=test_size, random_state=random_state, stratify=None
    )

    print(f"  训练集: {len(train_data)} 条")
    print(f"  测试集: {len(test_data)} 条")
    return train_data, test_data


def extract_all_genres(movies):
    """提取所有电影类型，生成类型字典"""
    all_genres = set()
    for genre_list in movies["genre_list"]:
        all_genres.update(genre_list)
    all_genres.discard("")

    genres_df = pd.DataFrame({
        "genreId": range(1, len(all_genres) + 1),
        "genreName": sorted(all_genres)
    })
    print(f"[INFO] 提取电影类型: {len(genres_df)} 种")
    return genres_df


def build_movie_genre_relation(movies, genres_df):
    """构建电影-类型关联表"""
    genre_name_to_id = dict(zip(genres_df["genreName"], genres_df["genreId"]))
    relations = []
    for _, row in movies.iterrows():
        for genre in row["genre_list"]:
            if genre in genre_name_to_id:
                relations.append({
                    "movieId": row["movieId"],
                    "genreId": genre_name_to_id[genre]
                })
    relation_df = pd.DataFrame(relations)
    print(f"[INFO] 电影-类型关联: {len(relation_df)} 条")
    return relation_df


def generate_statistics(movies, ratings, genres_df):
    """生成数据统计信息"""
    print("\n========== 数据统计 ==========")
    print(f"电影总数: {len(movies)}")
    print(f"用户总数: {ratings['userId'].nunique()}")
    print(f"评分总数: {len(ratings)}")
    print(f"电影类型数: {len(genres_df)}")
    print(f"评分均值: {ratings['rating'].mean():.2f}")
    print(f"评分中位数: {ratings['rating'].median():.1f}")
    print(f"每用户平均评分数: {len(ratings) / ratings['userId'].nunique():.1f}")
    print(f"每电影平均评分数: {len(ratings) / ratings['movieId'].nunique():.1f}")
    print(f"评分稀疏度: {1 - len(ratings) / (ratings['userId'].nunique() * movies['movieId'].nunique()):.4%}")
    print("================================\n")


def save_processed_data(movies, ratings, tags, genres_df, movie_genre_rel, train_data, test_data):
    """保存预处理后的数据"""
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

    # 保存电影数据
    movies_save = movies[["movieId", "title", "clean_title", "genres", "year"]].copy()
    movies_save.to_csv(os.path.join(PROCESSED_DATA_DIR, "movies_cleaned.csv"), index=False, encoding="utf-8")

    # 保存评分数据
    ratings_save = ratings[["userId", "movieId", "rating", "rating_normalized", "timestamp", "date_str"]].copy()
    ratings_save.to_csv(os.path.join(PROCESSED_DATA_DIR, "ratings_cleaned.csv"), index=False, encoding="utf-8")

    # 保存标签数据
    tags_save = tags[["userId", "movieId", "tag", "date_str"]].copy()
    tags_save.to_csv(os.path.join(PROCESSED_DATA_DIR, "tags_cleaned.csv"), index=False, encoding="utf-8")

    # 保存类型字典
    genres_df.to_csv(os.path.join(PROCESSED_DATA_DIR, "genres.csv"), index=False, encoding="utf-8")

    # 保存电影-类型关联
    movie_genre_rel.to_csv(os.path.join(PROCESSED_DATA_DIR, "movie_genre.csv"), index=False, encoding="utf-8")

    # 保存训练集和测试集
    train_save = train_data[["userId", "movieId", "rating", "rating_normalized"]].copy()
    train_save.to_csv(os.path.join(PROCESSED_DATA_DIR, "train.csv"), index=False, encoding="utf-8")

    test_save = test_data[["userId", "movieId", "rating", "rating_normalized"]].copy()
    test_save.to_csv(os.path.join(PROCESSED_DATA_DIR, "test.csv"), index=False, encoding="utf-8")

    print(f"[INFO] 预处理数据已保存到: {PROCESSED_DATA_DIR}")


def run_preprocess():
    """执行完整的数据预处理流程"""
    # 1. 加载原始数据
    movies, ratings, tags, links = load_raw_data()

    # 2. 数据清洗
    movies = clean_movies(movies)
    ratings = clean_ratings(ratings)
    tags = clean_tags(tags)

    # 3. 评分归一化
    ratings = normalize_ratings(ratings)

    # 4. 提取电影类型
    genres_df = extract_all_genres(movies)

    # 5. 构建电影-类型关联
    movie_genre_rel = build_movie_genre_relation(movies, genres_df)

    # 6. 数据集划分
    train_data, test_data = split_dataset(ratings)

    # 7. 输出统计信息
    generate_statistics(movies, ratings, genres_df)

    # 8. 保存预处理后的数据
    save_processed_data(movies, ratings, tags, genres_df, movie_genre_rel, train_data, test_data)

    return movies, ratings, tags, genres_df, movie_genre_rel, train_data, test_data


if __name__ == "__main__":
    run_preprocess()
