# ML Platform — 全流程演示

> 环境：WSL2 Ubuntu · Python 3.13 · SQLite（无需 Docker）
> 数据：Iris (分类 150 行) · Diabetes (回归 442 行) · Auto MPG (回归 398 行)

## 1. 启动后端

```bash
cd ~/projects/software_development
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

默认使用 SQLite + 本地 MLflow，无需 Docker 或环境变量。

## 2. 安装 CLI

```bash
cd cli && uv sync
uv tool install --from dist/ml_platform_cli-0.1.0-py3-none-any.whl \
  --with ../sdk/dist/ml_platform-0.1.0-py3-none-any.whl ml-platform-cli
```

## 3. 注册 / 登录

```bash
$ mlp auth login --register -u demo -e demo@mlp.test -p demo1234

✓ Registered as demo
  Server: http://localhost:8000
  Role:   user
```

Token 自动保存到 `~/.mlp/config.json`，后续命令自动携带。

## 4. 上传数据集

```bash
# Iris 分类数据集 (UCI)
$ mlp data upload /tmp/mlp_test_data/iris.csv
✓ Uploaded iris.csv
  ID:     10047bdc-563b-479a-97a1-ac18087eb785
  Rows:   150   Cols:   5   Size:   4609 bytes

# Diabetes 回归数据集 (sklearn)
$ mlp data upload /tmp/mlp_test_data/diabetes.csv
✓ Uploaded diabetes.csv
  ID:     1c34090b-bf14-47a2-9ca0-60ca0f28b754
  Rows:   442   Cols:   11  Size:   95137 bytes

# Auto MPG 回归数据集 (UCI)
$ mlp data upload /tmp/mlp_test_data/auto_mpg_raw.csv
✓ Uploaded auto_mpg_raw.csv
  ID:     887c13e5-1082-4431-a602-61afeeaa2ea5
  Rows:   398   Cols:   9   Size:   21582 bytes
```

### 查看列表

```bash
$ mlp data list
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ ID               ┃ Name             ┃ Rows ┃ Cols ┃ Size  ┃ Created          ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ 1c34090b-bf14-4… │ diabetes.csv     │ 442  │ 11   │ 95137 │ 2026-06-23T06:2… │
│ 887c13e5-1082-4… │ auto_mpg_raw.csv │ 398  │ 9    │ 21582 │ 2026-06-23T06:2… │
│ 10047bdc-563b-4… │ iris.csv         │ 150  │ 5    │ 4609  │ 2026-06-23T06:2… │
└──────────────────┴──────────────────┴──────┴──────┴───────┴──────────────────┘
```

> **注意**：rich 表格会截断 UUID。通过 SDK 或 `mlp data get <id>` 获取完整 ID。

## 5. 数据画像

```bash
$ mlp data profile 10047bdc-563b-479a-97a1-ac18087eb785

sepal_length (float64) — nulls: 0
  Mean: 5.8433  Std: 0.8281  Min: 4.3000  Max: 7.9000

sepal_width (float64) — nulls: 0
  Mean: 3.0540  Std: 0.4336  Min: 2.0000  Max: 4.4000

petal_length (float64) — nulls: 0
  Mean: 3.7587  Std: 1.7644  Min: 1.0000  Max: 6.9000

petal_width (float64) — nulls: 0
  Mean: 1.1987  Std: 0.7632  Min: 0.1000  Max: 2.5000

species (object) — nulls: 0
  Top: Iris-setosa: 50  Iris-versicolor: 50  Iris-virginica: 50
```

## 6. 创建实验并训练

```bash
# 分类实验
$ mlp experiments create --name iris-clf \
    -d 10047bdc-563b-479a-97a1-ac18087eb785 \
    -t species --type classification
✓ Created iris-clf

# 回归实验
$ mlp experiments create --name diabetes-reg \
    -d 1c34090b-bf14-47a2-9ca0-60ca0f28b754 \
    -t target --type regression
✓ Created diabetes-reg
```

### sklearn 训练

```bash
$ mlp experiments run-sklearn 7dab54ce-8491-4c7a-9b07-ee201e80b7b0
✓ completed
  MLflow Run: 7c8ae763d94b4950bb8db4bc61a29d3f
