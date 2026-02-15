import { describe, it, expect } from "vitest";
import type { Node as RFNode, Edge as RFEdge } from "reactflow";
import { convertToEngineGraph } from "./graphConverter";
import { executeGraph } from "./runner";

describe("Graph Converter — React Flow to Engine Bridge", () => {
  it("converts a flat diagram: NumericControl → Add → NumericIndicator", async () => {
    const rfNodes: RFNode[] = [
      {
        id: "ctrl-a",
        type: "NumericControl",
        position: { x: 80, y: 100 },
        data: { label: "A", value: 3 },
      },
      {
        id: "ctrl-b",
        type: "NumericControl",
        position: { x: 80, y: 260 },
        data: { label: "B", value: 7 },
      },
      {
        id: "add-1",
        type: "Add",
        position: { x: 320, y: 160 },
        data: { label: "Add" },
      },
      {
        id: "ind-result",
        type: "NumericIndicator",
        position: { x: 520, y: 160 },
        data: { label: "Result", value: 0 },
      },
    ];

    const rfEdges: RFEdge[] = [
      {
        id: "e1",
        source: "ctrl-a",
        sourceHandle: "value",
        target: "add-1",
        targetHandle: "a",
      },
      {
        id: "e2",
        source: "ctrl-b",
        sourceHandle: "value",
        target: "add-1",
        targetHandle: "b",
      },
      {
        id: "e3",
        source: "add-1",
        sourceHandle: "result",
        target: "ind-result",
        targetHandle: "value",
      },
    ];

    const graph = convertToEngineGraph(rfNodes, rfEdges);
    const result = await executeGraph(graph);

    expect(result.outputs["ind-result"]).toEqual({ value: 10 });
  });

  it("converts Subtract node correctly", async () => {
    const rfNodes: RFNode[] = [
      {
        id: "a",
        type: "NumericControl",
        position: { x: 0, y: 0 },
        data: { label: "A", value: 10 },
      },
      {
        id: "b",
        type: "NumericControl",
        position: { x: 0, y: 100 },
        data: { label: "B", value: 4 },
      },
      {
        id: "sub",
        type: "Subtract",
        position: { x: 200, y: 50 },
        data: { label: "Subtract" },
      },
      {
        id: "out",
        type: "NumericIndicator",
        position: { x: 400, y: 50 },
        data: { label: "Result", value: 0 },
      },
    ];

    const rfEdges: RFEdge[] = [
      { id: "e1", source: "a", sourceHandle: "value", target: "sub", targetHandle: "a" },
      { id: "e2", source: "b", sourceHandle: "value", target: "sub", targetHandle: "b" },
      { id: "e3", source: "sub", sourceHandle: "result", target: "out", targetHandle: "value" },
    ];

    const graph = convertToEngineGraph(rfNodes, rfEdges);
    const result = await executeGraph(graph);

    expect(result.outputs["out"]).toEqual({ value: 6 });
  });

  it("handles unconnected nodes gracefully", async () => {
    const rfNodes: RFNode[] = [
      {
        id: "ctrl",
        type: "NumericControl",
        position: { x: 0, y: 0 },
        data: { label: "A", value: 42 },
      },
      {
        id: "ind",
        type: "NumericIndicator",
        position: { x: 200, y: 0 },
        data: { label: "Out", value: 0 },
      },
    ];

    // No edges — nodes are disconnected
    const rfEdges: RFEdge[] = [];

    const graph = convertToEngineGraph(rfNodes, rfEdges);
    const result = await executeGraph(graph);

    // Indicator exists but receives no input
    expect(result.outputs["ind"]).toBeDefined();
  });
});

