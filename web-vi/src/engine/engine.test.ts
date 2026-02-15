import { describe, it, expect } from "vitest";
import { executeGraph } from "./runner";
import type { Graph } from "./schema";

describe("Recursive Graph Schema", () => {
  it("represents a flat graph with nodes and edges", () => {
    const graph: Graph = {
      id: "root",
      nodes: [
        {
          id: "const1",
          type: "Constant",
          data: { value: 5 },
          inputs: {},
          outputs: { value: { type: "number" } },
        },
        {
          id: "indicator1",
          type: "Indicator",
          data: {},
          inputs: { value: { type: "number" } },
          outputs: {},
        },
      ],
      edges: [
        { from: { nodeId: "const1", terminal: "value" }, to: { nodeId: "indicator1", terminal: "value" } },
      ],
    };

    expect(graph.nodes).toHaveLength(2);
    expect(graph.edges).toHaveLength(1);
  });

  it("supports nested graphs (nodes containing child graphs)", () => {
    const graph: Graph = {
      id: "root",
      nodes: [
        {
          id: "loop1",
          type: "WhileLoop",
          data: { maxIterations: 100 },
          inputs: {},
          outputs: { i: { type: "number" } },
          childGraph: {
            id: "loop1-inner",
            nodes: [
              {
                id: "add1",
                type: "Add",
                data: {},
                inputs: {
                  a: { type: "number" },
                  b: { type: "number" },
                },
                outputs: { result: { type: "number" } },
              },
            ],
            edges: [],
          },
        },
      ],
      edges: [],
    };

    expect(graph.nodes[0].childGraph).toBeDefined();
    expect(graph.nodes[0].childGraph!.nodes).toHaveLength(1);
    expect(graph.nodes[0].childGraph!.id).toBe("loop1-inner");
  });
});

