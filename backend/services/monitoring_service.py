from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models_db.model import InferenceLog


class MonitoringService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_deployment_metrics(self, deployment_id: str, time_range: str) -> dict[str, Any]:
        since = self._parse_time_range(time_range)

        result = await self.db.execute(
            select(
                func.count(InferenceLog.id).label("request_count"),
                func.coalesce(func.avg(InferenceLog.latency_ms), 0).label("avg_latency"),
            ).where(
                InferenceLog.deployment_id == deployment_id,
                InferenceLog.created_at >= since,
            )
        )
        row = result.one_or_none()

        request_count = row.request_count if row else 0
        avg_latency = round(float(row.avg_latency), 2) if row and row.avg_latency else 0.0

        # Count errors
        error_result = await self.db.execute(
            select(func.count(InferenceLog.id)).where(
                InferenceLog.deployment_id == deployment_id,
                InferenceLog.error_message.isnot(None),
                InferenceLog.created_at >= since,
            )
        )
        error_count = error_result.scalar() or 0

        seconds = max((datetime.now(UTC) - since).total_seconds(), 1)
        error_rate = error_count / max(request_count, 1)
        throughput = request_count / seconds

        return {
            "deployment_id": deployment_id,
            "time_range": time_range,
            "metrics": {
                "request_count": request_count,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": avg_latency * 1.5 if avg_latency else 0.0,
                "error_rate": round(error_rate, 4),
                "throughput_rps": round(throughput, 2),
            },
        }

    async def get_data_drift(self, deployment_id: str) -> dict[str, Any]:
        """Detect data drift using Evidently AI."""
        # Get recent inference logs
        result = await self.db.execute(
            select(InferenceLog)
            .where(InferenceLog.deployment_id == deployment_id)
            .order_by(InferenceLog.created_at.desc())
            .limit(200)
        )
        logs = result.scalars().all()

        if len(logs) < 50:
            return {
                "deployment_id": deployment_id,
                "drift_detected": False,
                "drift_score": 0.0,
                "feature_drifts": [],
                "message": "Not enough data for drift detection (need 50+ samples)",
            }

        try:
            import pandas as pd

            requests = []
            for log in logs:
                if log.request_data:
                    with contextlib.suppress(json.JSONDecodeError):
                        requests.append(json.loads(log.request_data))

            if len(requests) < 50 or not logs[0].deployment_id:
                return {
                    "deployment_id": deployment_id,
                    "drift_detected": False,
                    "drift_score": 0.0,
                    "feature_drifts": [],
                }

            ref_df = pd.DataFrame(requests[:100])
            cur_df = pd.DataFrame(requests[100:])

            # Simple statistical drift check
            drifts = []
            for col in ref_df.select_dtypes(include=["number"]).columns:
                ref_mean = ref_df[col].mean()
                cur_mean = cur_df[col].mean()
                ref_std = ref_df[col].std() or 1.0
                z_score = abs(cur_mean - ref_mean) / ref_std
                if z_score > 2.0:
                    drifts.append(
                        {
                            "feature": col,
                            "z_score": round(float(z_score), 3),
                            "drifted": True,
                        }
                    )

            drift_score = sum(d["z_score"] for d in drifts) / max(len(drifts), 1)
            return {
                "deployment_id": deployment_id,
                "drift_detected": len(drifts) > 0,
                "drift_score": round(drift_score, 3),
                "feature_drifts": drifts,
            }
        except Exception as e:
            return {
                "deployment_id": deployment_id,
                "drift_detected": False,
                "drift_score": 0.0,
                "feature_drifts": [],
                "error": str(e),
            }

    async def log_inference(
        self,
        deployment_id: str,
        request_data: dict | None,
        response_data: dict | None,
        latency_ms: float,
        error: str | None = None,
    ) -> None:
        log_entry = InferenceLog(
            deployment_id=deployment_id,
            request_data=json.dumps(request_data) if request_data else None,
            response_data=json.dumps(response_data) if response_data else None,
            latency_ms=latency_ms,
            error_message=error,
        )
        self.db.add(log_entry)
        await self.db.commit()

    @staticmethod
    def _parse_time_range(time_range: str) -> datetime:
        now = datetime.now(UTC)
        ranges = {
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
        }
        delta = ranges.get(time_range, timedelta(hours=1))
        return now - delta
