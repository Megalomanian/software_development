"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { NODE_DEFINITIONS, type NodeConfig } from "./types";

export type PipelineNodeData = {
  label: string;
  nodeType: keyof typeof NODE_DEFINITIONS;
  config: NodeConfig;
};

function PipelineNodeComponent({ data, selected }: NodeProps) {
  const d = data as PipelineNodeData;
  const def = NODE_DEFINITIONS[d.nodeType];

  return (
    <div
      className={`px-4 py-3 rounded-xl border-2 shadow-sm min-w-[160px] ${
        selected ? "ring-2 ring-blue-400" : ""
      } ${def.color}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
      <div className="flex items-center gap-2">
        <span className="text-lg">{def.icon}</span>
        <div>
          <div className="font-semibold text-sm">{d.label}</div>
          <div className="text-xs text-gray-500">{def.label}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
}

export const PipelineNodeMemo = memo(PipelineNodeComponent);