```

### 查看指标

```bash
$ mlp experiments metrics 7dab54ce-8491-4c7a-9b07-ee201e80b7b0
       Metrics
┏━━━━━━━━━━┳━━━━━━━━┓
┃ Metric   ┃ Value  ┃
┡━━━━━━━━━━╇━━━━━━━━┩
│ accuracy │ 0.7667 │
└──────────┴────────┘
            Parameters
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Param         ┃ Value          ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ problem_type  │ classification │
│ target_column │ species        │
│ rows          │ 150            │
└───────────────┴────────────────┘
```

```bash
$ mlp experiments metrics 8c859628-c9a1-478b-bcd7-50966e05e99d
       Metrics
┏━━━━━━━━┳━━━━━━━━━━━┓
┃ Metric ┃ Value     ┃
┡━━━━━━━━╇━━━━━━━━━━━┩
│ mse    │ 3713.7268 │
│ r2     │ 0.4217    │
└────────┴───────────┘
```

## 7. 训练队列

```bash
# 入队
$ mlp experiments enqueue 16d46630-6679-48b2-9f75-ade2aaffc032
✓ Enqueued mpg-reg — position 1

# 查看队列
$ mlp queue status
             Training Queue
┏━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┓
┃ Pos ┃ Experiment ┃ Status    ┃ Error ┃
┡━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━┩
│ 1   │ mpg-reg    │ completed │       │
└─────┴────────────┴───────────┴───────┘
   total: 1  completed: 1  running: -
         pending: 0  failed: 0
```

FIFO 顺序执行，后台 worker 自动处理。状态流转：`queued → running → completed`（失败则 `failed`）。

## 8. 模型注册、部署、预测

```bash
# 注册模型
$ mlp models register --name iris-model -e 7dab54ce-8491-4c7a-9b07-ee201e80b7b0
✓ Registered iris-model v1

# 部署
$ mlp deployments create -m 35c1b274-99b8-4a08-8c36-d996c079b422
✓ Deployed deploy-iris-model-v1 — status: running
  Endpoint: http://localhost:8000/api/deployments/0f499c60.../predict

# 预测 Iris-virginica (大花)
$ mlp deployments predict 0f499c60-88d7-413e-8904-d734d6ed34a1 \
    -d '{"sepal_length":6.5,"sepal_width":3.0,"petal_length":5.8,"petal_width":2.2}'
✓ Prediction: ['Iris-virginica']

# 预测 Iris-setosa (小花)
$ mlp deployments predict 0f499c60-88d7-413e-8904-d734d6ed34a1 \
    -d '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0.2}'
✓ Prediction: ['Iris-setosa']
```

## 9. 系统总览

```bash
$ mlp status
Server: ok
  Datasets:    3
  Experiments: 3
  Models:      1
  Deployments: 1 (1 running)

                Recent Experiments
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Name         ┃ Status    ┃ Created             ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ mpg-reg      │ completed │ 2026-06-23 06:22:44 │
│ iris-clf     │ completed │ 2026-06-23 06:22:43 │
│ diabetes-reg │ completed │ 2026-06-23 06:22:43 │
└──────────────┴───────────┴─────────────────────┘

                              Running Deployments
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                 ┃ Endpoint                                              ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ deploy-iris-model-v1 │ http://localhost:8000/api/deployments/0f499c60...     │
└──────────────────────┴───────────────────────────────────────────────────────┘
```

## 10. 完整命令速查

```
mlp auth login/logout/whoami
mlp data upload/list/get/profile/preview/delete
mlp experiments list/get/create/run/run-sklearn/metrics/compare/delete/enqueue
mlp queue status/watch
mlp models list/get/register/promote/delete/download
mlp deployments list/get/create/stop/delete/predict
mlp monitor metrics/drift
mlp status/health
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MLP_DATABASE_URL` | `sqlite+aiosqlite:///./mlp.db` | 生产环境设 PostgreSQL |
| `MLP_MLFLOW_TRACKING_URI` | `sqlite:///./mlflow.db` | 生产环境设 MLflow Server |
| `MLP_JWT_SECRET` | `change-me-...` | 生产环境必须修改 |
