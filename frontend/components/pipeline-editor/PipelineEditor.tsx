"use client";

import { useCallback, useRef, useState, type DragEvent } from "react";
import {
  ReactFlow,
  type Node,
  type Edge,
  type Connection,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  type OnConnect,
  type NodeMouseHandler,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { PipelineNodeMemo, type PipelineNodeData } from "./PipelineNode";
import { NodeConfigPanel } from "./NodeConfigPanel";
import type { NodeType, NodeConfig } from "./types";

const nodeTypes = { pipelineNode: PipelineNodeMemo };

const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];

let idCounter = 0;
function getId() {
  return `node_${++idCounter}`;
}

interface Props {
  onSave: (nodes: Node[], edges: Edge[]) => void;
}

export function PipelineEditor({ onSave }: Props) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as any);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData(
        "application/reactflow-type"
      ) as NodeType;
      if (!type) return;

      const wrapperBounds = reactFlowWrapper.current!.getBoundingClientRect();
      const position = {
        x: event.clientX - wrapperBounds.left - 80,
        y: event.clientY - wrapperBounds.top - 30,
      };

      const typeLabels: Record<NodeType, string> = {
        data_source: "数据源",
        feature_engineering: "特征工程",
        model_training: "模型训练",
        evaluation: "模型评估",
      };

      const newNode: Node = {
        id: getId(),
        type: "pipelineNode",
        position,
        data: {
          label: typeLabels[type],
          nodeType: type,
          config: {} as NodeConfig,
        } satisfies PipelineNodeData,
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [setNodes]
  );

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    setSelectedNode(node);
  }, []);

  const handleConfigSave = useCallback(
    (config: NodeConfig) => {
      if (!selectedNode) return;
      setNodes((nds) =>
        nds.map((n) =>
          n.id === selectedNode.id
            ? {
                ...n,
                data: { ...(n.data as PipelineNodeData), config },
              }
            : n
        )
      );
    },
    [selectedNode, setNodes]
  );

  const handleSave = () => {
    onSave(nodes, edges);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b bg-white shrink-0">
        <span className="text-sm text-gray-500">
          拖拽左侧节点到画布，连接形成 Pipeline
        </span>
        <button
          onClick={handleSave}
          className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          保存 Pipeline
        </button>
      </div>

      <div className="flex-1 flex">
        <div className="w-48 shrink-0 p-3 border-r bg-gray-50">
          <div className="space-y-2">
            {((
              ["data_source", "feature_engineering", "model_training", "evaluation"] as NodeType[]
            ).map((type) => {
              const labels: Record<NodeType, { label: string; icon: string; color: string }> = {
                data_source: { label: "数据源", icon: "📊", color: "border-blue-400 bg-blue-50" },
                feature_engineering: { label: "特征工程", icon: "🔧", color: "border-yellow-400 bg-yellow-50" },
                model_training: { label: "模型训练", icon: "🧠", color: "border-green-400 bg-green-50" },
                evaluation: { label: "模型评估", icon: "📈", color: "border-purple-400 bg-purple-50" },
              };
              const def = labels[type];
              return (
                <div
                  key={type}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("application/reactflow-type", type);
                    e.dataTransfer.effectAllowed = "move";
                  }}
                  className={`px-3 py-2.5 rounded-lg border-2 cursor-grab active:cursor-grabbing hover:shadow-sm transition-shadow text-sm ${def.color}`}
                >
                  <span>{def.icon}</span> <span className="font-medium">{def.label}</span>
                </div>
              );
            }))}
          </div>
        </div>

        <div ref={reactFlowWrapper} className="flex-1" style={{ height: "calc(100vh - 12rem)" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[20, 20]}
          >
            <Controls />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          </ReactFlow>
        </div>
      </div>

      {selectedNode && (
        <NodeConfigPanel
          nodeType={(selectedNode.data as PipelineNodeData).nodeType}
          config={(selectedNode.data as PipelineNodeData).config}
          onSave={handleConfigSave}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}
