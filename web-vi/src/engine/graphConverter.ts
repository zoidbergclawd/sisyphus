/**
 * Graph Converter — Bridge between React Flow diagram and the Engine schema.
 *
 * Converts React Flow nodes/edges into the recursive Graph schema that the
 * headless engine can execute. Handles tunneling: wires that cross WhileLoop
 * boundaries are translated into shift registers, iteration counters, and
 * loop conditions inside the engine's child graph.
 */

import type { Node as RFNode, Edge as RFEdge } from "reactflow";
import type { Graph, Node, Edge, NodeType } from "./schema";

/** Map React Flow node type names to engine node types */
const RF_TO_ENGINE_TYPE: Record<string, NodeType> = {
  NumericControl: "Constant",
  NumericIndicator: "Indicator",
  Add: "Add",
  Subtract: "Subtract",
  WhileLoop: "WhileLoop",
};

/**
 * Convention for tunnel handle IDs on WhileLoop nodes:
 * - "init" — input tunnel target handle (external wire connects here)
 * - "result" — output tunnel source handle (external wire connects here)
 * - "init-tunnel-in" — virtual source handle inside the loop body
 *   (shift register read: provides the current value to child nodes)
 * - "result-tunnel-out" — virtual target handle inside the loop body
 *   (shift register write: child nodes write back for next iteration)
 */

/**
 * Convert React Flow nodes and edges into the engine's Graph schema.
 */
export function convertToEngineGraph(
  rfNodes: RFNode[],
  rfEdges: RFEdge[]
): Graph {
  // Partition nodes: top-level vs children of WhileLoops
  const topLevelNodes = rfNodes.filter((n) => !n.parentNode);
  const childrenByParent = new Map<string, RFNode[]>();

  for (const node of rfNodes) {
    if (node.parentNode) {
      const siblings = childrenByParent.get(node.parentNode) ?? [];
      siblings.push(node);
      childrenByParent.set(node.parentNode, siblings);
    }
  }

  // Partition edges into:
  // 1. Top-level edges (between top-level nodes, including WhileLoop external tunnels)
  // 2. Tunnel-in edges (from WhileLoop tunnel-in to child nodes)
  // 3. Tunnel-out edges (from child nodes to WhileLoop tunnel-out)
  // 4. Internal edges (between child nodes within the same parent)
  const topLevelEdges: RFEdge[] = [];
  const tunnelInEdges = new Map<string, RFEdge[]>(); // parent ID → edges
  const tunnelOutEdges = new Map<string, RFEdge[]>(); // parent ID → edges
  const internalEdges = new Map<string, RFEdge[]>(); // parent ID → edges

  const nodeParentMap = new Map<string, string | undefined>();
  for (const node of rfNodes) {
    nodeParentMap.set(node.id, node.parentNode);
  }

  for (const edge of rfEdges) {
    const sourceParent = nodeParentMap.get(edge.source);
    const targetParent = nodeParentMap.get(edge.target);

    if (edge.sourceHandle?.endsWith("-tunnel-in")) {
      // Tunnel-in: WhileLoop source → child node target
      const parentId = edge.source;
      const list = tunnelInEdges.get(parentId) ?? [];
      list.push(edge);
      tunnelInEdges.set(parentId, list);
    } else if (edge.targetHandle?.endsWith("-tunnel-out")) {
      // Tunnel-out: child node source → WhileLoop target
      const parentId = edge.target;
      const list = tunnelOutEdges.get(parentId) ?? [];
      list.push(edge);
      tunnelOutEdges.set(parentId, list);
    } else if (!sourceParent && !targetParent) {
      // Both top-level
      topLevelEdges.push(edge);
    } else if (sourceParent && targetParent && sourceParent === targetParent) {
      // Both in same parent
      const list = internalEdges.get(sourceParent) ?? [];
      list.push(edge);
      internalEdges.set(sourceParent, list);
    } else {
      // Cross-boundary edge not using tunnel convention — treat as top-level
      topLevelEdges.push(edge);
    }
  }

  // Convert top-level nodes to engine nodes
  const engineNodes: Node[] = [];
  const engineEdges: Edge[] = [];

  for (const rfNode of topLevelNodes) {
    const engineType = RF_TO_ENGINE_TYPE[rfNode.type ?? ""];
    if (!engineType) continue;

    if (engineType === "WhileLoop") {
      const childGraph = buildChildGraph(
        rfNode,
        childrenByParent.get(rfNode.id) ?? [],
        tunnelInEdges.get(rfNode.id) ?? [],
        tunnelOutEdges.get(rfNode.id) ?? [],
        internalEdges,
        childrenByParent,
        tunnelInEdges,
        tunnelOutEdges
      );

      engineNodes.push({
        id: rfNode.id,
        type: "WhileLoop",
        data: { maxIterations: (rfNode.data?.maxIterations as number) ?? 1000 },
        inputs: { init: { type: "number" } },
        outputs: { result: { type: "number" } },
        childGraph,
      });
    } else {
      engineNodes.push(convertSimpleNode(rfNode));
    }
  }

  // Convert top-level edges
  for (const edge of topLevelEdges) {
    engineEdges.push({
      from: {
        nodeId: edge.source,
        terminal: edge.sourceHandle ?? "value",
      },
      to: {
        nodeId: edge.target,
        terminal: edge.targetHandle ?? "value",
      },
    });
  }

  return {
    id: "root",
    nodes: engineNodes,
    edges: engineEdges,
  };
}

