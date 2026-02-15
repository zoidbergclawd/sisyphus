"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

export interface NumericControlData {
  label: string;
  value: number;
  onChange?: (value: number) => void;
}

/** Numeric Control — an editable input node with an output handle (source). */
export const NumericControlNode = memo(function NumericControlNode({
  data,
  selected,
}: NodeProps<NumericControlData>) {
  return (
    <div
      className={`rounded-md border bg-white px-3 py-2 shadow-sm ${
        selected ? "ring-2 ring-blue-500 border-blue-500" : "border-gray-300"
      }`}
    >
      <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 mb-1">
        {data.label}
      </div>
      <input
        type="number"
        className="w-20 rounded border border-gray-200 bg-gray-50 px-2 py-1 text-sm text-right tabular-nums focus:outline-none focus:ring-1 focus:ring-blue-400"
        value={data.value}
        onChange={(e) => data.onChange?.(Number(e.target.value))}
      />
      <Handle type="source" position={Position.Right} id="value" />
    </div>
  );
});
