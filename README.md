# ML Platform

面向数据分析师的 MLOps 平台。覆盖 **数据接入 → 实验训练 → 模型注册 → 模型部署 → 推理监控** 完整生命周期。

## 架构

```
前端 / SDK  →  REST API (FastAPI :8000)  →  Temporal 工作流
                  │          │                 │
             PostgreSQL   MinIO/S3         MLflow / Ray Serve
                  │
             ClickHouse  ←  Prometheus  ←  API 指标
```

后端端口 `:8000`，Swagger 文档在 `http://localhost:8000/docs`。

---

## 快速开始

```bash
# 安装
uv sync
cd sdk && uv sync && cd ..

# 启动（本地开发，无需 Docker）
uv run uvicorn backend.main:app --reload

# 端到端演示（自动创建临时数据库）
uv run python demo_full_pipeline.py
```

服务启动后访问 `http://localhost:8000/docs` 查看交互式 API 文档。

---

## API 参考

所有接口前缀 `/api`，均返回 JSON。分页使用 `offset`/`limit` 参数（默认 `0`/`20`）。

### 1. 数据管理 `/api/data`

#### `GET /` — 列表
```
GET /api/data/?offset=0&limit=20
```
**响应**: 数组
```json
[{
  "id": "uuid",
  "name": "iris.csv",
  "description": null,
  "file_path": "/tmp/ml-platform/uploads/xxx_iris.csv",
  "file_type": "csv",
  "row_count": 150,
  "column_count": 5,
  "size_bytes": 4550,
  "version": 1,
  "created_at": "2026-06-22T14:00:00",
  "updated_at": "2026-06-22T14:00:00"
}]
```

#### `POST /upload` — 上传 CSV
```
Content-Type: multipart/form-data
file: <CSV 文件>
```
**响应**: 单个 Dataset 对象（同上），含自动生成的 `profile`（JSON 字符串）。

#### `GET /{dataset_id}` — 详情
**响应**: Dataset 对象。404 → `{"detail": "Dataset not found"}`

#### `GET /{dataset_id}/profile` — 数据画像
**响应**:
```json
{
  "columns": [{
    "name": "sepal_length",
    "dtype": "float64",
    "null_count": 0,
    "null_ratio": 0.0,
    "unique_count": 35,
    "mean": 5.84,
    "std": 0.83,
    "min": 4.3,
    "max": 7.9,
    "histogram": [{"bin": "4.3-4.7", "count": 5}, ...]
  }, {
    "name": "species",
    "dtype": "object",
    "null_count": 0,
    "null_ratio": 0.0,
    "unique_count": 3,
    "top_values": [{"value": "setosa", "count": 50}, ...]
  }]
}
```

> **前端注意**: 数值列 (`int`/`float`) 返回 `mean|std|min|max|histogram`；文本列返回 `top_values`（前 20 个）。

---

### 2. 实验训练 `/api/experiments`

#### `GET /` — 列表
```
GET /api/experiments/?offset=0&limit=20
```
**响应**:
```json
[{
  "id": "uuid",
  "name": "iris-classifier",
  "dataset_id": "uuid",
  "mlflow_run_id": "abc123",
  "description": "鸢尾花分类",
  "target_column": "species",
  "problem_type": "classification",
  "metrics": null,
  "params": null,
  "status": "pending",
  "created_at": "...",
  "updated_at": "..."
}]
```

**`status` 取值**: `pending` | `running` | `completed` | `failed`

**`problem_type` 取值**: `classification` | `regression`

#### `POST /` — 创建实验
```json
{
  "name": "iris-classifier",           // 必填，不填自动生成
  "dataset_id": "uuid",                // 必填
  "target_column": "species",          // 必填，目标列名
  "problem_type": "classification",    // classification | regression
  "description": "可选的实验描述"       // 可选
}
```
**响应**: 创建的 Experiment 对象。

#### `GET /{experiment_id}` — 详情
**响应**: 单个 Experiment 对象。404 → `{"detail": "Experiment not found"}`

#### `POST /{experiment_id}/run` — 执行训练（轻量）
创建一个 MLflow run，仅记录参数 + accuracy=0.0（不做实际训练），状态变更为 `completed`。
**响应**:
```json
{
  "experiment_id": "uuid",
  "mlflow_run_id": "abc123",
  "status": "completed"
}
```

