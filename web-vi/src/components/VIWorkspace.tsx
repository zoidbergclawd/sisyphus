"use client";

import { useCallback, useState } from "react";
import { useNodesState, useEdgesState } from "reactflow";
import DiagramEditor, { INITIAL_NODES, INITIAL_EDGES } from "./DiagramEditor";
import FrontPanel from "./FrontPanel";
import { runDiagram } from "../engine/useExecution";

/**
 * VIWorkspace — top-level workspace that owns shared state for both
 * the Diagram Editor and Front Panel views with two-way binding.
 */
export default function VIWorkspace() {
  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);
  const [isRunning, setIsRunning] = useState(false);
  const [showPanel, setShowPanel] = useState(false);

  /** Execute the diagram through the engine and update indicators */
  const onRun = useCallback(async () => {
    setIsRunning(true);
    try {
      const updates = await runDiagram(nodes, edges);
      setNodes((nds) =>
        nds.map((n) => {
          if (n.type === "NumericIndicator" && updates[n.id] !== undefined) {
            return { ...n, data: { ...n.data, value: updates[n.id] } };
          }
          return n;
        })
      );
    } finally {
      setIsRunning(false);
    }
  }, [nodes, edges, setNodes]);

  /** Update node data — used by FrontPanel controls and DiagramEditor */
  const updateNodeData = useCallback(
    (nodeId: string, newData: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, ...newData } } : n
        )
      );
    },
    [setNodes]
  );

  return (
    <div className="flex h-screen w-screen bg-gray-950">
      {/* Main diagram area */}
      <div className="relative flex-1">
        <DiagramEditor
          nodes={nodes}
          edges={edges}
          setNodes={setNodes}
          setEdges={setEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onRun={onRun}
          isRunning={isRunning}
        />
        {/* Panel toggle button — floats top-right of diagram area */}
        <button
          onClick={() => setShowPanel((v) => !v)}
          className={`absolute right-3 top-3 z-10 rounded border px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition-colors ${
            showPanel
              ? "border-cyan-500 bg-cyan-900 text-cyan-300"
              : "border-gray-600 bg-gray-800 text-gray-400 hover:border-cyan-700 hover:text-cyan-300"
          }`}
        >
          Panel
        </button>
      </div>

      {/* Front Panel sidebar */}
      {showPanel && (
        <aside className="w-72 shrink-0 overflow-y-auto border-l border-gray-800 bg-gray-900">
          <FrontPanel
            nodes={nodes}
            onNodeDataChange={updateNodeData}
            isRunning={isRunning}
          />
        </aside>
      )}
    </div>
  );
}
