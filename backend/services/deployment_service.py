from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models_db.model import Deployment, ModelVersion


class DeploymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_deployments(self, offset: int, limit: int) -> list[Deployment]:
        result = await self.db.execute(
            select(Deployment)
            .order_by(Deployment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_deployment(self, data: dict) -> Deployment:
        model_id = data["model_version_id"]
        model_result = await self.db.execute(
            select(ModelVersion).where(ModelVersion.id == model_id)
        )
        model = model_result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail=f"Model version {model_id} not found")

        deployment_name = f"deploy-{model.name}-v{model.version}"

        deployment = Deployment(
            name=deployment_name,
            model_version_id=model_id,
            replicas=data.get("replicas", 1),
            ray_serve_app=deployment_name,
            endpoint_url=f"http://localhost:8000/{deployment_name}",
            status="deploying",
        )
        self.db.add(deployment)
        await self.db.commit()

        # Attempt Ray Serve deploy
        try:
            from backend.services.ray_serve_manager import RayServeManager

            mgr = RayServeManager()
            result = mgr.deploy_model(
                model_uri=model.mlflow_model_uri or model.artifact_path or "",
                deployment_name=deployment_name,
                num_replicas=deployment.replicas,
            )
            if result["status"] == "running":
                deployment.status = "running"
                deployment.endpoint_url = result.get("endpoint")
            else:
                deployment.status = "failed"
        except Exception:
            deployment.status = "failed_no_ray"

        await self.db.commit()
        return deployment

    async def get_deployment(self, deployment_id: str) -> Deployment | None:
        result = await self.db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        return result.scalar_one_or_none()

    async def stop_deployment(self, deployment_id: str) -> Deployment:
        deployment = await self.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        try:
            from backend.services.ray_serve_manager import RayServeManager

            mgr = RayServeManager()
            mgr.stop_deployment(deployment.ray_serve_app or deployment.name)
        except Exception:
            pass

        deployment.status = "stopped"
        await self.db.commit()
        return deployment

    async def predict(self, deployment_id: str, data: dict) -> dict:
        deployment = await self.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        if deployment.status != "running":
            return {"error": "Deployment is not running"}

        try:
            from backend.services.ray_serve_manager import RayServeManager

            mgr = RayServeManager()
            return mgr.predict(deployment.ray_serve_app or deployment.name, data)
        except Exception as e:
            return {"error": str(e)}
