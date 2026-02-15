import { describe, it, expect } from "vitest";
import type { Node as RFNode, Edge as RFEdge } from "reactflow";
import { runDiagram } from "./useExecution";

describe("runDiagram — Execute React Flow diagram via engine", () => {
  it("executes a flat graph and returns updated indicator values", async () => {
    const rfNodes: RFNode[] = [
      {
        id: "ctrl-a",
        type: "NumericControl",
        position: { x: 0, y: 0 },
        data: { label: "A", value: 3 },
      },
      {
        id: "ctrl-b",
        type: "NumericControl",
        position: { x: 0, y: 100 },
        data: { label: "B", value: 7 },
      },
      {
        id: "add-1",
        type: "Add",
        position: { x: 200, y: 50 },
        data: { label: "Add" },
      },
      {
        id: "ind-result",
        type: "NumericIndicator",
        position: { x: 400, y: 50 },
        data: { label: "Result", value: 0 },
      },
    ];

    const rfEdges: RFEdge[] = [
      { id: "e1", source: "ctrl-a", sourceHandle: "value", target: "add-1", targetHandle: "a" },
      { id: "e2", source: "ctrl-b", sourceHandle: "value", target: "add-1", targetHandle: "b" },
      { id: "e3", source: "add-1", sourceHandle: "result", target: "ind-result", targetHandle: "value" },
    ];

    const updates = await runDiagram(rfNodes, rfEdges);

    // Returns a map of indicator node IDs to their computed values
    expect(updates).toEqual({ "ind-result": 10 });
  });

  it("returns empty map when no indicators exist", async () => {
    const rfNodes: RFNode[] = [
      {
        id: "ctrl-a",
        type: "NumericControl",
        position: { x: 0, y: 0 },
        data: { label: "A", value: 5 },
      },
    ];

    const updates = await runDiagram(rfNodes, []);
    expect(updates).toEqual({});
  });

  it("executes WhileLoop and returns final indicator value", async () => {
    const rfNodes: RFNode[] = [
      {
        id: "init-val",
        type: "NumericControl",
        position: { x: 0, y: 100 },
        data: { label: "Init", value: 0 },
      },
      {
        id: "loop-1",
        type: "WhileLoop",
        position: { x: 200, y: 50 },
        data: { label: "While Loop", maxIterations: 5 },
        style: { width: 320, height: 220 },
      },
      {
        id: "add-inside",
        type: "Add",
        position: { x: 50, y: 60 },
        data: { label: "Add" },
        parentNode: "loop-1",
        extent: "parent" as const,
      },
      {
        id: "one-const",
        type: "NumericControl",
        position: { x: 50, y: 130 },
        data: { label: "Step", value: 1 },
        parentNode: "loop-1",
        extent: "parent" as const,
      },
      {
        id: "result-ind",
        type: "NumericIndicator",
        position: { x: 600, y: 100 },
        data: { label: "Result", value: 0 },
      },
    ];

    const rfEdges: RFEdge[] = [
      { id: "e1", source: "init-val", sourceHandle: "value", target: "loop-1", targetHandle: "init" },
      { id: "e2", source: "loop-1", sourceHandle: "result", target: "result-ind", targetHandle: "value" },
      { id: "e3", source: "loop-1", sourceHandle: "init-tunnel-in", target: "add-inside", targetHandle: "a" },
      { id: "e4", source: "one-const", sourceHandle: "value", target: "add-inside", targetHandle: "b" },
      { id: "e5", source: "add-inside", sourceHandle: "result", target: "loop-1", targetHandle: "result-tunnel-out" },
    ];

    const updates = await runDiagram(rfNodes, rfEdges);
    expect(updates).toEqual({ "result-ind": 5 });
  });
});