#### `POST /{experiment_id}/run-sklearn` — 执行训练（真实 sklearn）
加载数据集 CSV → LabelEncoder 编码 → 80/20 切分 → RandomForest 训练 → MLflow 记录指标和模型。

**响应**:
```json
{
  "experiment_id": "uuid",
  "mlflow_run_id": "abc123",
  "status": "completed"
}
```

> **注意**: 这个接口会实实在在地跑 sklearn 训练，耗时取决于数据集大小。训练后模型自动存入 MLflow 本地存储，可用于后续部署。

#### `GET /{experiment_id}/mlflow-metrics` — 查看训练结果
**响应**:
```json
{
  "metrics": [
    {"key": "accuracy", "value": 0.9667},
    {"key": "mse", "value": 0.12},
    {"key": "r2", "value": 0.85}
  ],
  "params": [
    {"key": "problem_type", "value": "classification"},
    {"key": "target_column", "value": "species"},
    {"key": "rows", "value": "150"}
  ]
}
```

> **分类**返回 `accuracy`；**回归**返回 `mse` + `r2`。

---

### 3. 模型管理 `/api/models`

#### `GET /` — 列表
```
GET /api/models/?offset=0&limit=20
```
**响应**:
```json
[{
  "id": "uuid",
  "name": "iris-v1",
  "version": 1,
  "experiment_id": "uuid",
  "mlflow_model_uri": "abc123",
  "framework": "sklearn",
  "metrics": null,
  "artifact_path": null,
  "status": "registered",
  "created_at": "...",
  "updated_at": "..."
}]
```

**`status` 取值**: `registered`

#### `GET /{model_id}` — 详情
**响应**: 单个 ModelVersion 对象。

#### `POST /register` — 注册模型（从实验）
```json
{
  "name": "iris-v1",
  "experiment_id": "uuid"
}
```
**响应**: 创建的 ModelVersion 对象（version=1, framework="sklearn"）。

#### `POST /{model_id}/promote` — 版本晋升
复制当前模型记录，`version + 1`，返回新版本对象。
```json
// 响应 (新版本)
{ "id": "uuid", "name": "iris-v1", "version": 2, "status": "registered" }
```

---

### 4. 在线推理 `/api/deployments`

#### `GET /` — 列表
```
GET /api/deployments/?offset=0&limit=20
```
**响应**:
```json
[{
  "id": "uuid",
  "model_version_id": "uuid",
  "name": "deploy-iris-v1-v1",
  "status": "running",
  "ray_serve_app": "deploy-iris-v1-v1",
  "endpoint_url": "http://localhost:8000/api/deployments/uuid/predict",
  "replicas": 1,
  "traffic_percent": 100,
  "created_at": "...",
  "updated_at": "..."
}]
```

**`status` 取值**: `deploying` | `running` | `stopped` | `failed`

#### `POST /` — 部署模型
```json
{
  "model_version_id": "uuid",
  "replicas": 1              // 可选，默认 1
}
```
模型从 MLflow 加载到内存（本地推理），不依赖外部服务。

**响应**:
```json
{
  "id": "uuid",
  "name": "deploy-iris-v1-v1",
  "model_version_id": "uuid",
  "status": "running",
  "endpoint_url": "http://localhost:8000/api/deployments/uuid/predict",
  "replicas": 1
}
```

#### `GET /{deployment_id}` — 详情
**响应**: 单个 Deployment 对象。

#### `POST /{deployment_id}/stop` — 停止部署
从内存卸载模型，`status` 变为 `stopped`。
**响应**:
```json
{ "id": "uuid", "status": "stopped" }
```

#### `POST /{deployment_id}/predict` — 推理
**请求**:
```json
{
  "sepal_length": 5.1,
  "sepal_width": 3.5,
  "petal_length": 1.4,
  "petal_width": 0.2
}
```

**成功响应**:
```json
{ "prediction": ["setosa"] }
```

**失败响应**:
```json
{ "error": "Deployment is not running" }
// 或
{ "error": "具体错误信息" }
```

> **前端注意**: 推理请求的特征键名必须与训练时的列名一致（区分大小写），否则会返回特征不匹配错误。

