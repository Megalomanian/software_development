# ML Platform

面向业务分析师的低代码 MLOps 平台。覆盖 **数据接入 → 特征工程 → 模型训练 → 模型部署 → 推理监控** 完整生命周期。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | FastAPI (Python 3.12+) + SQLAlchemy |
| 前端 | Next.js 15 + React 19 + TypeScript |
| UI | Tailwind CSS + Recharts + React Flow |
| 工作流 | Temporal |
| 实验追踪 | MLflow |
| 模型服务 | Ray Serve |
| 数据库 | PostgreSQL + ClickHouse |
| 对象存储 | MinIO (S3) |
| 监控 | Prometheus + Grafana + Evidently AI |
| 包管理 | uv (Python) / npm (前端) |

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Megalomanian/software_development.git
cd software_development

# 2. 安装 Python 依赖（使用清华镜像）
uv sync

# 3. 安装前端依赖
cd frontend && npm install && cd ..

# 4. 启动基础设施（Docker）
docker compose up -d postgres minio mlflow

# 5. 启动后端（:8000）
uv run uvicorn backend.main:app --reload

# 6. 启动前端（:3000）— 新终端
cd frontend && npm run dev
```

打开 http://localhost:3000 查看平台。

## 项目结构

```
├── backend/
│   ├── api/            # FastAPI 路由（data, experiments, models, deployments, monitoring）
│   ├── core/           # 配置、依赖注入、中间件
│   ├── services/       # 业务逻辑层
│   ├── models_db/      # SQLAlchemy ORM 模型
│   ├── workflows/      # Temporal 工作流
│   └── tests/          # 36 个测试用例
├── frontend/
│   ├── app/            # 10 个页面（数据/实验/Pipeline/模型/部署/监控）
│   └── components/     # Pipeline 编辑器、Sidebar 等
├── infra/              # Prometheus 配置
├── docker-compose.yml  # 8 个基础设施服务
└── .github/workflows/  # CI/CD（lint + test + build）
```

## 命令速查

```bash
# Python
uv sync                    # 安装依赖
uv run pytest              # 运行测试（34 passed, 2 skipped）
uv run ruff check .        # Lint

# 前端
cd frontend
npm run dev                # 开发服务器 :3000
npx tsc --noEmit           # 类型检查
npx next lint              # ESLint
npx next build             # 生产构建

# Docker
docker compose up -d       # 启动全部服务
docker compose down        # 停止全部
```

## 环境变量

所有变量使用 `MLP_` 前缀，定义在 `backend/core/config.py`：

| 变量 | 默认值 |
|------|--------|
| `MLP_DATABASE_URL` | `postgresql+asyncpg://mlp:mlp@localhost:5432/mlp` |
| `MLP_MLFLOW_TRACKING_URI` | `http://localhost:5000` |
| `MLP_MINIO_ENDPOINT` | `localhost:9000` |
| `MLP_TEMPORAL_HOST` | `localhost:7233` |
