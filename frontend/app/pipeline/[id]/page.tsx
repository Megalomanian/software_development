"use client";

import { useCallback, use } from "react";
import { useRouter } from "next/navigation";
import type { Node, Edge } from "@xyflow/react";
import { PipelineEditor } from "@/components/pipeline-editor/PipelineEditor";
import { apiFetch } from "@/lib/api";

export default function PipelinePage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  const isNew = id === "new";

  const handleSave = useCallback(
    async (nodes: Node[], edges: Edge[]) => {
      const mappedNodes = nodes.map((n) => ({
        type: n.data.nodeType,
        label: n.data.label,
        x: n.position.x,
        y: n.position.y,
        config: n.data.config,
      }));

      const mappedEdges = edges.map((e) => ({
        source: e.source,
        target: e.target,
      }));

      const body = {
        name: `实验_${new Date().toLocaleString("zh-CN")}`,
        target_column: "target",
        problem_type: "classification",
        nodes: mappedNodes,
        edges: mappedEdges,
      };

      const result = await apiFetch<{ id: string }>("/api/experiments/", {
        method: "POST",
        body: JSON.stringify(body),
      });

      router.push(`/experiments/${result.id}`);
    },
    [router]
  );

  return (
    <div className="-m-6 h-screen flex flex-col">
      <PipelineEditor onSave={handleSave} />
    </div>
  );
}