---

### 5. 监控告警 `/api/monitoring`

#### `GET /{deployment_id}/metrics` — 部署指标
```
GET /api/monitoring/{deployment_id}/metrics?time_range=1h
```

**`time_range` 取值**: `5m` | `15m` | `1h` | `6h` | `24h` | `7d`

**响应**:
```json
{
  "deployment_id": "uuid",
  "time_range": "1h",
  "metrics": {
    "request_count": 42,
    "avg_latency_ms": 12.5,
    "p95_latency_ms": 25.0,
    "error_rate": 0.0238,
    "throughput_rps": 0.01
  }
}
```

#### `GET /{deployment_id}/drift` — 数据漂移检测
```
GET /api/monitoring/{deployment_id}/drift
```

> 基于最近 200 条推理日志，对数值特征做 z-score 检测（阈值 2.0）。需要 ≥50 条日志才能检测。

**响应**:
```json
{
  "deployment_id": "uuid",
  "drift_detected": true,
  "drift_score": 2.56,
  "feature_drifts": [
    {"feature": "sepal_length", "z_score": 2.56, "drifted": true}
  ]
}
// 数据不足时:
{
  "deployment_id": "uuid",
  "drift_detected": false,
  "drift_score": 0.0,
  "feature_drifts": [],
  "message": "Not enough data for drift detection (need 50+ samples)"
}
```

---

### 6. 用户认证 `/api/auth`

所有密码使用 bcrypt 哈希存储，Token 使用 JWT (HS256) 签发，默认有效期 1440 分钟（24 小时）。需要在 `Authorization` 头中携带 `Bearer <token>`。

#### `POST /register` — 注册
```json
{
  "username": "alice",       // 必填，全局唯一
  "email": "alice@test.com", // 必填，全局唯一
  "password": "secret123"    // 必填，至少 6 位
}
```
**成功响应** (200):
```json
{
  "id": "uuid",
  "username": "alice",
  "email": "alice@test.com",
  "role": "user",
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```
> 注册成功即返回 token，无需再登录。

**错误响应**:
- 409 — `{"detail": "Email already registered"}`
- 409 — `{"detail": "Username already taken"}`
- 422 — `{"detail": "Password must be at least 6 characters"}`

#### `POST /login` — 登录
```json
{
  "email": "alice@test.com",
  "password": "secret123"
}
```
**成功响应** (200): 同注册返回（id, username, email, role, access_token, token_type）

**错误响应**:
- 401 — `{"detail": "Invalid email or password"}`

#### `GET /me` — 当前用户
```
Authorization: Bearer <token>
```
**成功响应** (200):
```json
{
  "id": "uuid",
  "username": "alice",
  "email": "alice@test.com",
  "role": "user",
  "created_at": "2026-06-22T14:00:00"
}
```
**错误响应**: 401 — Token 无效或过期

#### `GET /users` — 用户列表（需认证）
```
GET /api/auth/users?offset=0&limit=50
Authorization: Bearer <token>
```
**响应**: 数组，元素同 `/me` 格式。

---

### 7. 训练任务队列

当有多个模型训练任务需要执行时，可通过队列接口排队执行。队列采用 **FIFO**（先进先出）策略，后台 worker 逐个处理，一次只运行一个任务。

队列集成在 `/api/experiments` 路由下：

#### `POST /api/experiments/{id}/enqueue` — 加入队列
将已创建的实验加入训练队列。无需请求体。

**成功响应** (200):
```json
{
  "experiment_id": "uuid",
  "position": 1,
  "status": "queued"
}
```
**错误响应**: 404 — 实验不存在

