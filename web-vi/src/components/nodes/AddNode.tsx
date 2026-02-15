"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

/** Add node — two inputs (a, b), one output (result). */
export const AddNode = memo(function AddNode({
  selected,
}: NodeProps) {
  return (
    <div
      className={`flex h-12 w-12 items-center justify-center rounded-md border bg-white shadow-sm text-lg font-bold text-emerald-600 ${
        selected ? "ring-2 ring-blue-500 border-blue-500" : "border-gray-300"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="a"
        style={{ top: "30%" }}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="b"
        style={{ top: "70%" }}
      />
      +
      <Handle type="source" position={Position.Right} id="result" />
    </div>
  );
});
