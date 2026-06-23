# 🧠 ML Platform

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/fastapi-0.115%2B-green" alt="FastAPI">
  <img src="https://img.shields.io/badge/sklearn-1.6%2B-orange" alt="sklearn">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="License">
  <img src="https://img.shields.io/badge/tests-60%20passed-success" alt="Tests">
</p>

<p align="center">
  <strong>从数据到推理，一行命令就够了。</strong><br>
  面向数据分析师的端到端 MLOps 平台 — 无需 Docker、无需 Kubernetes、无需前端。
</p>

---

## 🤔 解决了什么问题？

数据分析师的日常困境：

| 痛点 | 传统方式 | ML Platform |
|------|---------|-------------|
| 📂 数据分散在 CSV/Excel 里 | 手动 pandas 读取、清洗、画图 | `mlp data upload` → 自动画像 |
| 🧪 训练模型要写一堆代码 | 手写 sklearn + MLflow 集成 | `mlp experiments run-sklearn` → 自动追踪 |
| 📋 多个训练任务互相覆盖 | 打开 5 个终端手动排队 | `mlp queue watch` → FIFO 队列自动调度 |
| 🚀 部署模型要学 Docker/K8s | `docker build` + `kubectl apply` | `mlp deployments create` → 内存加载，即刻可用 |
| 📊 线上模型看不到效果 | 自己做 Grafana + Prometheus | `mlp monitor metrics` → 请求量/延迟/错误率一键查 |

**一句话**：把 "数据分析师 → 模型上线" 的路径从 **几周** 缩短到 **几分钟**。

---

## 🏗 架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户交互层                              │
│  ┌──────────────────┐  ┌──────────────────────────────┐  │
│  │  🖥 mlp CLI       │  │  🐍 Python SDK                │  │
│  │  typer + rich    │  │  from ml_platform import …   │  │
│  └────────┬─────────┘  └────────────┬─────────────────┘  │
│           │        HTTP REST        │                     │
│           └───────────┬────────────┘                     │
├───────────────────────┼─────────────────────────────────┤
│               🚀 REST API (FastAPI :8000)                │
│  ┌─────────┬─────────┬──────────┬──────────┬──────────┐ │
│  │ /data   │ /exp    │ /models  │ /deploy  │ /monitor │ │
│  └────┬────┴────┬────┴────┬─────┴────┬─────┴────┬─────┘ │
├───────┼─────────┼─────────┼──────────┼──────────┼───────┤
│       │   ┌─────┴─────┐   │   ┌──────┴──────┐   │        │
│       │   │ PostgreSQL│   │   │   MLflow    │   │        │
│       │   │  / SQLite │   │   │  (追踪实验)  │   │        │
│       │   └───────────┘   │   └─────────────┘   │        │
│       │                   │                     │        │
│  ┌────┴────────┐   ┌──────┴──────┐   ┌─────────┴────┐   │
│  │ 训练队列     │   │ 本地模型注册 │   │  推理日志     │   │
│  │ FIFO Worker │   │  (内存推理)  │   │  (ClickHouse) │   │
│  └─────────────┘   └─────────────┘   └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

```bash
# 1. 安装
uv sync                         # 后端
cd cli && uv sync && cd ..      # CLI

# 2. 启动（默认 SQLite，零依赖启动）
uv run uvicorn backend.main:app --reload

# 3. 登录
mlp auth login --register -u alice -e alice@test.com -p secret123

# 4. 走通全流程
mlp data upload iris.csv
mlp experiments create -n demo -d <id> -t species --type classification
mlp experiments run-sklearn <exp-id>
mlp experiments metrics <exp-id>
```

服务启动后访问 **http://localhost:8000/docs** 查看交互式 Swagger 文档。

| 启动方式 | 命令 |
|---------|------|
| 默认 (SQLite) | `uv run uvicorn backend.main:app --reload` |
| 指定 PostgreSQL | `MLP_DATABASE_URL=postgresql+asyncpg://...` |
| 指定 MLflow Server | `MLP_MLFLOW_TRACKING_URI=http://mlflow:5000` |

