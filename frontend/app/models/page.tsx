"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, Rocket, ArrowUpCircle, Plus, X } from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface ModelVersion {
  id: string;
  name: string;
  version: number;
  framework: string | null;
  status: string;
  created_at: string;
}

interface Experiment {
  id: string;
  name: string;
  mlflow_run_id: string | null;
  status: string;
}

export default function ModelsPage() {
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRegister, setShowRegister] = useState(false);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExp, setSelectedExp] = useState("");
  const [modelName, setModelName] = useState("");
  const [registering, setRegistering] = useState(false);

  const fetchModels = useCallback(async () => {
    const data = await apiFetch<ModelVersion[]>("/api/models/");
    setModels(data);
    setLoading(false);
  }, []);

  useEffect(() => { fetchModels(); }, [fetchModels]);

  const handlePromote = async (id: string) => {
    await apiFetch(`/api/models/${id}/promote`, { method: "POST" });
    fetchModels();
  };

  const openRegister = async () => {
    const data = await apiFetch<Experiment[]>("/api/experiments/");
    setExperiments(data.filter((e) => e.mlflow_run_id));
    setShowRegister(true);
  };

  const handleRegister = async () => {
    if (!selectedExp || !modelName) return;
    setRegistering(true);
    await apiFetch("/api/models/register", {
      method: "POST",
      body: JSON.stringify({
        name: modelName,
        experiment_id: selectedExp,
      }),
    });
    setRegistering(false);
    setShowRegister(false);
    fetchModels();
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
          <h1 className="text-2xl font-bold">模型管理</h1>
          <p className="text-gray-500 text-sm">模型注册、版本管理和评估</p>
        </div>
        <button
          onClick={openRegister}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          注册模型
        </button>
      </div>

      {/* Register modal */}
      {showRegister && (
        <div className="fixed inset-0 bg-black/30 z-40 flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-xl w-96 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">注册模型</h3>
              <button onClick={() => setShowRegister(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">模型名称</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="my-model"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">
                选择已完成的实验
              </label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={selectedExp}
                onChange={(e) => setSelectedExp(e.target.value)}
              >
                <option value="">-- 选择实验 --</option>
                {experiments.map((exp) => (
                  <option key={exp.id} value={exp.id}>
                    {exp.name} ({exp.status})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowRegister(false)} className="px-3 py-1.5 text-sm text-gray-500">
                取消
              </button>
              <button
                onClick={handleRegister}
                disabled={!selectedExp || !modelName || registering}
                className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {registering ? "注册中..." : "确认注册"}
              </button>
            </div>
          </div>
        </div>
      )}

      {models.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
          <p>暂无已注册模型，运行实验后在此注册</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((m) => (
            <div key={m.id} className="bg-white rounded-xl border p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-semibold">{m.name}</h3>
                  <p className="text-xs text-gray-400">v{m.version}</p>
                </div>
                <div className="flex items-center gap-1">
                  <Link
                    href="/deployments"
                    className="text-gray-400 hover:text-green-600 transition-colors"
                    title="部署"
                  >
                    <Rocket className="w-4 h-4" />
                  </Link>
                  <button
                    onClick={() => handlePromote(m.id)}
                    className="text-gray-400 hover:text-blue-600 transition-colors"
                    title="提升版本"
                  >
                    <ArrowUpCircle className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span>{m.framework || "sklearn"}</span>
                <span className={`px-1.5 py-0.5 rounded ${
                  m.status === "registered" ? "bg-green-100 text-green-700" : "bg-gray-100"
                }`}>
                  {m.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
