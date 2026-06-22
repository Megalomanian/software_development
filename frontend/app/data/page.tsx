"use client";

import { useState, useCallback, useEffect } from "react";
import { Upload, FileText, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Dataset {
  id: string;
  name: string;
  row_count: number | null;
  column_count: number | null;
  file_type: string;
  created_at: string;
}

interface ColumnProfile {
  name: string;
  dtype: string;
  null_count: number;
  null_ratio: number;
  unique_count: number;
  mean?: number;
  std?: number;
  min?: number;
  max?: number;
  histogram?: { bin: string; count: number }[];
  top_values?: { value: string; count: number }[];
}

export default function DataPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [uploading, setUploading] = useState(false);
  const [selected, setSelected] = useState<Dataset | null>(null);
  const [profile, setProfile] = useState<{ columns: ColumnProfile[] } | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDatasets = useCallback(async () => {
    const data = await apiFetch<Dataset[]>("/api/data/");
    setDatasets(data);
    setLoading(false);
  }, []);

  useEffect(() => { fetchDatasets(); }, [fetchDatasets]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/data/upload`, {
      method: "POST",
      body: form,
    });
    setUploading(false);
    fetchDatasets();
  };

  const handleSelect = async (dataset: Dataset) => {
    setSelected(dataset);
    const data = await apiFetch<{ columns: ColumnProfile[] }>(
      `/api/data/${dataset.id}/profile`
    );
    setProfile(data);
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
          <h1 className="text-2xl font-bold">数据管理</h1>
          <p className="text-gray-500 text-sm">上传数据集、查看数据画像</p>
        </div>
        <label className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition-colors">
          <Upload className="w-4 h-4" />
          {uploading ? "上传中..." : "上传数据集"}
          <input type="file" accept=".csv,.xlsx" className="hidden" onChange={handleUpload} />
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Dataset list */}
        <div className="bg-white rounded-xl border p-4">
          <h2 className="font-semibold mb-3">数据集列表</h2>
          {datasets.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">暂无数据集，请上传</p>
          ) : (
            <div className="space-y-2">
              {datasets.map((ds) => (
                <button
                  key={ds.id}
                  onClick={() => handleSelect(ds)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${
                    selected?.id === ds.id
                      ? "border-blue-300 bg-blue-50"
                      : "hover:bg-gray-50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-gray-400" />
                    <span className="font-medium text-sm">{ds.name}</span>
                  </div>
                  <div className="flex gap-3 mt-1 text-xs text-gray-400">
                    {ds.row_count != null && <span>{ds.row_count.toLocaleString()} 行</span>}
                    {ds.column_count != null && <span>{ds.column_count} 列</span>}
                    <span>{ds.file_type}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Profile panel */}
        <div className="bg-white rounded-xl border p-4">
          <h2 className="font-semibold mb-3">
            {selected ? `${selected.name} — 数据画像` : "数据画像"}
          </h2>
          {!profile ? (
            <p className="text-gray-400 text-sm py-8 text-center">
              请选择左侧数据集查看
            </p>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-auto">
              {profile.columns.map((col) => (
                <div key={col.name} className="border rounded-lg p-3 text-sm">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">{col.name}</span>
                    <span className="text-gray-400 text-xs">{col.dtype}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs text-gray-500">
                    <div>空值: {col.null_count} ({(col.null_ratio * 100).toFixed(1)}%)</div>
                    <div>唯一值: {col.unique_count}</div>
                    {col.mean != null && <div>均值: {col.mean.toFixed(2)}</div>}
                    {col.min != null && <div>最小: {col.min.toFixed(2)}</div>}
                    {col.max != null && <div>最大: {col.max.toFixed(2)}</div>}
                    {col.std != null && <div>标准差: {col.std.toFixed(2)}</div>}
                  </div>
                  {col.top_values && col.top_values.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {col.top_values.slice(0, 5).map((tv) => (
                        <span
                          key={tv.value}
                          className="px-1.5 py-0.5 bg-gray-100 rounded text-xs"
                        >
                          {tv.value}: {tv.count}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