describe("DAG Engine Runner", () => {
  it("executes a simple constant -> indicator graph", async () => {
    const graph: Graph = {
      id: "root",
      nodes: [
        {
          id: "const1",
          type: "Constant",
          data: { value: 42 },
          inputs: {},
          outputs: { value: { type: "number" } },
        },
        {
          id: "indicator1",
          type: "Indicator",
          data: {},
          inputs: { value: { type: "number" } },
          outputs: {},
        },
      ],
      edges: [
        { from: { nodeId: "const1", terminal: "value" }, to: { nodeId: "indicator1", terminal: "value" } },
      ],
    };

    const result = await executeGraph(graph);
    expect(result.outputs["indicator1"]).toEqual({ value: 42 });
  });

  it("executes Add node with two constant inputs", async () => {
    const graph: Graph = {
      id: "root",
      nodes: [
        {
          id: "a",
          type: "Constant",
          data: { value: 3 },
          inputs: {},
          outputs: { value: { type: "number" } },
        },
        {
          id: "b",
          type: "Constant",
          data: { value: 7 },
          inputs: {},
          outputs: { value: { type: "number" } },
        },
        {
          id: "add1",
          type: "Add",
          data: {},
          inputs: { a: { type: "number" }, b: { type: "number" } },
          outputs: { result: { type: "number" } },
        },
        {
          id: "out",
          type: "Indicator",
          data: {},
          inputs: { value: { type: "number" } },
          outputs: {},
        },
      ],
      edges: [
        { from: { nodeId: "a", terminal: "value" }, to: { nodeId: "add1", terminal: "a" } },
        { from: { nodeId: "b", terminal: "value" }, to: { nodeId: "add1", terminal: "b" } },
        { from: { nodeId: "add1", terminal: "result" }, to: { nodeId: "out", terminal: "value" } },
      ],
    };

    const result = await executeGraph(graph);
    expect(result.outputs["out"]).toEqual({ value: 10 });
  });

  it("executes a While Loop that increments 10 times", async () => {
    // PRD verification: "A loop runs 10 times, increments a value, and outputs the final result (10)"
    //
    // Graph structure:
    //   Constant(0) -> WhileLoop(condition: i < 10) -> Indicator
    //   Inside loop: shift register + Increment(+1)
    //
    // The WhileLoop node has:
    //   - An input tunnel "init" for the initial shift register value
    //   - A child graph with:
    //     - ShiftRegisterRead: reads current iteration value
    //     - Increment: adds 1
    //     - ShiftRegisterWrite: writes back for next iteration
    //     - LoopCondition: controls whether to continue (i < 10)
    //   - An output tunnel "result" for the final value

    const graph: Graph = {
      id: "root",
      nodes: [
        {
          id: "init",
          type: "Constant",
          data: { value: 0 },
          inputs: {},
          outputs: { value: { type: "number" } },
        },
        {
          id: "loop",
          type: "WhileLoop",
          data: { maxIterations: 1000 },
          inputs: {
            init: { type: "number" },
          },
          outputs: {
            result: { type: "number" },
          },
          childGraph: {
            id: "loop-inner",
            nodes: [
              {
                id: "sr-read",
                type: "ShiftRegisterRead",
                data: { register: "init" },
                inputs: {},
                outputs: { value: { type: "number" } },
              },
              {
                id: "inc",
                type: "Increment",
                data: { amount: 1 },
                inputs: { value: { type: "number" } },
                outputs: { result: { type: "number" } },
              },
              {
                id: "sr-write",
                type: "ShiftRegisterWrite",
                data: { register: "init" },
                inputs: { value: { type: "number" } },
                outputs: {},
              },
              {
                id: "limit",
                type: "Constant",
                data: { value: 10 },
                inputs: {},
                outputs: { value: { type: "number" } },
              },
              {
                id: "cmp",
                type: "LessThan",
                data: {},
                inputs: { a: { type: "number" }, b: { type: "number" } },
                outputs: { result: { type: "boolean" } },
              },
              {
                id: "condition",
                type: "LoopCondition",
                data: {},
                inputs: { continue: { type: "boolean" } },
                outputs: {},
              },
            ],
            edges: [
              { from: { nodeId: "sr-read", terminal: "value" }, to: { nodeId: "inc", terminal: "value" } },
              { from: { nodeId: "inc", terminal: "result" }, to: { nodeId: "sr-write", terminal: "value" } },
              { from: { nodeId: "inc", terminal: "result" }, to: { nodeId: "cmp", terminal: "a" } },
              { from: { nodeId: "limit", terminal: "value" }, to: { nodeId: "cmp", terminal: "b" } },
              { from: { nodeId: "cmp", terminal: "result" }, to: { nodeId: "condition", terminal: "continue" } },
            ],
          },
        },
        {
          id: "display",
          type: "Indicator",
          data: {},
          inputs: { value: { type: "number" } },
          outputs: {},
        },
      ],
      edges: [
        { from: { nodeId: "init", terminal: "value" }, to: { nodeId: "loop", terminal: "init" } },
        { from: { nodeId: "loop", terminal: "result" }, to: { nodeId: "display", terminal: "value" } },
      ],
    };

    const result = await executeGraph(graph);
    expect(result.outputs["display"]).toEqual({ value: 10 });
  });

  it("prevents infinite loops with maxIterations safety", async () => {
    // A loop where condition is always true, but maxIterations = 5
    const graph: Graph = {
      id: "root",
      nodes: [
        {
          id: "init",
          type: "Constant",
          data: { value: 0 },
          inputs: {},
          outputs: { value: { type: "number" } },
        },
        {
          id: "loop",
          type: "WhileLoop",
          data: { maxIterations: 5 },
          inputs: { init: { type: "number" } },
          outputs: { result: { type: "number" } },
          childGraph: {
            id: "loop-inner",
            nodes: [
              {
                id: "sr-read",
                type: "ShiftRegisterRead",
                data: { register: "init" },
                inputs: {},
                outputs: { value: { type: "number" } },
              },
              {
                id: "inc",
                type: "Increment",
                data: { amount: 1 },
                inputs: { value: { type: "number" } },
                outputs: { result: { type: "number" } },
              },
              {
                id: "sr-write",
                type: "ShiftRegisterWrite",
                data: { register: "init" },
                inputs: { value: { type: "number" } },
                outputs: {},
              },
              {
                id: "always-true",
                type: "Constant",
                data: { value: true },
                inputs: {},
                outputs: { value: { type: "boolean" } },
              },
              {
                id: "condition",
                type: "LoopCondition",
                data: {},
                inputs: { continue: { type: "boolean" } },
                outputs: {},
              },
            ],
            edges: [
              { from: { nodeId: "sr-read", terminal: "value" }, to: { nodeId: "inc", terminal: "value" } },
              { from: { nodeId: "inc", terminal: "result" }, to: { nodeId: "sr-write", terminal: "value" } },
              { from: { nodeId: "always-true", terminal: "value" }, to: { nodeId: "condition", terminal: "continue" } },
            ],
          },
        },
        {
          id: "display",
          type: "Indicator",
          data: {},
          inputs: { value: { type: "number" } },
          outputs: {},
        },
      ],
      edges: [
        { from: { nodeId: "init", terminal: "value" }, to: { nodeId: "loop", terminal: "init" } },
        { from: { nodeId: "loop", terminal: "result" }, to: { nodeId: "display", terminal: "value" } },
      ],
    };

    const result = await executeGraph(graph);
    // Ran 5 times with always-true, so incremented 5 times
    expect(result.outputs["display"]).toEqual({ value: 5 });
  });

  it("handles nested loops (loop inside a loop)", async () => {
    // Outer loop runs 3 times, inner loop runs 4 times each
    // Total increments: 3 * 4 = 12
    const graph: Graph = {
      id: "root",
      nodes: [
        {
          id: "init-outer",
          type: "Constant",
          data: { value: 0 },
          inputs: {},
          outputs: { value: { type: "number" } },
        },
        {
          id: "outer-loop",
          type: "WhileLoop",
          data: { maxIterations: 100 },
          inputs: { init: { type: "number" } },
          outputs: { result: { type: "number" } },
          childGraph: {
            id: "outer-inner",
            nodes: [
              {
                id: "outer-sr-read",
                type: "ShiftRegisterRead",
                data: { register: "init" },
                inputs: {},
                outputs: { value: { type: "number" } },
              },
              // Inner loop: increments the value 4 times
              {
                id: "inner-loop",
                type: "WhileLoop",
                data: { maxIterations: 100 },
                inputs: { init: { type: "number" } },
                outputs: { result: { type: "number" } },
                childGraph: {
                  id: "inner-inner",
                  nodes: [
                    {
                      id: "inner-sr-read",
                      type: "ShiftRegisterRead",
                      data: { register: "init" },
                      inputs: {},
                      outputs: { value: { type: "number" } },
                    },
                    {
                      id: "inner-inc",
                      type: "Increment",
                      data: { amount: 1 },
                      inputs: { value: { type: "number" } },
                      outputs: { result: { type: "number" } },
                    },
                    {
                      id: "inner-sr-write",
                      type: "ShiftRegisterWrite",
                      data: { register: "init" },
                      inputs: { value: { type: "number" } },
                      outputs: {},
                    },
                    // Iteration counter for inner loop
                    {
                      id: "inner-iter-read",
                      type: "ShiftRegisterRead",
                      data: { register: "iter" },
                      inputs: {},
                      outputs: { value: { type: "number" } },
                    },
                    {
                      id: "inner-iter-inc",
                      type: "Increment",
                      data: { amount: 1 },
                      inputs: { value: { type: "number" } },
                      outputs: { result: { type: "number" } },
                    },
                    {
                      id: "inner-iter-write",
                      type: "ShiftRegisterWrite",
                      data: { register: "iter" },
                      inputs: { value: { type: "number" } },
                      outputs: {},
                    },
                    {
                      id: "inner-limit",
                      type: "Constant",
                      data: { value: 4 },
                      inputs: {},
                      outputs: { value: { type: "number" } },
                    },
                    {
                      id: "inner-cmp",
                      type: "LessThan",
                      data: {},
                      inputs: { a: { type: "number" }, b: { type: "number" } },
                      outputs: { result: { type: "boolean" } },
                    },
                    {
                      id: "inner-condition",
                      type: "LoopCondition",
                      data: {},
                      inputs: { continue: { type: "boolean" } },
                      outputs: {},
                    },
                  ],
                  edges: [
                    { from: { nodeId: "inner-sr-read", terminal: "value" }, to: { nodeId: "inner-inc", terminal: "value" } },
                    { from: { nodeId: "inner-inc", terminal: "result" }, to: { nodeId: "inner-sr-write", terminal: "value" } },
                    { from: { nodeId: "inner-iter-read", terminal: "value" }, to: { nodeId: "inner-iter-inc", terminal: "value" } },
                    { from: { nodeId: "inner-iter-inc", terminal: "result" }, to: { nodeId: "inner-iter-write", terminal: "value" } },
                    { from: { nodeId: "inner-iter-inc", terminal: "result" }, to: { nodeId: "inner-cmp", terminal: "a" } },
                    { from: { nodeId: "inner-limit", terminal: "value" }, to: { nodeId: "inner-cmp", terminal: "b" } },
                    { from: { nodeId: "inner-cmp", terminal: "result" }, to: { nodeId: "inner-condition", terminal: "continue" } },
                  ],
                },
              },
              {
                id: "outer-sr-write",
                type: "ShiftRegisterWrite",
                data: { register: "init" },
                inputs: { value: { type: "number" } },
                outputs: {},
              },
              // Outer iteration counter
              {
                id: "outer-iter-read",
                type: "ShiftRegisterRead",
                data: { register: "iter" },
                inputs: {},
                outputs: { value: { type: "number" } },
              },
              {
                id: "outer-iter-inc",
                type: "Increment",
                data: { amount: 1 },
                inputs: { value: { type: "number" } },
                outputs: { result: { type: "number" } },
              },
              {
                id: "outer-iter-write",
                type: "ShiftRegisterWrite",
                data: { register: "iter" },
                inputs: { value: { type: "number" } },
                outputs: {},
              },
              {
                id: "outer-limit",
                type: "Constant",
                data: { value: 3 },
                inputs: {},
                outputs: { value: { type: "number" } },
              },
              {
                id: "outer-cmp",
                type: "LessThan",
                data: {},
                inputs: { a: { type: "number" }, b: { type: "number" } },
                outputs: { result: { type: "boolean" } },
              },
              {
                id: "outer-condition",
                type: "LoopCondition",
                data: {},
                inputs: { continue: { type: "boolean" } },
                outputs: {},
              },
            ],
            edges: [
              // Feed accumulator into inner loop
              { from: { nodeId: "outer-sr-read", terminal: "value" }, to: { nodeId: "inner-loop", terminal: "init" } },
              // Inner loop result back to outer shift register
              { from: { nodeId: "inner-loop", terminal: "result" }, to: { nodeId: "outer-sr-write", terminal: "value" } },
              // Outer iteration counter
              { from: { nodeId: "outer-iter-read", terminal: "value" }, to: { nodeId: "outer-iter-inc", terminal: "value" } },
              { from: { nodeId: "outer-iter-inc", terminal: "result" }, to: { nodeId: "outer-iter-write", terminal: "value" } },
              { from: { nodeId: "outer-iter-inc", terminal: "result" }, to: { nodeId: "outer-cmp", terminal: "a" } },
              { from: { nodeId: "outer-limit", terminal: "value" }, to: { nodeId: "outer-cmp", terminal: "b" } },
              { from: { nodeId: "outer-cmp", terminal: "result" }, to: { nodeId: "outer-condition", terminal: "continue" } },
            ],
          },
        },
        {
          id: "display",
          type: "Indicator",
          data: {},
          inputs: { value: { type: "number" } },
          outputs: {},
        },
      ],
      edges: [
        { from: { nodeId: "init-outer", terminal: "value" }, to: { nodeId: "outer-loop", terminal: "init" } },
        { from: { nodeId: "outer-loop", terminal: "result" }, to: { nodeId: "display", terminal: "value" } },
      ],
    };

    const result = await executeGraph(graph);
    expect(result.outputs["display"]).toEqual({ value: 12 });
  });
});
