"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps, NodeResizer } from "reactflow";

interface WhileLoopData {
  label: string;
  width?: number;
  height?: number;
}

/** While Loop container node — resizable parent that holds child nodes. */
export const WhileLoopNode = memo(function WhileLoopNode({
  data,
  selected,
}: NodeProps<WhileLoopData>) {
  return (
    <div
      className={`relative rounded border-2 ${
        selected
          ? "border-cyan-500 ring-2 ring-cyan-500/30"
          : "border-gray-600"
      }`}
      style={{
        width: data.width ?? 320,
        height: data.height ?? 220,
        background: "rgba(30, 41, 59, 0.6)",
      }}
    >
      <NodeResizer
        minWidth={200}
        minHeight={150}
        isVisible={selected ?? false}
        lineClassName="!border-cyan-500"
        handleClassName="!h-2.5 !w-2.5 !rounded-sm !border-cyan-500 !bg-gray-900"
      />

      {/* Header */}
      <div className="flex items-center gap-1.5 border-b border-gray-700 bg-gray-800/80 px-2 py-1 rounded-t">
        <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
          ↻ While Loop
        </span>
      </div>

      {/* Input tunnel (left) */}
      <Handle
        type="target"
        position={Position.Left}
        id="init"
        style={{ top: "50%" }}
        className="!h-3 !w-3 !rounded-sm !border-cyan-600 !bg-cyan-800"
      />

      {/* Output tunnel (right) */}
      <Handle
        type="source"
        position={Position.Right}
        id="result"
        style={{ top: "50%" }}
        className="!h-3 !w-3 !rounded-sm !border-cyan-600 !bg-cyan-800"
      />
    </div>
  );
});
