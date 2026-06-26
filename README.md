# MovieRec

基于知识图谱的个性化电影推荐系统。本项目为本科毕业设计项目，围绕 MovieLens 数据集构建电影推荐应用，结合协同过滤、SVD 矩阵分解、知识图谱路径推荐和混合推荐模型，为用户提供个性化电影推荐、电影浏览、评分管理和知识图谱可视化能力。

## 项目简介

MovieRec 采用前后端分离架构：

- 前端使用 Vue 3、Vite、Element Plus 和 ECharts。
- 后端使用 Flask 提供 REST API。
- 图数据库使用 Neo4j 存储用户、电影、类型和评分关系。
- 推荐算法使用 Pandas、NumPy、SciPy 和 scikit-learn 实现。

数据集使用 MovieLens `ml-latest-small`，包含约 9,742 部电影、100,836 条评分记录和 610 位用户。

## 主要功能

- 用户注册、登录和个人信息管理
- 电影列表浏览、搜索、类型筛选和电影详情查看
- 用户电影评分、评分记录查看和删除
- 协同过滤推荐
- SVD 矩阵分解推荐
- 基于 Neo4j 的知识图谱路径推荐
- 混合推荐模型
- 电影知识图谱和全局知识图谱可视化
- 管理端用户、电影、评分和模型评估管理

## 技术栈

### 前端

- Vue 3
- Vite
- Vue Router
- Pinia
- Element Plus
- ECharts
- Axios

### 后端

- Python
- Flask
- Flask-CORS
- PyJWT
- Neo4j Python Driver
- Pandas
- NumPy
- SciPy
- scikit-learn

### 数据库

- Neo4j

## 目录结构

```text
MovieRec/
├── backend/                 # Flask 后端服务
│   ├── app/
│   │   ├── routes/          # API 路由
│   │   ├── services/        # Neo4j 服务和推荐算法
│   │   └── utils/           # 认证工具
│   ├── data/                # MovieLens 原始数据和预处理数据
│   ├── scripts/             # 数据下载、预处理和导入脚本
│   ├── requirements.txt
│   └── run.py
├── frontend/                # Vue 前端项目
│   ├── src/
│   │   ├── api/
│   │   ├── layouts/
│   │   ├── views/
│   │   └── components/
│   └── package.json
├── sql/                     # Neo4j Schema 和示例 Cypher
├── start_backend.bat
├── start_frontend.bat
├── start_neo4j.bat
└── 技术文档.md
```

## 运行说明

### 1. 启动 Neo4j

确保本机已安装并启动 Neo4j，默认连接配置位于：

```text
backend/app/config.py
```

默认配置：

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=123456
```

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 导入数据

```bash
python scripts/import_data.py
```

如需重新生成预处理数据，可执行：

```bash
python scripts/preprocess_data.py
```

### 4. 启动后端

```bash
python run.py
```

默认后端地址：

```text
http://127.0.0.1:5000
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认前端地址以 Vite 输出为准。

## 默认账号

系统初始化时会创建管理员账号：

```text
用户名：admin
密码：123456
```

## 推荐算法说明

本系统实现了四类推荐方式：

- 协同过滤：基于用户评分行为计算用户相似度。
- SVD 矩阵分解：对用户-电影评分矩阵进行低维隐因子建模。
- 知识图谱路径推荐：通过用户高评分电影的类型路径发现候选电影。
- 混合推荐：融合协同过滤、SVD 和知识图谱相关特征，提高推荐效果。

## 说明

本仓库为已完成的本科毕业设计项目归档版本，保留原项目结构、数据和实现内容。
