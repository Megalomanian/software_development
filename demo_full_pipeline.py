#!/usr/bin/env python3
"""全流程模型训练演示脚本。

演示完整 MLOps 流程：
  数据上传 → 实验创建 → 模型训练（sklearn）→ 模型注册 → 部署 → 预测
无需外部服务，使用本地 SQLite + 本地 MLflow 文件存储。
"""

from __future__ import annotations

import asyncio
import io
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def main():
    # ---- 准备环境 ----
    tmpdir = tempfile.mkdtemp(prefix="ml_demo_")
    db_url = f"sqlite+aiosqlite:///{tmpdir}/mlp.db"
    os.environ["MLP_DATABASE_URL"] = db_url
    os.environ["MLP_MLFLOW_TRACKING_URI"] = f"sqlite:///{tmpdir}/mlflow.db"

    print("=" * 60)
    print("ML Platform — 全流程模型训练演示")
    print("=" * 60)

    # ---- 启动后端 (不带 Prometheus 避免 ASGI 兼容问题) ----
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from backend.api.data import router as data_router
    from backend.api.deployments import router as deployment_router
    from backend.api.experiments import router as experiment_router
    from backend.api.models import router as model_router
    from backend.api.monitoring import router as monitoring_router
    from backend.core.dependencies import get_db

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from backend.models_db.base import Base

    engine = create_async_engine(db_url, echo=False)
    demo_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = FastAPI(title="ML Platform Demo")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    app.include_router(data_router, prefix="/api/data")
    app.include_router(experiment_router, prefix="/api/experiments")
    app.include_router(model_router, prefix="/api/models")
    app.include_router(deployment_router, prefix="/api/deployments")
    app.include_router(monitoring_router, prefix="/api/monitoring")

    async def override_get_db():
        async with demo_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    try:
        # ============ 1. 数据上传 ============
        print("\n📊 步骤 1/6: 上传数据集")
        csv_data = (
            b"sepal_length,sepal_width,petal_length,petal_width,species\n"
            b"5.1,3.5,1.4,0.2,setosa\n"
            b"4.9,3.0,1.4,0.2,setosa\n"
            b"4.7,3.2,1.3,0.2,setosa\n"
            b"5.0,3.6,1.4,0.2,setosa\n"
            b"5.4,3.9,1.7,0.4,setosa\n"
            b"7.0,3.2,4.7,1.4,versicolor\n"
            b"6.4,3.2,4.5,1.5,versicolor\n"
            b"6.9,3.1,4.9,1.5,versicolor\n"
            b"5.5,2.3,4.0,1.3,versicolor\n"
            b"6.5,2.8,4.6,1.5,versicolor\n"
            b"6.3,3.3,6.0,2.5,virginica\n"
            b"5.8,2.7,5.1,1.9,virginica\n"
            b"7.1,3.0,5.9,2.1,virginica\n"
            b"6.3,2.9,5.6,1.8,virginica\n"
            b"6.5,3.0,5.8,2.2,virginica\n"
        )
        resp = await client.post(
            "/api/data/upload",
            files={"file": ("iris.csv", io.BytesIO(csv_data), "text/csv")},
        )
        dataset = resp.json()
        print(f"   数据集: {dataset['name']} | {dataset['row_count']} 行 x {dataset['column_count']} 列")
        print(f"   大小: {dataset['size_bytes']} bytes")

        # ---- 查看数据画像 ----
        resp = await client.get(f"/api/data/{dataset['id']}/profile")
        profile = resp.json()
        print(f"   列数: {len(profile['columns'])}")
        for col in profile["columns"][:3]:
            print(f"     - {col['name']} ({col['dtype']}): null={col['null_count']}, unique={col['unique_count']}")

        # ============ 2. 创建实验 ============
        print("\n🧪 步骤 2/6: 创建实验")
        resp = await client.post(
            "/api/experiments/",
            json={
                "name": "iris-species-classifier",
                "dataset_id": dataset["id"],
                "target_column": "species",
                "problem_type": "classification",
                "description": "鸢尾花品种分类 — RandomForest",
            },
        )
        experiment = resp.json()
        print(f"   实验: {experiment['name']}")
        print(f"   类型: {experiment['problem_type']} | 目标: {experiment['target_column']}")
        print(f"   状态: {experiment['status']}")

        # ============ 3. 模型训练 ============
        print("\n🏋️ 步骤 3/6: 训练模型 (sklearn RandomForest)")
        resp = await client.post(f"/api/experiments/{experiment['id']}/run-sklearn")
        result = resp.json()
        print(f"   状态: {result['status']}")
        print(f"   MLflow Run ID: {result['mlflow_run_id']}")

        # ---- 查看训练指标 ----
        resp = await client.get(f"/api/experiments/{experiment['id']}/mlflow-metrics")
        mlflow_data = resp.json()
        print("   训练指标:")
        for m in mlflow_data["metrics"]:
            print(f"     - {m['key']}: {m['value']:.4f}")
        print("   超参数:")
        for p in mlflow_data["params"]:
            print(f"     - {p['key']}: {p['value']}")

        # ============ 4. 注册模型 ============
        print("\n📦 步骤 4/6: 注册模型到模型中心")
        resp = await client.post(
            "/api/models/register",
            json={"name": "iris-classifier-v1", "experiment_id": experiment["id"]},
        )
        model = resp.json()
        print(f"   模型: {model['name']} v{model['version']}")
        print(f"   框架: {model['framework']} | 状态: {model['status']}")

        # ---- 版本晋升 ----
        resp = await client.post(f"/api/models/{model['id']}/promote")
        promoted = resp.json()
        print(f"   晋升: v{model['version']} → v{promoted['version']}")

        # ============ 5. 部署 ============
        print("\n🚀 步骤 5/6: 部署模型")
        resp = await client.post(
            "/api/deployments/",
            json={"model_version_id": model["id"], "replicas": 1},
        )
        deployment = resp.json()
        print(f"   部署: {deployment['name']}")
        print(f"   状态: {deployment['status']}")

        # ============ 6. 推理预测 ============
        print("\n🔮 步骤 6/6: 发送预测请求")
        sample_input = {
            "sepal_length": 5.1,
            "sepal_width": 3.5,
            "petal_length": 1.4,
            "petal_width": 0.2,
        }
        print(f"   输入: {sample_input}")
        resp = await client.post(
            f"/api/deployments/{deployment['id']}/predict",
            json=sample_input,
        )
        prediction = resp.json()
        print(f"   预测结果: {prediction}")

        # ---- 监控指标 ----
        print("\n📈 部署监控:")
        resp = await client.get(f"/api/monitoring/{deployment['id']}/metrics?time_range=1h")
        metrics = resp.json()
        m = metrics["metrics"]
        print(f"   请求数: {m['request_count']} | 平均延迟: {m['avg_latency_ms']}ms")
        print(f"   错误率: {m['error_rate']} | 吞吐: {m['throughput_rps']} req/s")

        print("\n" + "=" * 60)
        print("✅ 全流程完成!")
        print("=" * 60)
        print(f"\n流程总结:")
        print(f"  1. 上传数据: {dataset['name']} ({dataset['row_count']} 行)")
        print(f"  2. 创建实验: {experiment['name']}")
        acc = {m["key"]: m["value"] for m in mlflow_data["metrics"]}.get("accuracy", "N/A")
        print(f"  3. 训练完成: accuracy={acc}")
        print(f"  4. 模型注册: {model['name']} v{model['version']} → v{promoted['version']}")
        print(f"  5. 模型部署: {deployment['status']}")
        print(f"  6. 在线推理: {'✓' if deployment['status'] == 'running' else '部署未 running'}")

    finally:
        await client.aclose()
        await engine.dispose()
        # Cleanup temp files
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
