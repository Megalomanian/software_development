"use client";

import { useState, type ChangeEvent } from "react";
import { X } from "lucide-react";
import type { NodeType, NodeConfig, FeatureOp } from "./types";

const MODEL_OPTIONS = [
  { value: "random_forest", label: "随机森林" },
  { value: "logistic_regression", label: "逻辑回归" },
  { value: "linear_regression", label: "线性回归" },
  { value: "xgboost", label: "XGBoost" },
];

const METRIC_OPTIONS = ["accuracy", "precision", "recall", "f1", "mse", "r2", "mae"];

const FEATURE_OPS: { value: FeatureOp["type"]; label: string }[] = [
  { value: "drop_columns", label: "删除列" },
  { value: "fill_na", label: "填充空值" },
  { value: "normalize", label: "标准化" },
  { value: "one_hot_encode", label: "One-Hot 编码" },
  { value: "label_encode", label: "标签编码" },
];

interface Props {
  nodeType: NodeType;
  config: NodeConfig;
  onSave: (config: NodeConfig) => void;
  onClose: () => void;
}

export function NodeConfigPanel({ nodeType, config, onSave, onClose }: Props) {
  const [localConfig, setLocalConfig] = useState<NodeConfig>(config);

  const handleSave = () => {
    onSave(localConfig);
    onClose();
  };

  const addFeatureOp = () => {
    const ops = [...(localConfig.operations || []), { type: "normalize" as const, value: "" }];
    setLocalConfig({ ...localConfig, operations: ops });
  };

  const updateFeatureOp = (index: number, field: keyof FeatureOp, value: string) => {
    const ops = [...(localConfig.operations || [])];
    ops[index] = { ...ops[index], [field]: value };
    setLocalConfig({ ...localConfig, operations: ops });
  };

  const removeFeatureOp = (index: number) => {
    const ops = (localConfig.operations || []).filter((_, i) => i !== index);
    setLocalConfig({ ...localConfig, operations: ops });
  };

  return (
    <div className="fixed top-16 right-4 w-80 bg-white rounded-xl border shadow-lg z-50 max-h-[80vh] overflow-auto">
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-semibold text-sm">节点配置</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Model training config */}
        {nodeType === "model_training" && (
          <>
            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">算法</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={localConfig.model_type || "random_forest"}
                onChange={(e) =>
                  setLocalConfig({ ...localConfig, model_type: e.target.value as NodeConfig["model_type"] })
                }
              >
                {MODEL_OPTIONS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">
                超参数 (JSON)
              </label>
              <textarea
                className="w-full border rounded-lg px-3 py-2 text-sm font-mono"
                rows={4}
                defaultValue={JSON.stringify(localConfig.params || {}, null, 2)}
                onBlur={(e) => {
                  try {
                    setLocalConfig({ ...localConfig, params: JSON.parse(e.target.value) });
                  } catch {
                    // invalid JSON, ignore
                  }
                }}
              />
            </div>
          </>
        )}

        {/* Feature engineering config */}
        {nodeType === "feature_engineering" && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-gray-500">特征操作</label>
              <button
                onClick={addFeatureOp}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                + 添加
              </button>
            </div>
            <div className="space-y-2">
              {(localConfig.operations || []).map((op, i) => (
                <div key={i} className="flex items-center gap-2">
                  <select
                    className="border rounded px-2 py-1 text-xs flex-1"
                    value={op.type}
                    onChange={(e) =>
                      updateFeatureOp(i, "type", e.target.value)
                    }
                  >
                    {FEATURE_OPS.map((fo) => (
                      <option key={fo.value} value={fo.value}>
                        {fo.label}
                      </option>
                    ))}
                  </select>
                  <input
                    className="border rounded px-2 py-1 text-xs w-24"
                    placeholder="列名"
                    value={op.column || ""}
                    onChange={(e) => updateFeatureOp(i, "column", e.target.value)}
                  />
                  <button
                    onClick={() => removeFeatureOp(i)}
                    className="text-red-400 hover:text-red-600 text-xs"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Evaluation config */}
        {nodeType === "evaluation" && (
          <div>
            <label className="text-xs font-medium text-gray-500 block mb-1">
              评估指标
            </label>
            <div className="flex flex-wrap gap-1.5">
              {METRIC_OPTIONS.map((m) => {
                const selected = (localConfig.metrics || []).includes(m);
                return (
                  <button
                    key={m}
                    onClick={() => {
                      const current = localConfig.metrics || [];
                      const next = selected
                        ? current.filter((x) => x !== m)
                        : [...current, m];
                      setLocalConfig({ ...localConfig, metrics: next });
                    }}
                    className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                      selected
                        ? "bg-purple-100 border-purple-300 text-purple-700"
                        : "bg-gray-50 border-gray-200 text-gray-500"
                    }`}
                  >
                    {m}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {nodeType === "data_source" && (
          <div>
            <label className="text-xs font-medium text-gray-500 block mb-1">
              数据集 ID
            </label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="选择或输入数据集 ID"
              value={localConfig.dataset_id || ""}
              onChange={(e) =>
                setLocalConfig({ ...localConfig, dataset_id: e.target.value })
              }
            />
          </div>
        )}
      </div>

      <div className="border-t p-3 flex justify-end gap-2">
        <button
          onClick={onClose}
          className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700"
        >
          取消
        </button>
        <button
          onClick={handleSave}
          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          保存
        </button>
      </div>
    </div>
  );
}
