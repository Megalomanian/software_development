"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Loader2, Power, ExternalLink, Rocket, X, RefreshCw,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Deployment {
  id: string;
  name: string;
  status: string;
  endpoint_url: string | null;
  replicas: number;
  created_at: string;
}

interface ModelVersion {
  id: string;
  name: string;
  version: number;
  status: string;
}

export default function DeploymentsPage() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [replicas, setReplicas] = useState(1);
  const [deploying, setDeploying] = useState(false);

  const fetchDeployments = useCallback(async () => {
    const data = await apiFetch<Deployment[]>("/api/deployments/");
    setDeployments(data);
    setLoading(false);
  }, []);

  useEffect(() => { fetchDeployments(); }, [fetchDeployments]);

  const handleCreate = async () => {
    if (!selectedModel) return;
    setDeploying(true);
    await apiFetch("/api/deployments/", {
      method: "POST",
      body: JSON.stringify({
        model_version_id: selectedModel,
        replicas,
      }),
    });
    setDeploying(false);
    setShowCreate(false);
    fetchDeployments();
  };

  const handleStop = async (id: string) => {
    await apiFetch(`/api/deployments/${id}/stop`, { method: "POST" });
    fetchDeployments();
  };

  const openCreate = async () => {
    const data = await apiFetch<ModelVersion[]>("/api/models/");
    setModels(data);
    setShowCreate(true);
  };

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
          <h1 className="text-2xl font-bold">在线推理</h1>
          <p className="text-gray-500 text-sm">模型部署和推理服务管理</p>
        </div>
        <button
          onClick={openCreate}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Rocket className="w-4 h-4" />
          一键部署
        </button>
      </div>

      {/* Create deployment modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/30 z-40 flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-xl w-96 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">新建部署</h3>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">
                选择模型
              </label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                <option value="">-- 选择模型版本 --</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} v{m.version}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">
                副本数
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={replicas}
                onChange={(e) => setReplicas(Number(e.target.value))}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowCreate(false)}
                className="px-3 py-1.5 text-sm text-gray-500"
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                disabled={!selectedModel || deploying}
                className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {deploying ? (
                  <>
                    <RefreshCw className="w-3 h-3 inline animate-spin mr-1" />
                    部署中...
                  </>
                ) : (
                  "确认部署"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {deployments.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
          <Rocket className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>暂无部署，点击「一键部署」选择模型开始</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {deployments.map((d) => (
            <div key={d.id} className="bg-white rounded-xl border p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm">{d.name}</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  d.status === "running" ? "bg-green-100 text-green-700" :
                  d.status === "stopped" ? "bg-gray-100 text-gray-500" :
                  d.status === "deploying" ? "bg-yellow-100 text-yellow-700" :
                  "bg-red-100 text-red-700"
                }`}>
                  {d.status}
                </span>
              </div>
              <div className="text-xs text-gray-500 space-y-1 mb-3">
                <div>副本数: {d.replicas}</div>
                {d.endpoint_url && (
                  <div className="flex items-center gap-1">
                    <span className="truncate">{d.endpoint_url}</span>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                {d.endpoint_url && d.status === "running" && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(d.endpoint_url || "");
                    }}
                    className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
                  >
                    <ExternalLink className="w-3 h-3" /> 复制端点
                  </button>
                )}
                <button
                  onClick={() => handleStop(d.id)}
                  disabled={d.status !== "running"}
                  className="text-xs text-red-600 hover:text-red-800 disabled:text-gray-300"
                >
                  <Power className="w-3 h-3 inline" /> 停止
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
