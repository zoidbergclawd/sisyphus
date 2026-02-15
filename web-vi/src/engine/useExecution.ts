/**
 * Execution bridge — converts React Flow state to engine graph, runs it,
 * and returns indicator values for updating the UI.
 */

import type { Node as RFNode, Edge as RFEdge } from "reactflow";
import { convertToEngineGraph } from "./graphConverter";
import { executeGraph } from "./runner";

/**
 * Execute the current React Flow diagram through the engine.
 *
 * Returns a map of NumericIndicator node IDs to their computed values.
 */
export async function runDiagram(
  nodes: RFNode[],
  edges: RFEdge[]
): Promise<Record<string, number>> {
  const graph = convertToEngineGraph(nodes, edges);
  const result = await executeGraph(graph);

  // Extract indicator values from engine output
  const updates: Record<string, number> = {};
  for (const [nodeId, terminals] of Object.entries(result.outputs)) {
    if (terminals.value !== undefined) {
      updates[nodeId] = terminals.value as number;
    }
  }

  return updates;
}