#### `GET /api/experiments/queue/status` — 查看队列
```
GET /api/experiments/queue/status
```
**响应**:
```json
{
  "total": 5,
  "pending": 2,
  "running": {
    "experiment_id": "uuid",
    "experiment_name": "iris-classifier",
    "position": 1,
    "status": "running",
    "added_at": "2026-06-22T14:00:00",
    "error": null
  },
  "completed": 2,
  "failed": 1,
  "jobs": [
    {"experiment_id": "uuid", "experiment_name": "iris-classifier", "position": 1, "status": "running", "added_at": "...", "error": null},
    {"experiment_id": "uuid", "experiment_name": "regression-test", "position": 2, "status": "queued", "added_at": "...", "error": null},
    {"experiment_id": "uuid", "experiment_name": "batch-1", "position": 3, "status": "completed", "added_at": "...", "error": null},
    {"experiment_id": "uuid", "experiment_name": "batch-2", "position": 4, "status": "failed", "added_at": "...", "error": "..."},
    {"experiment_id": "uuid", "experiment_name": "batch-3", "position": 5, "status": "completed", "added_at": "...", "error": null}
  ]
}
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| total | int | 累计任务总数 |
| pending | int | 等待中的数量 |
| running | object\|null | 当前正在运行的任务（无则为 null） |
| completed | int | 已完成数量 |
| failed | int | 失败数量 |
| jobs | array | 全部任务列表（按入队顺序） |

**`status` 流转**:
```
queued → running → completed
              ↘ failed
```

> **注意**: worker 是应用进程内的后台 asyncio 任务，服务器重启后队列会丢失。

---

### 8. 系统状态 `/api/system`

#### `GET /status` — 全局概览
```
GET /api/system/status
```
**响应**:
```json
{
  "server": "ok",
  "counts": {
    "datasets": 12,
    "experiments": 8,
    "models": 5,
    "deployments": 3,
    "running_deployments": 2
  },
  "recent_experiments": [
    {"id": "uuid", "name": "iris-v2", "status": "completed", "created_at": "..."}
  ],
  "running_deployments_list": [
    {"id": "uuid", "name": "dep-iris-v1", "endpoint_url": "http://..."}
  ]
}
```

---

### 9. 健康检查

#### `GET /api/health`
```json
{ "status": "ok" }
```

---

## 完整流程示例

### 基础流程：数据 → 训练 → 部署 → 预测

```bash
# 1. 上传数据
curl -F "file=@iris.csv" http://localhost:8000/api/data/upload
# → {"id": "ds-xxx", "name": "iris.csv", "row_count": 150, ...}

# 2. 创建实验
curl -X POST http://localhost:8000/api/experiments/ \
  -H "Content-Type: application/json" \
  -d '{"name":"my-exp","dataset_id":"ds-xxx","target_column":"species","problem_type":"classification"}'
# → {"id": "exp-xxx", "status": "pending", ...}

# 3. 训练
curl -X POST http://localhost:8000/api/experiments/exp-xxx/run-sklearn
# → {"status": "completed", "mlflow_run_id": "abc123"}

# 4. 查看指标
curl http://localhost:8000/api/experiments/exp-xxx/mlflow-metrics
# → {"metrics": [{"key":"accuracy","value":0.97}], "params": [...]}

# 5. 注册模型
curl -X POST http://localhost:8000/api/models/register \
  -H "Content-Type: application/json" \
  -d '{"name":"my-model","experiment_id":"exp-xxx"}'
# → {"id": "model-xxx", "name": "my-model", "version": 1, ...}

# 6. 部署
curl -X POST http://localhost:8000/api/deployments/ \
  -H "Content-Type: application/json" \
  -d '{"model_version_id":"model-xxx","replicas":1}'
# → {"id": "dep-xxx", "status": "running", ...}

# 7. 预测
curl -X POST http://localhost:8000/api/deployments/dep-xxx/predict \
  -H "Content-Type: application/json" \
  -d '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0.2}'
# → {"prediction": ["setosa"]}

# 8. 查看监控
curl http://localhost:8000/api/monitoring/dep-xxx/metrics?time_range=24h
# → {"metrics": {"request_count": 1, "avg_latency_ms": 5.2, ...}}

# 9. 停止部署
curl -X POST http://localhost:8000/api/deployments/dep-xxx/stop
# → {"id": "dep-xxx", "status": "stopped"}
```

### 用户认证流程

```bash
# 注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@test.com","password":"secret123"}'
# → {"id": "user-xxx", "username": "alice", "access_token": "eyJ...", ...}

# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@test.com","password":"secret123"}'
# → {"id": "user-xxx", "username": "alice", "access_token": "eyJ...", ...}

