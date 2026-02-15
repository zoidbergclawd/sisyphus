/**
 * Recursive Graph Schema for Web VI
 *
 * The key insight: a Graph contains Nodes, and Nodes can contain child Graphs.
 * This recursive structure supports nested structures like While Loops.
 */

/** Terminal definition on a node (input or output port) */
export interface Terminal {
  type: "number" | "boolean" | "string";
}

/** A connection endpoint */
export interface TerminalRef {
  nodeId: string;
  terminal: string;
}

/** A wire connecting an output terminal to an input terminal */
export interface Edge {
  from: TerminalRef;
  to: TerminalRef;
}

/** Node types supported by the engine */
export type NodeType =
  | "Constant"
  | "Indicator"
  | "Add"
  | "Subtract"
  | "Increment"
  | "LessThan"
  | "WhileLoop"
  | "ShiftRegisterRead"
  | "ShiftRegisterWrite"
  | "LoopCondition";

/** A node in the graph. May contain a recursive child graph. */
export interface Node {
  id: string;
  type: NodeType;
  data: Record<string, unknown>;
  inputs: Record<string, Terminal>;
  outputs: Record<string, Terminal>;
  /** Recursive: a node can contain a child graph (e.g., WhileLoop body) */
  childGraph?: Graph;
}

/** A graph: the fundamental recursive unit. Contains nodes and edges. */
export interface Graph {
  id: string;
  nodes: Node[];
  edges: Edge[];
}

/** Result of executing a graph */
export interface ExecutionResult {
  /** Map of Indicator node IDs to their terminal values */
  outputs: Record<string, Record<string, unknown>>;
}
