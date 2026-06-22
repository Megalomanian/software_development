"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { Loader2, BarChart3, TrendingUp } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface MetricsData {
  metrics: { key: string; value: number }[];
  params: { key: string; value: string }[];
}

export default function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = useCallback(async () => {
    const data = await apiFetch<MetricsData>(`/api/experiments/${id}/mlflow-metrics`);
    setMetrics(data);
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchMetrics(); }, [fetchMetrics]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">实验详情</h1>
        <p className="text-gray-500 text-sm">ID: {id}</p>
      </div>

      {!metrics || metrics.metrics.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>暂无指标数据，请先运行实验</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Metrics */}
          <div className="bg-white rounded-xl border p-4">
            <h2 className="font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-green-600" />
              训练指标
            </h2>
            <div className="grid grid-cols-2 gap-3">
              {metrics.metrics.map((m) => (
                <div key={m.key} className="bg-gray-50 rounded-lg p-3">
                  <div className="text-2xl font-bold text-green-600">
                    {typeof m.value === "number" ? m.value.toFixed(4) : m.value}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{m.key}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Params */}
          <div className="bg-white rounded-xl border p-4">
            <h2 className="font-semibold mb-4">超参数</h2>
            <div className="space-y-2">
              {metrics.params.map((p) => (
                <div key={p.key} className="flex justify-between text-sm bg-gray-50 rounded-lg p-3">
                  <span className="text-gray-500">{p.key}</span>
                  <span className="font-mono">{p.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
