import type { Graph, Node, ExecutionResult } from "./schema";

/** Values flowing through the graph: map of terminal names to values */
type TerminalValues = Record<string, unknown>;

/** Output state for each node after execution */
type NodeOutputs = Map<string, TerminalValues>;

/**
 * Topologically sort nodes based on edges (Kahn's algorithm).
 * Returns node IDs in execution order.
 */
function topologicalSort(graph: Graph): string[] {
  const inDegree = new Map<string, number>();
  const adjacency = new Map<string, string[]>();

  for (const node of graph.nodes) {
    inDegree.set(node.id, 0);
    adjacency.set(node.id, []);
  }

  for (const edge of graph.edges) {
    const current = inDegree.get(edge.to.nodeId) ?? 0;
    inDegree.set(edge.to.nodeId, current + 1);
    const adj = adjacency.get(edge.from.nodeId) ?? [];
    adj.push(edge.to.nodeId);
    adjacency.set(edge.from.nodeId, adj);
  }

  const queue: string[] = [];
  inDegree.forEach((degree, nodeId) => {
    if (degree === 0) {
      queue.push(nodeId);
    }
  });

  const sorted: string[] = [];
  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    sorted.push(nodeId);
    for (const neighbor of adjacency.get(nodeId) ?? []) {
      const newDegree = (inDegree.get(neighbor) ?? 1) - 1;
      inDegree.set(neighbor, newDegree);
      if (newDegree === 0) {
        queue.push(neighbor);
      }
    }
  }

  return sorted;
}

/**
 * Resolve input values for a node by following edges.
 */
function resolveInputs(
  node: Node,
  graph: Graph,
  nodeOutputs: NodeOutputs
): TerminalValues {
  const inputs: TerminalValues = {};

  for (const edge of graph.edges) {
    if (edge.to.nodeId === node.id) {
      const sourceOutputs = nodeOutputs.get(edge.from.nodeId);
      if (sourceOutputs !== undefined) {
        inputs[edge.to.terminal] = sourceOutputs[edge.from.terminal];
      }
    }
  }

  return inputs;
}

/**
 * Execute a single primitive node (non-structure node).
 */
function executeNode(node: Node, inputs: TerminalValues): TerminalValues {
  switch (node.type) {
    case "Constant":
      return { value: node.data.value };

    case "Indicator":
      return { ...inputs };

    case "Add": {
      const a = inputs.a as number;
      const b = inputs.b as number;
      return { result: a + b };
    }

    case "Subtract": {
      const a = inputs.a as number;
      const b = inputs.b as number;
      return { result: a - b };
    }

    case "Increment": {
      const value = inputs.value as number;
      const amount = node.data.amount as number;
      return { result: value + amount };
    }

    case "LessThan": {
      const a = inputs.a as number;
      const b = inputs.b as number;
      return { result: a < b };
    }

    default:
      return {};
  }
}

/**
 * Execute a While Loop node with its child graph.
 *
 * Shift registers connect the outer graph to the inner loop body.
 * Each iteration:
 *   1. ShiftRegisterRead nodes provide current values
 *   2. The child graph body executes
 *   3. ShiftRegisterWrite nodes update values for next iteration
 *   4. LoopCondition node determines whether to continue
 */
function executeWhileLoop(
  node: Node,
  inputs: TerminalValues
): TerminalValues {
  const childGraph = node.childGraph;
  if (!childGraph) {
    throw new Error(`WhileLoop node "${node.id}" has no child graph`);
  }

  const maxIterations = (node.data.maxIterations as number) ?? 1000;

  // Initialize shift registers from tunnel inputs
  // Each input terminal on the WhileLoop becomes a shift register
  const shiftRegisters = new Map<string, unknown>();
  for (const [name, value] of Object.entries(inputs)) {
    shiftRegisters.set(name, value);
  }

  // Also initialize any shift registers that don't have external inputs
  // (like iteration counters) to a default value
  for (const childNode of childGraph.nodes) {
    if (childNode.type === "ShiftRegisterRead") {
      const register = childNode.data.register as string;
      if (!shiftRegisters.has(register)) {
        shiftRegisters.set(register, 0);
      }
    }
  }

  let iterations = 0;

  while (iterations < maxIterations) {
    // Execute one iteration of the child graph
    const iterResult = executeChildGraphIteration(
      childGraph,
      shiftRegisters
    );

    iterations++;

    // Update shift registers from ShiftRegisterWrite outputs
    iterResult.registerWrites.forEach((value, register) => {
      shiftRegisters.set(register, value);
    });

    // Check loop condition
    if (!iterResult.shouldContinue) {
      break;
    }
  }

  // Map shift registers to output terminals
  // Each output terminal on the WhileLoop reads from a shift register
  const outputs: TerminalValues = {};
  for (const terminalName of Object.keys(node.outputs)) {
    // Output terminal name maps to the shift register of the same-named input
    outputs[terminalName] = shiftRegisters.get(
      // Map "result" output to "init" input register convention
      // For WhileLoop, the output reads from the register that the input initialized
      findRegisterForOutput(node, terminalName)
    );
  }

  return outputs;
}

