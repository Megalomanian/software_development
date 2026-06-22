"use client";

import { type DragEvent } from "react";
import { NODE_DEFINITIONS, type NodeType } from "./types";

export function NodePalette() {
  const onDragStart = (event: DragEvent, nodeType: NodeType) => {
    event.dataTransfer.setData("application/reactflow-type", nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="bg-white rounded-xl border p-4">
      <h3 className="text-sm font-semibold mb-3 text-gray-500">节点类型</h3>
      <div className="space-y-2">
        {(Object.entries(NODE_DEFINITIONS) as [NodeType, typeof NODE_DEFINITIONS[keyof typeof NODE_DEFINITIONS]][]).map(
          ([type, def]) => (
            <div
              key={type}
              draggable
              onDragStart={(e) => onDragStart(e, type)}
              className={`px-3 py-2.5 rounded-lg border-2 cursor-grab active:cursor-grabbing hover:shadow-sm transition-shadow ${def.color}`}
            >
              <div className="flex items-center gap-2 text-sm">
                <span>{def.icon}</span>
                <span className="font-medium">{def.label}</span>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
