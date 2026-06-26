"""
后端服务启动入口
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 50)
    print("  MovieRec 后端服务启动中...")
    print("  地址: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
