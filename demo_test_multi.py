#!/usr/bin/env python3
"""多场景推理测试 —— 同一个部署模型上跑多种输入。"""

from __future__ import annotations

import asyncio
import io
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    tmpdir = tempfile.mkdtemp(prefix="ml_test_")
    os.environ["MLP_DATABASE_URL"] = f"sqlite+aiosqlite:///{tmpdir}/mlp.db"
    os.environ["MLP_MLFLOW_TRACKING_URI"] = f"sqlite:///{tmpdir}/mlflow.db"

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from backend.api.data import router as data_router
    from backend.api.deployments import router as deployment_router
    from backend.api.experiments import router as experiment_router
    from backend.api.models import router as model_router
    from backend.api.monitoring import router as monitoring_router
    from backend.core.dependencies import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from backend.models_db.base import Base
    from httpx import ASGITransport, AsyncClient

    engine = create_async_engine(os.environ["MLP_DATABASE_URL"], echo=False)
    demo_session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = FastAPI(title="Test")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(data_router, prefix="/api/data")
    app.include_router(experiment_router, prefix="/api/experiments")
    app.include_router(model_router, prefix="/api/models")
    app.include_router(deployment_router, prefix="/api/deployments")
    app.include_router(monitoring_router, prefix="/api/monitoring")

    async def override_get_db():
        async with demo_session() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    try:
        # ====== 训练和部署 ======
        print("=" * 60)
        print("训练鸢尾花分类模型 + 部署")
        print("=" * 60)

        csv_data = (
            b"sl,sw,pl,pw,species\n"
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
        resp = await client.post("/api/data/upload", files={"file": ("iris.csv", io.BytesIO(csv_data), "text/csv")})
        ds_id = resp.json()["id"]

        resp = await client.post("/api/experiments/", json={
            "name": "iris", "dataset_id": ds_id, "target_column": "species", "problem_type": "classification",
        })
        exp_id = resp.json()["id"]

        resp = await client.post(f"/api/experiments/{exp_id}/run-sklearn")
        print(f"训练: {resp.json()['status']}")

        resp = await client.post("/api/models/register", json={"name": "iris-v1", "experiment_id": exp_id})
        model = resp.json()
        print(f"注册: {model['name']} v{model['version']}")

        resp = await client.post("/api/deployments/", json={"model_version_id": model["id"]})
        dep = resp.json()
        dep_id = dep["id"]
        print(f"部署: {dep['status']}\n")

        # ====== 多场景测试 ======
        print("=" * 60)
        print("场景 1: 典型 setosa（花萼短、花瓣短）")
        print("=" * 60)
        cases = [
            ("典型 setosa",   {"sl": 5.1, "sw": 3.5, "pl": 1.4, "pw": 0.2}, "setosa"),
            ("典型 setosa 2", {"sl": 4.8, "sw": 3.0, "pl": 1.4, "pw": 0.1}, "setosa"),
            ("边缘 setosa",   {"sl": 5.5, "sw": 3.8, "pl": 1.8, "pw": 0.4}, "setosa"),
            ("典型 versicolor",  {"sl": 6.5, "sw": 2.8, "pl": 4.6, "pw": 1.5}, "versicolor"),
            ("典型 versicolor 2",{"sl": 5.9, "sw": 3.0, "pl": 4.2, "pw": 1.5}, "versicolor"),
            ("边缘 versicolor",  {"sl": 6.2, "sw": 2.5, "pl": 4.0, "pw": 1.3}, "versicolor"),
            ("典型 virginica",   {"sl": 6.8, "sw": 3.0, "pl": 5.9, "pw": 2.1}, "virginica"),
            ("典型 virginica 2", {"sl": 6.3, "sw": 3.3, "pl": 6.0, "pw": 2.5}, "virginica"),
            ("边缘 virginica",   {"sl": 6.5, "sw": 3.0, "pl": 5.5, "pw": 1.8}, "virginica"),
        ]

        results = []
        for label, features, expected in cases:
            resp = await client.post(f"/api/deployments/{dep_id}/predict", json=features)
            pred = resp.json().get("prediction", ["error"])[0]
            ok = "✅" if pred == expected else "❌"
            results.append(ok == "✅")
            print(f"  {ok} {label:20s} → {pred:12s} (期望: {expected})")

        correct = sum(results)
        print(f"\n  {correct}/{len(results)} 正确")

        # ====== 场景 2: 批量推理 ======
        print("\n" + "=" * 60)
        print("场景 2: 批量推理（同模型连续调用）")
        print("=" * 60)
        batch = [
            {"sl": 5.0, "sw": 3.4, "pl": 1.5, "pw": 0.2},
            {"sl": 6.7, "sw": 3.0, "pl": 5.0, "pw": 1.7},
            {"sl": 5.8, "sw": 2.7, "pl": 4.1, "pw": 1.0},
            {"sl": 7.2, "sw": 3.2, "pl": 6.0, "pw": 1.8},
            {"sl": 4.6, "sw": 3.2, "pl": 1.4, "pw": 0.2},
        ]
        tasks = [client.post(f"/api/deployments/{dep_id}/predict", json=f) for f in batch]
        responses = await asyncio.gather(*tasks)
        for i, (feat, r) in enumerate(zip(batch, responses)):
            print(f"  样本{i+1}: {feat['sl']},{feat['sw']},{feat['pl']},{feat['pw']} → {r.json()['prediction'][0]}")

        # ====== 场景 3: 未知特征值 ======
        print("\n" + "=" * 60)
        print("场景 3: 极端/异常输入")
        print("=" * 60)
        edge_cases = [
            ("全零",         {"sl": 0, "sw": 0, "pl": 0, "pw": 0}),
            ("超大值",        {"sl": 99, "sw": 99, "pl": 99, "pw": 99}),
            ("缺失键",        {"sl": 5.0, "sw": 3.0}),  # missing pl, pw
        ]
        for label, features in edge_cases:
            try:
                resp = await client.post(f"/api/deployments/{dep_id}/predict", json=features)
                result = resp.json()
                if "prediction" in result:
                    print(f"  ⚠️  {label}: {result['prediction']} (模型仍给出结果)")
                else:
                    print(f"  ❌ {label}: {result}")
            except Exception as e:
                print(f"  ❌ {label}: {e}")

        # ====== 场景 4: 部署状态检查 ======
        print("\n" + "=" * 60)
        print("场景 4: 部署生命周期")
        print("=" * 60)
        resp = await client.get(f"/api/deployments/{dep_id}")
        dep_info = resp.json()
        print(f"  当前状态: {dep_info['status']}")
        print(f"  名称: {dep_info['name']}")
        print(f"  副本数: {dep_info['replicas']}")

        # 停止部署
        resp = await client.post(f"/api/deployments/{dep_id}/stop")
        print(f"  停止后: {resp.json()['status']}")

        # 停止后再预测
        resp = await client.post(f"/api/deployments/{dep_id}/predict", json={"sl": 5.0, "sw": 3.0, "pl": 1.5, "pw": 0.2})
        print(f"  停服后预测: {resp.json()}")

        print("\n" + "=" * 60)
        print("✅ 多场景测试完成")
        print("=" * 60)

    finally:
        await client.aclose()
        await engine.dispose()
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
