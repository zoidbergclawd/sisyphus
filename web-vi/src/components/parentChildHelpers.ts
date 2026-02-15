import type { Node } from "reactflow";

/** Minimum node size to be considered a container (avoids false positives with compact nodes). */
const MIN_CONTAINER_WIDTH = 150;
const MIN_CONTAINER_HEIGHT = 100;

/**
 * Find the WhileLoop node that contains the given node based on position overlap.
 * Returns the container's node ID, or null if the node is not inside any loop.
 */
export function findContainingLoop(
  node: Node,
  allNodes: Node[]
): string | null {
  for (const candidate of allNodes) {
    if (candidate.id === node.id) continue;
    if (candidate.type !== "WhileLoop") continue;

    const cw = (candidate.style?.width as number) ?? 320;
    const ch = (candidate.style?.height as number) ?? 220;

    if (cw < MIN_CONTAINER_WIDTH || ch < MIN_CONTAINER_HEIGHT) continue;

    const cx = candidate.position.x;
    const cy = candidate.position.y;

    if (
      node.position.x >= cx &&
      node.position.y >= cy &&
      node.position.x < cx + cw &&
      node.position.y < cy + ch
    ) {
      return candidate.id;
    }
  }
  return null;
}

/**
 * Reparent a node: set or clear its parentNode and adjust position between
 * absolute (canvas) and relative (parent-local) coordinates.
 *
 * - newParentId !== null and differs from current: adopt into parent
 * - newParentId === null and node was parented: remove from parent
 * - newParentId matches current parent: no-op
 */
export function reparentNode(
  node: Node,
  newParentId: string | null,
  parentNode: Node
): Node {
  const currentParent = node.parentNode ?? null;

  // No change
  if (newParentId === currentParent) return node;

  if (newParentId !== null && currentParent === null) {
    // Adopting into a parent: convert absolute → parent-relative
    return {
      ...node,
      parentNode: newParentId,
      extent: "parent" as const,
      position: {
        x: node.position.x - parentNode.position.x,
        y: node.position.y - parentNode.position.y,
      },
    };
  }

  if (newParentId === null && currentParent !== null) {
    // Removing from parent: convert parent-relative → absolute
    return {
      ...node,
      parentNode: undefined,
      extent: undefined,
      position: {
        x: node.position.x + parentNode.position.x,
        y: node.position.y + parentNode.position.y,
      },
    };
  }

  return node;
}
