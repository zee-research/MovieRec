"""
MovieLens数据集下载脚本
下载ml-latest-small数据集到data/目录
"""
import os
import zipfile
import requests

# 数据集下载地址（MovieLens Small: 100,000条评分，9,000部电影，600个用户）
DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def download_movielens():
    """下载MovieLens数据集"""
    zip_path = os.path.join(DATA_DIR, "ml-latest-small.zip")
    extract_dir = os.path.join(DATA_DIR, "ml-latest-small")

    # 如果已经解压过则跳过
    if os.path.exists(extract_dir) and os.listdir(extract_dir):
        print("[INFO] MovieLens数据集已存在，跳过下载")
        return extract_dir

    os.makedirs(DATA_DIR, exist_ok=True)

    # 下载zip文件
    print(f"[INFO] 正在下载MovieLens数据集: {DATASET_URL}")
    response = requests.get(DATASET_URL, stream=True, timeout=120)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                pct = downloaded * 100 // total_size
                print(f"\r[INFO] 下载进度: {pct}%", end="", flush=True)

    print("\n[INFO] 下载完成，正在解压...")

    # 解压zip文件
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(DATA_DIR)

    # 删除zip文件
    os.remove(zip_path)
    print(f"[INFO] 数据集已解压到: {extract_dir}")
    return extract_dir


if __name__ == "__main__":
    download_movielens()