# 查看当前用户
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJ..."
# → {"id": "user-xxx", "username": "alice", "email": "alice@test.com", "role": "user", ...}
```

### 批量训练队列流程

```bash
# 创建 3 个实验并加入队列
for name in batch-1 batch-2 batch-3; do
  # 创建实验 (假设已有 dataset_id)
  EXP_ID=$(curl -s -X POST http://localhost:8000/api/experiments/ \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$name\",\"dataset_id\":\"ds-xxx\",\"target_column\":\"target\",\"problem_type\":\"classification\"}" \
    | jq -r '.id')
  # 加入队列
  curl -X POST "http://localhost:8000/api/experiments/$EXP_ID/enqueue"
done

# 查看队列状态
curl http://localhost:8000/api/experiments/queue/status | jq .
# → {"total":3, "pending":2, "running":{...}, "completed":0, "failed":0, "jobs":[...]}

# 等待全部完成（轮询直到 pending==0）
curl http://localhost:8000/api/experiments/queue/status | jq '.pending'
```

---

## Python SDK

```python
import asyncio
from ml_platform import Client

async def main():
    async with Client("http://localhost:8000") as client:
        # 注册 & 登录
        user = await client.auth.register("alice", "alice@test.com", "secret123")
        # 后续请求自动携带 token
        client.set_token(user["access_token"])

        # 上传 → 训练 → 注册 → 部署 → 预测
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

        # 系统状态
        status = await client.system.status()
        print(status)

asyncio.run(main())
```

---

## 数据模型速查

### User
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | str | 用户名（唯一） |
| email | str | 邮箱（唯一，用于登录） |
| hashed_password | str | bcrypt 哈希密码 |
| role | str | user（默认） |
| created_at | datetime | |
| updated_at | datetime | |

### Dataset
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | str | 文件名 |
| file_path | str | 服务器存储路径 |
| file_type | str | 扩展名 (csv) |
| row_count | int\|null | 行数 |
| column_count | int\|null | 列数 |
| size_bytes | int\|null | 文件大小 |
| profile | JSON str\|null | 画像 |
| version | int | 版本号 |
| created_at | datetime | |
| updated_at | datetime | |

### Experiment
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | |
| name | str | 实验名称 |
| dataset_id | UUID\|null | 关联数据集 |
| mlflow_run_id | str\|null | MLflow Run ID |
| description | str\|null | 描述 |
| target_column | str | 目标列 |
| problem_type | str | classification\|regression |
| metrics | JSON str\|null | 指标 |
| params | JSON str\|null | 超参数 |
| status | str | pending\|running\|completed\|failed |

### ModelVersion
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | |
| name | str | 模型名 |
| version | int | 版本号 |
| experiment_id | UUID\|null | 来源实验 |
| mlflow_model_uri | str\|null | MLflow Run ID |
| framework | str\|null | sklearn |
| status | str | registered |

### Deployment
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | |
| model_version_id | UUID | 关联模型版本 |
| name | str | 部署名 |
| status | str | deploying\|running\|stopped\|failed |
| endpoint_url | str\|null | 推理 URL |
| replicas | int | 副本数 |

### Deployment 状态机
```
deploying ──→ running ──→ stopped
```

---

## 环境变量

全部 `MLP_` 前缀，定义在 `backend/core/config.py`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MLP_DATABASE_URL` | `postgresql+asyncpg://mlp:mlp@localhost:5432/mlp` | 也支持 sqlite+aiosqlite |
| `MLP_MLFLOW_TRACKING_URI` | `http://localhost:5000` | 也支持 sqlite:///path/to/mlflow.db |
| `MLP_MINIO_ENDPOINT` | `localhost:9000` | |
| `MLP_MINIO_ACCESS_KEY` | `minioadmin` | |
| `MLP_MINIO_SECRET_KEY` | `minioadmin` | |
| `MLP_MINIO_BUCKET` | `ml-platform` | |
| `MLP_TEMPORAL_HOST` | `localhost:7233` | |
| `MLP_CLICKHOUSE_URL` | `http://localhost:8123` | |
| `MLP_RAY_ADDRESS` | `auto` | |
| `MLP_DEBUG` | `false` | 开启 SQL echo |

---

## 项目结构

