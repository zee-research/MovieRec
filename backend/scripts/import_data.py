"""
数据导入脚本 —— 将处理好的CSV数据导入Neo4j知识图谱
"""
import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.neo4j_service import Neo4jService


def main():
    print("=" * 50)
    print("  MovieRec 知识图谱数据导入")
    print("=" * 50)

    # 1. 验证连接
    if not Neo4jService.verify_connection():
        print("[FATAL] 无法连接到Neo4j，请检查：")
        print("  - Neo4j是否已启动")
        print("  - bolt://localhost:7687 是否可达")
        print("  - 用户名/密码是否正确（当前: neo4j / neo4j123）")
        sys.exit(1)

    # 2. 执行全量导入
    Neo4jService.import_all_data()

    # 3. 显示统计
    stats = Neo4jService.get_statistics()
    print("\n[INFO] 知识图谱统计信息：")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    Neo4jService.close()
    print("\n[DONE] 导入完成！")


if __name__ == "__main__":
    main()
