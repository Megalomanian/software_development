from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models_db.model import Deployment, ModelVersion
from backend.services.local_serving import LocalModelRegistry


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
            endpoint_url=f"http://localhost:8000/api/deployments/predict/{deployment_name}",
            status="deploying",
        )
        self.db.add(deployment)
        await self.db.flush()

        # Try local serving first — no external dependency
        mlflow_run_id = model.mlflow_model_uri or ""
        result = LocalModelRegistry.deploy(
            name=deployment_name,
            mlflow_run_id=mlflow_run_id,
            tracking_uri=settings.mlflow_tracking_uri,
        )

        if result["status"] == "running":
            deployment.status = "running"
            deployment.endpoint_url = f"http://localhost:8000/api/deployments/{deployment.id}/predict"
        else:
            # Local serving failed; try Ray Serve as fallback
            try:
                from backend.services.ray_serve_manager import RayServeManager

                mgr = RayServeManager()
                ray_result = mgr.deploy_model(
                    model_uri=model.mlflow_model_uri or model.artifact_path or "",
                    deployment_name=deployment_name,
                    num_replicas=deployment.replicas,
                )
                if ray_result["status"] == "running":
                    deployment.status = "running"
                    deployment.endpoint_url = ray_result.get("endpoint")
                else:
                    deployment.status = "failed"
            except Exception:
                deployment.status = "failed"

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

        # Stop local serving
        name = deployment.ray_serve_app or deployment.name
        LocalModelRegistry.stop(name)

        # Also try Ray Serve if it was used
        try:
            from backend.services.ray_serve_manager import RayServeManager

            RayServeManager().stop_deployment(name)
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

        name = deployment.ray_serve_app or deployment.name

        # Try local serving first
        if LocalModelRegistry.is_running(name):
            return LocalModelRegistry.predict(name, data)

        # Fall back to Ray Serve
        try:
            from backend.services.ray_serve_manager import RayServeManager

            return RayServeManager().predict(name, data)
        except Exception as e:
            return {"error": str(e)}
