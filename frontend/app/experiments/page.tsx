"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, Play, Loader2, FlaskConical } from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Experiment {
  id: string;
  name: string;
  problem_type: string;
  target_column: string;
  status: string;
  created_at: string;
}

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchExperiments = useCallback(async () => {
    const data = await apiFetch<Experiment[]>("/api/experiments/");
    setExperiments(data);
    setLoading(false);
  }, []);

  useEffect(() => { fetchExperiments(); }, [fetchExperiments]);

  const handleRun = async (id: string) => {
    await apiFetch(`/api/experiments/${id}/run`, { method: "POST" });
    fetchExperiments();
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
          <h1 className="text-2xl font-bold">实验训练</h1>
          <p className="text-gray-500 text-sm">管理 ML 实验和训练任务</p>
        </div>
        <Link
          href="/pipeline/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          新建实验
        </Link>
      </div>

      {experiments.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center text-gray-400">
          <FlaskConical className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>暂无实验，点击「新建实验」开始在 Pipeline 编辑器中构建</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border">
          <table className="w-full">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium">名称</th>
                <th className="text-left px-4 py-3 text-sm font-medium">类型</th>
                <th className="text-left px-4 py-3 text-sm font-medium">目标列</th>
                <th className="text-left px-4 py-3 text-sm font-medium">状态</th>
                <th className="text-right px-4 py-3 text-sm font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map((exp) => (
                <tr key={exp.id} className="border-b last:border-b-0">
                  <td className="px-4 py-3 text-sm font-medium">{exp.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{exp.problem_type}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{exp.target_column}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      exp.status === "completed" ? "bg-green-100 text-green-700" :
                      exp.status === "running" ? "bg-yellow-100 text-yellow-700" :
                      "bg-gray-100 text-gray-500"
                    }`}>
                      {exp.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <Link
                      href={`/experiments/${exp.id}`}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      查看
                    </Link>
                    <button
                      onClick={() => handleRun(exp.id)}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      <Play className="w-4 h-4 inline" /> 运行
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
