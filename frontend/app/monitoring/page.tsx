"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, AlertTriangle, CheckCircle, RefreshCw } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { apiFetch } from "@/lib/api";

interface DeploymentMetrics {
  request_count: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  error_rate: number;
  throughput_rps: number;
}

interface MetricsData {
  deployment_id: string;
  time_range: string;
  metrics: DeploymentMetrics;
}

interface DriftData {
  deployment_id: string;
  drift_detected: boolean;
  drift_score: number;
  feature_drifts: { feature: string; z_score: number; drifted: boolean }[];
  message?: string;
}

export default function MonitoringPage() {
  const [metrics, setMetrics] = useState<MetricsData[]>([]);
  const [drifts, setDrifts] = useState<Record<string, DriftData>>({});
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState("1h");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const deps = await apiFetch<{ id: string }[]>("/api/deployments/");
      const running = deps.filter((d: any) => d.status === "running");

      const metricsResults = await Promise.all(
        running.map((d) =>
          apiFetch<MetricsData>(`/api/monitoring/${d.id}/metrics?time_range=${timeRange}`)
        )
      );
      setMetrics(metricsResults);

      const driftResults = await Promise.all(
        running.map((d) =>
          apiFetch<DriftData>(`/api/monitoring/${d.id}/drift`)
        )
      );
      const driftMap: Record<string, DriftData> = {};
      driftResults.forEach((d) => {
        driftMap[d.deployment_id] = d;
      });
      setDrifts(driftMap);
    } catch {
      // no active deployments
    }
    setLoading(false);
  }, [timeRange]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const chartData = metrics.map((m) => ({
    name: m.deployment_id.slice(0, 8),
    "平均延迟 (ms)": m.metrics.avg_latency_ms,
    "P95 延迟 (ms)": m.metrics.p95_latency_ms,
    "吞吐量 (rps)": m.metrics.throughput_rps,
    请求数: m.metrics.request_count,
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">监控告警</h1>
          <p className="text-gray-500 text-sm">推理服务指标和数据漂移检测</p>
        </div>
        <div className="flex items-center gap-2">
          {["5m", "15m", "1h", "6h", "24h"].map((r) => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
                timeRange === r
                  ? "bg-blue-50 border-blue-300 text-blue-700"
                  : "bg-white border-gray-200 text-gray-500 hover:bg-gray-50"
              }`}
            >
              {r}
            </button>
          ))}
          <button
            onClick={fetchData}
            className="p-1.5 text-gray-400 hover:text-gray-600"
            title="刷新"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {metrics.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
          <p>暂无运行中的推理服务</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Metrics cards */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {metrics.map((m) => {
              const drift = drifts[m.deployment_id];
              return (
                <div key={m.deployment_id} className="space-y-3">
                  <div className="bg-white rounded-xl border p-3 text-center">
                    <div className="text-xs text-gray-400 mb-1">
                      Deploy {m.deployment_id.slice(0, 8)}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <MiniMetric label="请求" value={m.metrics.request_count.toLocaleString()} />
                      <MiniMetric label="平均延迟" value={`${m.metrics.avg_latency_ms}ms`} />
                      <MiniMetric label="P95" value={`${m.metrics.p95_latency_ms}ms`} />
                      <MiniMetric label="错误率" value={`${(m.metrics.error_rate * 100).toFixed(1)}%`} />
                    </div>
                    {drift && (
                      <div className="mt-2 pt-2 border-t">
                        {drift.drift_detected ? (
                          <span className="inline-flex items-center gap-1 text-xs text-red-600">
                            <AlertTriangle className="w-3 h-3" />
                            漂移: {drift.drift_score.toFixed(2)}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-green-600">
                            <CheckCircle className="w-3 h-3" />
                            无漂移
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  {/* Drift details */}
                  {drift?.feature_drifts?.length > 0 && (
                    <div className="bg-white rounded-xl border p-3">
                      <div className="text-xs font-medium text-gray-500 mb-2">
                        特征漂移详情
                      </div>
                      {drift.feature_drifts.map((f) => (
                        <div
                          key={f.feature}
                          className="flex justify-between text-xs py-1"
                        >
                          <span>{f.feature}</span>
                          <span className="text-red-500 font-mono">
                            z={f.z_score}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Chart */}
          <div className="bg-white rounded-xl border p-4">
            <h3 className="font-semibold text-sm mb-4">指标对比</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Bar dataKey="平均延迟 (ms)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="P95 延迟 (ms)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-gray-400">{label}</div>
      <div className="font-semibold text-sm">{value}</div>
    </div>
  );
}