/**
 * Convert a non-WhileLoop React Flow node to an engine Node.
 */
function convertSimpleNode(rfNode: RFNode): Node {
  const engineType = RF_TO_ENGINE_TYPE[rfNode.type ?? ""] ?? "Constant";

  switch (engineType) {
    case "Constant":
      return {
        id: rfNode.id,
        type: "Constant",
        data: { value: rfNode.data?.value ?? 0 },
        inputs: {},
        outputs: { value: { type: "number" } },
      };

    case "Indicator":
      return {
        id: rfNode.id,
        type: "Indicator",
        data: {},
        inputs: { value: { type: "number" } },
        outputs: {},
      };

    case "Add":
      return {
        id: rfNode.id,
        type: "Add",
        data: {},
        inputs: { a: { type: "number" }, b: { type: "number" } },
        outputs: { result: { type: "number" } },
      };

    case "Subtract":
      return {
        id: rfNode.id,
        type: "Subtract",
        data: {},
        inputs: { a: { type: "number" }, b: { type: "number" } },
        outputs: { result: { type: "number" } },
      };

    default:
      return {
        id: rfNode.id,
        type: engineType,
        data: rfNode.data ?? {},
        inputs: {},
        outputs: {},
      };
  }
}

/**
 * Build the engine child graph for a WhileLoop node.
 *
 * This is where tunneling happens. The visual diagram has:
 * - An "init" input tunnel and a "result" output tunnel on the WhileLoop
 * - Child nodes inside the loop body
 * - Tunnel-in edges (WhileLoop → child, via "init-tunnel-in" source handle)
 * - Tunnel-out edges (child → WhileLoop, via "result-tunnel-out" target handle)
 *
 * The engine needs:
 * - ShiftRegisterRead nodes (provide current value each iteration)
 * - ShiftRegisterWrite nodes (update value for next iteration)
 * - An iteration counter (ShiftRegisterRead/Increment/ShiftRegisterWrite)
 * - A LessThan comparison + LoopCondition to control termination
 */
