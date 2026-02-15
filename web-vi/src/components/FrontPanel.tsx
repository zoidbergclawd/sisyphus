"use client";

import type { Node } from "reactflow";

interface FrontPanelProps {
  /** All React Flow nodes from the diagram */
  nodes: Node[];
  /** Callback to update a node's data (same as DiagramEditor's updateNodeData) */
  onNodeDataChange: (nodeId: string, newData: Record<string, unknown>) => void;
  /** Whether the diagram is currently executing */
  isRunning: boolean;
}

/**
 * Front Panel — a separate view showing Controls (editable) and Indicators (read-only).
 * Mirrors the LabVIEW Front Panel concept: users interact with Controls/Indicators
 * without seeing the wiring diagram.
 */
export default function FrontPanel({
  nodes,
  onNodeDataChange,
  isRunning,
}: FrontPanelProps) {
  const controls = nodes.filter((n) => n.type === "NumericControl");
  const indicators = nodes.filter((n) => n.type === "NumericIndicator");

  return (
    <div className="flex h-full flex-col gap-6 p-6" data-testid="front-panel">
      {/* Controls section */}
      <section>
        <h3 className="mb-3 text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500">
          Controls
        </h3>
        {controls.length === 0 ? (
          <p className="text-xs text-gray-600">
            No controls on diagram. Add a Numeric Control.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {controls.map((node) => (
              <div
                key={node.id}
                className="flex items-center justify-between rounded-md border border-gray-700 bg-gray-800 px-4 py-3"
              >
                <label
                  className="text-sm font-medium text-gray-300"
                  htmlFor={`panel-ctrl-${node.id}`}
                >
                  {node.data.label}
                </label>
                <input
                  id={`panel-ctrl-${node.id}`}
                  type="number"
                  className="w-24 rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm text-right tabular-nums text-gray-200 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  value={node.data.value}
                  onChange={(e) =>
                    onNodeDataChange(node.id, { value: Number(e.target.value) })
                  }
                />
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Indicators section */}
      <section>
        <h3 className="mb-3 text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500">
          Indicators
        </h3>
        {indicators.length === 0 ? (
          <p className="text-xs text-gray-600">
            No indicators on diagram. Add a Numeric Indicator.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {indicators.map((node) => (
              <div
                key={node.id}
                className="flex items-center justify-between rounded-md border border-gray-700 bg-gray-800 px-4 py-3"
              >
                <span className="text-sm font-medium text-gray-300">
                  {node.data.label}
                </span>
                <div
                  className="w-24 rounded border border-gray-600 bg-gray-950 px-2 py-1 text-sm text-right tabular-nums text-gray-200"
                  data-testid={`panel-ind-${node.id}`}
                >
                  {node.data.value}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Running indicator */}
      {isRunning && (
        <div className="text-xs text-cyan-400" data-testid="panel-running">
          Executing...
        </div>
      )}
    </div>
  );
}