---

## 🖥 CLI 命令参考

### 安装

```bash
cd cli && uv sync
./cli/.venv/bin/mlp --help

# 或通过 wheel 安装（从 Release 下载后）
uv tool install --from ml_platform_cli-*.whl --with ml_platform-*.whl ml-platform-cli
```

### 命令树

```
mlp
├── 🔐 auth        login / logout / whoami / register
├── 📂 data        upload / list / get / profile / preview / delete
├── 🧪 experiments  list / ids / get / create / run / run-sklearn /
│                   metrics / compare / delete / enqueue
├── 📋 queue        status / watch
├── 🤖 models       list / ids / get / register / promote / delete / download
├── 🚀 deployments  list / get / create / stop / delete / predict
├── 📊 monitor      metrics / drift
├── ⚙️  config       show / --server <url>
├── 📈 status       系统总览
└── 💚 health       健康检查
```

### 常用示例

```bash
# ── 认证 ──
mlp auth login --register -u alice -e alice@test.com -p secret123
mlp auth whoami
mlp config                           # 查看当前配置
mlp config --server http://prod:8000 # 切换后端

# ── 数据 ──
mlp data upload iris.csv
mlp data list
mlp data profile <id>                # 数值列: mean/std/min/max, 文本列: top 20

# ── 实验 ──
mlp experiments ids                    # 列出所有实验 ID（完整 UUID，无分页）
mlp experiments create -n my-exp -d <dataset-id> -t target --type classification
mlp experiments run-sklearn <exp-id>
mlp experiments metrics <exp-id>      # rich 表格展示 accuracy / mse / r2

# ── 训练队列 ──
mlp experiments enqueue <exp-id>      # 加入 FIFO 队列
mlp queue status                      # 当前队列状态
mlp queue watch                       # 实时刷新面板 (Ctrl+C 退出)

# ── 模型 ──
mlp models ids                        # 列出所有模型 ID（完整 UUID，无分页）
mlp models register -n my-model -e <exp-id>
mlp models download <model-id> -o model.pkl

# ── 部署 ──
mlp deployments create -m <model-id>
mlp deployments predict <dep-id> -d '{"f1":5.1,"f2":3.5}'
mlp deployments stop <dep-id>

# ── 监控 ──
mlp monitor metrics <dep-id> --range 24h
mlp monitor drift <dep-id>

# ── 系统 ──
mlp status
mlp health
```

### 配置后端 URL

```bash
# 方式 1: 环境变量（优先级最高）
MLP_SERVER=http://192.168.1.100:8000 mlp status

# 方式 2: mlp config 命令（持久化）
mlp config --server http://192.168.1.100:8000

# 方式 3: 登录时指定
mlp auth login -e alice@test.com -p xxx --server http://prod:8000
```

---

## 🐍 Python SDK

```python
import asyncio
from ml_platform import Client

async def main():
    async with Client("http://localhost:8000") as client:
        # 注册
        user = await client.auth.register("alice", "alice@test.com", "secret123")
        client.set_token(user["access_token"])

        # 上传 → 训练 → 部署 → 预测
        ds = await client.data.upload("iris.csv")
        exp = await client.experiments.create(
            name="demo", dataset_id=ds["id"],
            target_column="species", problem_type="classification")
        await client.experiments.run_sklearn(exp["id"])
        model = await client.models.register("iris-model", exp["id"])
        dep = await client.deployments.create(model["id"])
        pred = await client.deployments.predict(dep["id"], {
            "sepal_length": 5.1, "sepal_width": 3.5,
            "petal_length": 1.4, "petal_width": 0.2,
        })
        print(pred)  # {"prediction": ["setosa"]}

asyncio.run(main())
```

---

## 🎥 完整流程演示

参见 **[DEMO.md](./DEMO.md)** — 从零开始走通全流程：注册 → 上传 Iris / Diabetes / Auto MPG → 训练 → 指标 → 队列 → 模型部署 → 在线预测。