function buildChildGraph(
  loopNode: RFNode,
  directChildren: RFNode[],
  tunnelIn: RFEdge[],
  tunnelOut: RFEdge[],
  allInternalEdges: Map<string, RFEdge[]>,
  allChildrenByParent: Map<string, RFNode[]>,
  allTunnelInEdges: Map<string, RFEdge[]>,
  allTunnelOutEdges: Map<string, RFEdge[]>
): Graph {
  const childNodes: Node[] = [];
  const childEdges: Edge[] = [];
  const loopId = loopNode.id;
  const maxIterations = (loopNode.data?.maxIterations as number) ?? 1000;

  // 1. Create ShiftRegisterRead for the "init" register
  const srReadId = `${loopId}__sr-read-init`;
  childNodes.push({
    id: srReadId,
    type: "ShiftRegisterRead",
    data: { register: "init" },
    inputs: {},
    outputs: { value: { type: "number" } },
  });

  // 2. Convert direct child nodes (non-WhileLoop children)
  for (const child of directChildren) {
    const childType = RF_TO_ENGINE_TYPE[child.type ?? ""];
    if (!childType) continue;

    if (childType === "WhileLoop") {
      // Nested loop — recurse
      const nestedChildGraph = buildChildGraph(
        child,
        allChildrenByParent.get(child.id) ?? [],
        allTunnelInEdges.get(child.id) ?? [],
        allTunnelOutEdges.get(child.id) ?? [],
        allInternalEdges,
        allChildrenByParent,
        allTunnelInEdges,
        allTunnelOutEdges
      );

      childNodes.push({
        id: child.id,
        type: "WhileLoop",
        data: { maxIterations: (child.data?.maxIterations as number) ?? 1000 },
        inputs: { init: { type: "number" } },
        outputs: { result: { type: "number" } },
        childGraph: nestedChildGraph,
      });
    } else {
      childNodes.push(convertSimpleNode(child));
    }
  }

  // 3. Wire tunnel-in edges: ShiftRegisterRead → child node inputs
  for (const edge of tunnelIn) {
    childEdges.push({
      from: { nodeId: srReadId, terminal: "value" },
      to: {
        nodeId: edge.target,
        terminal: edge.targetHandle ?? "value",
      },
    });
  }

  // 4. Create ShiftRegisterWrite and wire tunnel-out edges
  const srWriteId = `${loopId}__sr-write-init`;
  childNodes.push({
    id: srWriteId,
    type: "ShiftRegisterWrite",
    data: { register: "init" },
    inputs: { value: { type: "number" } },
    outputs: {},
  });

  for (const edge of tunnelOut) {
    childEdges.push({
      from: {
        nodeId: edge.source,
        terminal: edge.sourceHandle ?? "value",
      },
      to: { nodeId: srWriteId, terminal: "value" },
    });
  }

  // 5. Wire internal edges (between child nodes within this loop)
  const internal = allInternalEdges.get(loopId) ?? [];
  for (const edge of internal) {
    childEdges.push({
      from: {
        nodeId: edge.source,
        terminal: edge.sourceHandle ?? "value",
      },
      to: {
        nodeId: edge.target,
        terminal: edge.targetHandle ?? "value",
      },
    });
  }

  // 6. Create iteration counter and loop condition
  // The loop runs maxIterations times using an internal counter
  const iterReadId = `${loopId}__iter-read`;
  const iterIncId = `${loopId}__iter-inc`;
  const iterWriteId = `${loopId}__iter-write`;
  const limitId = `${loopId}__limit`;
  const cmpId = `${loopId}__cmp`;
  const condId = `${loopId}__condition`;

  childNodes.push(
    {
      id: iterReadId,
      type: "ShiftRegisterRead",
      data: { register: "iter" },
      inputs: {},
      outputs: { value: { type: "number" } },
    },
    {
      id: iterIncId,
      type: "Increment",
      data: { amount: 1 },
      inputs: { value: { type: "number" } },
      outputs: { result: { type: "number" } },
    },
    {
      id: iterWriteId,
      type: "ShiftRegisterWrite",
      data: { register: "iter" },
      inputs: { value: { type: "number" } },
      outputs: {},
    },
    {
      id: limitId,
      type: "Constant",
      data: { value: maxIterations },
      inputs: {},
      outputs: { value: { type: "number" } },
    },
    {
      id: cmpId,
      type: "LessThan",
      data: {},
      inputs: { a: { type: "number" }, b: { type: "number" } },
      outputs: { result: { type: "boolean" } },
    },
    {
      id: condId,
      type: "LoopCondition",
      data: {},
      inputs: { continue: { type: "boolean" } },
      outputs: {},
    }
  );

  // Wire iteration counter
  childEdges.push(
    { from: { nodeId: iterReadId, terminal: "value" }, to: { nodeId: iterIncId, terminal: "value" } },
    { from: { nodeId: iterIncId, terminal: "result" }, to: { nodeId: iterWriteId, terminal: "value" } },
    { from: { nodeId: iterIncId, terminal: "result" }, to: { nodeId: cmpId, terminal: "a" } },
    { from: { nodeId: limitId, terminal: "value" }, to: { nodeId: cmpId, terminal: "b" } },
    { from: { nodeId: cmpId, terminal: "result" }, to: { nodeId: condId, terminal: "continue" } }
  );

  return {
    id: `${loopId}-child`,
    nodes: childNodes,
    edges: childEdges,
  };
}