```
├── backend/
│   ├── main.py              # FastAPI 入口，路由注册 + lifespan
│   ├── api/                 # 路由层
│   │   ├── data.py                  # 数据管理
│   │   ├── experiments.py           # 实验训练 + 队列
│   │   ├── models.py                # 模型管理
│   │   ├── deployments.py           # 在线推理
│   │   ├── monitoring.py            # 监控告警
│   │   ├── auth.py                  # 用户认证
│   │   └── system.py                # 系统状态
│   ├── services/            # 业务逻辑层
│   │   ├── data_service.py          # 数据上传 + pandas 画像
│   │   ├── training_service.py      # 实验 CRUD + sklearn 训练
│   │   ├── model_service.py         # 模型注册 + 版本晋升
│   │   ├── deployment_service.py    # 部署生命周期
│   │   ├── monitoring_service.py    # 指标聚合 + 漂移检测
│   │   ├── local_serving.py         # 本地内存模型推理
│   │   ├── training_queue.py        # FIFO 训练任务队列
│   │   └── ray_serve_manager.py     # Ray Serve 备选方案
│   ├── models_db/           # SQLAlchemy ORM (Dataset, Experiment, ModelVersion, Deployment, InferenceLog, User)
│   ├── core/                # 配置 (config.py)、依赖注入 (dependencies.py)、认证 (auth.py)、中间件 (middleware.py)
│   ├── workflows/           # Temporal 工作流
│   └── tests/               # 50 个测试 (含 auth + queue + e2e)
├── sdk/ml_platform/         # Python SDK (client, data, experiments, models, deployments, monitoring, auth, system)
├── infra/                   # Prometheus 配置
├── demo_full_pipeline.py    # 全流程演示脚本
├── docker-compose.yml       # 基础设施服务
└── pyproject.toml
```

---

## 前端集成指南

### CORS
后端已配置 `allow_origins=["*"]`，开发环境无需额外处理。

### 基础 URL
默认 `http://localhost:8000`，通过环境变量 `NEXT_PUBLIC_API_URL` 配置。

### 请求模式（以 React/TypeScript 为例）

```typescript
const API_BASE = "http://localhost:8000";

// 通用 fetch 封装
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
```

### 页面建议

| 路由 | 功能 | 核心 API |
|------|------|---------|
| `/login` | 登录 / 注册 | `POST /api/auth/login`, `/register` |
| `/data` | 数据集上传 + 列表 + 画像 | `GET/POST /api/data` |
| `/experiments` | 实验列表 + 创建 + 运行 + 指标 | `GET/POST /api/experiments` |
| `/experiments/:id` | 实验详情 + MLflow 指标面板 | `GET /api/experiments/:id` |
| `/queue` | 训练队列监控面板 | `GET /api/experiments/queue/status` |
| `/models` | 模型注册 + 版本列表 | `GET/POST /api/models` |
| `/deployments` | 部署列表 + 部署/停止 + 在线预测 | `GET/POST /api/deployments` |
| `/monitoring` | 监控面板 + 漂移检测 | `GET /api/monitoring` |
| `/status` | 系统状态总览 | `GET /api/system/status` |

### 认证集成

所有需要鉴权的接口在请求头中携带 JWT token：

```typescript
// 登录成功后存储 token
const { access_token } = await apiFetch("/api/auth/login", {
  method: "POST",
  body: JSON.stringify({ email, password }),
});
localStorage.setItem("token", access_token);

// 后续请求统一添加
function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("token");
  return fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
    ...options,
  }).then(async (res) => {
    if (!res.ok) {
      if (res.status === 401 && window.location.pathname !== "/login") {
        localStorage.removeItem("token");
        window.location.href = "/login";
      }
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  });
}
```

### 典型页面数据流

**实验列表页**:
```
1. GET /api/experiments/ → 渲染表格
2. POST /api/experiments/ → 创建新实验
3. POST /api/experiments/:id/run-sklearn → 执行训练（可能需要 loading 状态）
4. GET /api/experiments/:id/mlflow-metrics → 展示训练结果（轮询直到 completed）
```

**在线推理页**:
```
1. GET /api/deployments/ → 部署列表
2. POST /api/deployments/ → 部署模型
3. 输入特征 → POST /api/deployments/:id/predict → 展示预测结果
4. GET /api/monitoring/:id/metrics → 展示请求量/延迟/错误率图表
```
