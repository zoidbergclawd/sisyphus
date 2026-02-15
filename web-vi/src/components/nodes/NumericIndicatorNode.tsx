"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

export interface NumericIndicatorData {
  label: string;
  value: number;
}

/** Numeric Indicator — a read-only display node with an input handle (target). */
export const NumericIndicatorNode = memo(function NumericIndicatorNode({
  data,
  selected,
}: NodeProps<NumericIndicatorData>) {
  return (
    <div
      className={`rounded-md border bg-white px-3 py-2 shadow-sm ${
        selected ? "ring-2 ring-blue-500 border-blue-500" : "border-gray-300"
      }`}
    >
      <Handle type="target" position={Position.Left} id="value" />
      <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 mb-1">
        {data.label}
      </div>
      <div className="w-20 rounded border border-gray-200 bg-gray-100 px-2 py-1 text-sm text-right tabular-nums">
        {data.value}
      </div>
    </div>
  );
});