/**
 * Find which shift register an output terminal should read from.
 * Convention: output terminals read from the register initialized by the
 * corresponding input. If there's only one input/output pair, they match.
 */
function findRegisterForOutput(node: Node, outputName: string): string {
  const inputNames = Object.keys(node.inputs);
  const outputNames = Object.keys(node.outputs);

  // Direct name match (input "x" -> output "x")
  if (inputNames.includes(outputName)) {
    return outputName;
  }

  // Single input/output: they correspond
  if (inputNames.length === 1 && outputNames.length === 1) {
    return inputNames[0];
  }

  // Position-based matching
  const idx = outputNames.indexOf(outputName);
  if (idx >= 0 && idx < inputNames.length) {
    return inputNames[idx];
  }

  return outputName;
}

interface IterationResult {
  shouldContinue: boolean;
  registerWrites: Map<string, unknown>;
}

/**
 * Execute one iteration of a child graph inside a loop.
 */
function executeChildGraphIteration(
  graph: Graph,
  shiftRegisters: Map<string, unknown>
): IterationResult {
  const nodeOutputs: NodeOutputs = new Map();
  const sorted = topologicalSort(graph);
  const nodeMap = new Map(graph.nodes.map((n) => [n.id, n]));

  for (const nodeId of sorted) {
    const node = nodeMap.get(nodeId);
    if (!node) continue;

    if (node.type === "ShiftRegisterRead") {
      const register = node.data.register as string;
      nodeOutputs.set(node.id, { value: shiftRegisters.get(register) });
    } else if (node.type === "ShiftRegisterWrite") {
      const inputs = resolveInputs(node, graph, nodeOutputs);
      nodeOutputs.set(node.id, inputs);
    } else if (node.type === "LoopCondition") {
      const inputs = resolveInputs(node, graph, nodeOutputs);
      nodeOutputs.set(node.id, inputs);
    } else if (node.type === "WhileLoop") {
      // Nested loop: recursive execution
      const inputs = resolveInputs(node, graph, nodeOutputs);
      const outputs = executeWhileLoop(node, inputs);
      nodeOutputs.set(node.id, outputs);
    } else {
      const inputs = resolveInputs(node, graph, nodeOutputs);
      const outputs = executeNode(node, inputs);
      nodeOutputs.set(node.id, outputs);
    }
  }

  // Collect shift register writes
  const registerWrites = new Map<string, unknown>();
  for (const node of graph.nodes) {
    if (node.type === "ShiftRegisterWrite") {
      const register = node.data.register as string;
      const outputs = nodeOutputs.get(node.id);
      if (outputs) {
        registerWrites.set(register, outputs.value);
      }
    }
  }

  // Determine loop condition
  let shouldContinue = true;
  for (const node of graph.nodes) {
    if (node.type === "LoopCondition") {
      const outputs = nodeOutputs.get(node.id);
      if (outputs) {
        shouldContinue = outputs.continue as boolean;
      }
    }
  }

  return { shouldContinue, registerWrites };
}

/**
 * Execute a complete graph and return results.
 * This is the main entry point for the headless engine.
 */
export async function executeGraph(graph: Graph): Promise<ExecutionResult> {
  const nodeOutputs: NodeOutputs = new Map();
  const sorted = topologicalSort(graph);
  const nodeMap = new Map(graph.nodes.map((n) => [n.id, n]));

  for (const nodeId of sorted) {
    const node = nodeMap.get(nodeId);
    if (!node) continue;

    const inputs = resolveInputs(node, graph, nodeOutputs);

    let outputs: TerminalValues;

    if (node.type === "WhileLoop") {
      outputs = executeWhileLoop(node, inputs);
    } else {
      outputs = executeNode(node, inputs);
    }

    nodeOutputs.set(node.id, outputs);
  }

  // Collect Indicator outputs
  const result: ExecutionResult = { outputs: {} };
  for (const node of graph.nodes) {
    if (node.type === "Indicator") {
      const values = nodeOutputs.get(node.id);
      if (values) {
        result.outputs[node.id] = values;
      }
    }
  }

  return result;
}