describe("Tunneling — Wires Crossing Loop Boundaries", () => {
  it("converts a WhileLoop with child nodes and tunneled wires", async () => {
    // PRD verification scenario:
    // Loop (i < 5) -> Add(i, 1) -> Indicator
    // Expected: Indicator shows values 0, 1, 2, 3, 4, 5
    // (the last value output from the loop after 5 iterations is 5)
    //
    // Visual layout:
    //   [Const 0] ---> [WhileLoop] ---> [Indicator]
    //                   contains:
    //                     [Add(i, 1)] where i is the shift register value
    //
    // The WhileLoop has:
    //   - Input tunnel "init" wired from Const(0)
    //   - Output tunnel "result" wired to Indicator
    //   - An Add node inside that adds 1 to the shift register each iteration
    //   - maxIterations (configured in data) controls the loop count
    //   - The loop internally uses i < maxIterations as condition

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
      // Wire from init constant to WhileLoop input tunnel
      { id: "e1", source: "init-val", sourceHandle: "value", target: "loop-1", targetHandle: "init" },
      // Wire from WhileLoop output tunnel to indicator
      { id: "e2", source: "loop-1", sourceHandle: "result", target: "result-ind", targetHandle: "value" },
      // Inside loop: shift register value → Add input "a"
      // (this is a tunnel wire: the loop's "init" tunnel feeds into the Add node's "a" input)
      { id: "e3", source: "loop-1", sourceHandle: "init-tunnel-in", target: "add-inside", targetHandle: "a" },
      // Inside loop: constant 1 → Add input "b"
      { id: "e4", source: "one-const", sourceHandle: "value", target: "add-inside", targetHandle: "b" },
      // Inside loop: Add result → output tunnel (feeds back to shift register and to output)
      { id: "e5", source: "add-inside", sourceHandle: "result", target: "loop-1", targetHandle: "result-tunnel-out" },
    ];

    const graph = convertToEngineGraph(rfNodes, rfEdges);
    const result = await executeGraph(graph);

    // After 5 iterations: 0+1=1, 1+1=2, 2+1=3, 3+1=4, 4+1=5
    expect(result.outputs["result-ind"]).toEqual({ value: 5 });
  });

  it("supports nested loop execution via converter", async () => {
    // Outer loop runs 3 times, inner loop adds 2 each time
    // Start at 0, after 3 outer iterations: 0 + 2 + 2 + 2 = 6
    const rfNodes: RFNode[] = [
      {
        id: "init-val",
        type: "NumericControl",
        position: { x: 0, y: 100 },
        data: { label: "Init", value: 0 },
      },
      {
        id: "outer-loop",
        type: "WhileLoop",
        position: { x: 200, y: 50 },
        data: { label: "Outer Loop", maxIterations: 3 },
        style: { width: 400, height: 300 },
      },
      {
        id: "inner-loop",
        type: "WhileLoop",
        position: { x: 30, y: 50 },
        data: { label: "Inner Loop", maxIterations: 2 },
        style: { width: 200, height: 150 },
        parentNode: "outer-loop",
        extent: "parent" as const,
      },
      {
        id: "inc-node",
        type: "Add",
        position: { x: 30, y: 30 },
        data: { label: "Add" },
        parentNode: "inner-loop",
        extent: "parent" as const,
      },
      {
        id: "one-const",
        type: "NumericControl",
        position: { x: 30, y: 90 },
        data: { label: "1", value: 1 },
        parentNode: "inner-loop",
        extent: "parent" as const,
      },
      {
        id: "result-ind",
        type: "NumericIndicator",
        position: { x: 700, y: 100 },
        data: { label: "Result", value: 0 },
      },
    ];

    const rfEdges: RFEdge[] = [
      // Init → outer loop input tunnel
      { id: "e1", source: "init-val", sourceHandle: "value", target: "outer-loop", targetHandle: "init" },
      // Outer loop output → indicator
      { id: "e2", source: "outer-loop", sourceHandle: "result", target: "result-ind", targetHandle: "value" },
      // Outer loop tunnel-in → inner loop input
      { id: "e3", source: "outer-loop", sourceHandle: "init-tunnel-in", target: "inner-loop", targetHandle: "init" },
      // Inner loop output → outer loop tunnel-out
      { id: "e4", source: "inner-loop", sourceHandle: "result", target: "outer-loop", targetHandle: "result-tunnel-out" },
      // Inner loop tunnel-in → Add input "a"
      { id: "e5", source: "inner-loop", sourceHandle: "init-tunnel-in", target: "inc-node", targetHandle: "a" },
      // Constant 1 → Add input "b"
      { id: "e6", source: "one-const", sourceHandle: "value", target: "inc-node", targetHandle: "b" },
      // Add result → inner loop tunnel-out
      { id: "e7", source: "inc-node", sourceHandle: "result", target: "inner-loop", targetHandle: "result-tunnel-out" },
    ];

    const graph = convertToEngineGraph(rfNodes, rfEdges);
    const result = await executeGraph(graph);

    // Outer 3 iterations, inner 2 iterations each: 3 * 2 = 6
    expect(result.outputs["result-ind"]).toEqual({ value: 6 });
  });
});