**[demo/presentation.html](./demo/presentation.html)** — 🎞 21 页 Reveal.js 幻灯片，含架构图、ER 图、训练队列时序图、认证流程图等 Mermaid 图表。

---

## 📖 API 参考

所有接口前缀 `/api`，均返回 JSON。分页使用 `offset`/`limit`（默认 `0`/`20`）。

> 写操作 (`POST`/`DELETE`) 需要 `Authorization: Bearer <token>`。

### 1. 📂 数据管理 `/api/data`

| 端点 | 说明 |
|------|------|
| `GET /` | 列表 (`?offset=0&limit=20`) |
| `POST /upload` | 上传 CSV（multipart） |
| `GET /{id}` | 详情 |
| `GET /{id}/profile` | 数据画像（数值列 mean/std/min/max/histogram，文本列 top_values） |
| `GET /{id}/preview?rows=10` | 前 N 行预览 |
| `DELETE /{id}` | 删除 |

### 2. 🧪 实验训练 `/api/experiments`

| 端点 | 说明 |
|------|------|
| `GET /` | 列表 |
| `GET /ids` | 🆕 所有实验 ID+名称+状态（无分页，适合快速查找） |
| `POST /` | 创建 `{name, dataset_id, target_column, problem_type}` |
| `GET /{id}` | 详情 |
| `POST /{id}/run` | 轻量执行（仅记录参数） |
| `POST /{id}/run-sklearn` | **sklearn 真实训练**（RandomForest + MLflow） |
| `GET /{id}/mlflow-metrics` | 训练指标（accuracy / mse / r2） |
| `DELETE /{id}` | 删除 |
| `GET /compare?ids=...` | 多实验对比 |
| `POST /{id}/enqueue` | ⭐ 加入训练队列 |
| `GET /queue/status` | ⭐ 队列状态 |

**`status` 流转**: `pending → running → completed`（`failed`）

### 3. 🤖 模型管理 `/api/models`

| 端点 | 说明 |
|------|------|
| `GET /` | 列表 |
| `GET /ids` | 🆕 所有模型 ID+名称+版本+状态（无分页，适合快速查找） |
| `GET /{id}` | 详情 |
| `POST /register` | 注册 `{name, experiment_id}` |
| `POST /{id}/promote` | 版本晋升 (version +1) |
| `DELETE /{id}` | 删除 |
| `GET /{id}/download` | ⭐ 下载 pickle 模型文件 |

### 4. 🚀 部署推理 `/api/deployments`

| 端点 | 说明 |
|------|------|
| `GET /` | 列表 |
| `POST /` | 部署 `{model_version_id, replicas}` |
| `GET /{id}` | 详情 |
| `POST /{id}/stop` | 停止 |
| `DELETE /{id}` | 删除 |
| `POST /{id}/predict` | 🔮 **在线预测** `{feature: value, ...}` |

### 5. 📊 监控 `/api/monitoring`

| 端点 | 说明 |
|------|------|
| `GET /{id}/metrics?time_range=1h` | 请求量/延迟/错误率/吞吐 |
| `GET /{id}/drift` | z-score 漂移检测（阈值 2.0） |

### 6. 🔐 认证 `/api/auth`

| 端点 | 说明 |
|------|------|
| `POST /register` | 注册 `{username, email, password}` → token |
| `POST /login` | 登录 `{email, password}` → token |
| `GET /me` | 当前用户（需 Bearer token） |
| `GET /users` | 用户列表（需认证） |

### 7. ⚙️ 系统 `/api/system` + 健康检查

| 端点 | 说明 |
|------|------|
| `GET /api/system/status` | 实体计数 + 最近实验 + 运行中部署 |
| `GET /api/health` | `{"status": "ok"}` |

---

## 🗄 数据模型速查

> 完整 ER 图见 **[demo/diagrams/er-diagram.png](./demo/diagrams/er-diagram.png)**（7 表 5 关系）

### User
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | PK |
| username | str | 唯一 |
| email | str | 唯一，登录凭据 |
| hashed_password | str | bcrypt |
| role | str | `user` |

### Experiment
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | PK |
| name | str | 实验名称 |
| dataset_id | UUID | FK → datasets |
| target_column | str | 目标列 |
| problem_type | str | `classification` / `regression` |
| mlflow_run_id | str? | MLflow Run ID |
| metrics | JSON? | 指标 |
| status | str | `pending`/`running`/`completed`/`failed` |

### ModelVersion
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | PK |
| name | str | 模型名 |
| version | int | 版本号 |
| experiment_id | UUID? | 来源实验 |
| framework | str? | `sklearn` |

### Deployment
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | PK |
| model_version_id | UUID | FK |
| name | str | 部署名 |
| status | str | `deploying`/`running`/`stopped`/`failed` |
| endpoint_url | str? | 推理 URL |

---

## 🔧 环境变量

全部 `MLP_` 前缀：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MLP_DATABASE_URL` | `sqlite+aiosqlite:///./mlp.db` | PostgreSQL: `postgresql+asyncpg://...` |
| `MLP_MLFLOW_TRACKING_URI` | `sqlite:///./mlflow.db` | MLflow Server: `http://localhost:5000` |
| `MLP_MINIO_ENDPOINT` | `localhost:9000` | S3 对象存储 |
| `MLP_MINIO_ACCESS_KEY` | `minioadmin` | |
| `MLP_MINIO_SECRET_KEY` | `minioadmin` | |
| `MLP_MINIO_BUCKET` | `ml-platform` | |
| `MLP_TEMPORAL_HOST` | `localhost:7233` | 工作流引擎 |
| `MLP_CLICKHOUSE_URL` | `http://localhost:8123` | 指标存储 |
| `MLP_JWT_SECRET` | `change-me-...` | ⚠️ 生产必须改 |
| `MLP_DEBUG` | `false` | SQL echo |
| `MLP_SERVER` | `http://localhost:8000` | CLI 专用：目标 API 地址 |

---

## 📁 项目结构

```
├── backend/
│   ├── main.py              # FastAPI 入口 + lifespan
│   ├── api/                 # 路由层（7 模块）
│   ├── services/            # 业务逻辑（8 服务）
│   ├── models_db/           # SQLAlchemy ORM（6 模型）
│   ├── core/                # 配置 / DI / 认证 / 中间件
│   └── tests/               # 60 个测试
├── sdk/ml_platform/         # Python SDK（8 模块）
├── cli/ml_platform_cli/     # 🖥 命令行工具（30+ 命令）
├── demo/
│   ├── presentation.html    # 🎞 Reveal.js 演示 PPT
│   └── diagrams/            # Mermaid 源文件 + PNG 图表
├── DEMO.md                  # 🎥 完整演示流程
├── docker-compose.yml       # 生产基础设施
└── pyproject.toml
```

---

## 🧩 前端集成

后端已配置 CORS `allow_origins=["*"]`。JWT token 存入 `localStorage`，请求时携带：

```typescript
const token = localStorage.getItem("token");
fetch(`${API_BASE}${path}`, {
  headers: {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  },
});
```

### 建议页面

| 路由 | 功能 | 核心 API |
|------|------|---------|
| `/login` | 登录/注册 | `POST /api/auth/login` |
| `/data` | 数据集管理 | `GET/POST /api/data` |
| `/experiments` | 实验列表+创建+训练 | `GET/POST /api/experiments` |
| `/experiments/:id` | 指标面板 | `GET /api/experiments/:id` |
| `/queue` | 训练队列监控 | `GET /api/experiments/queue/status` |
| `/models` | 模型注册+版本 | `GET/POST /api/models` |
| `/deployments` | 部署+在线预测 | `GET/POST /api/deployments` |
| `/monitoring` | 监控面板 | `GET /api/monitoring` |
| `/status` | 系统总览 | `GET /api/system/status` |


---

<p align="center">
  <sub>Built with ❤️ using FastAPI · SQLAlchemy · MLflow · sklearn · typer · rich</sub>
</p>
