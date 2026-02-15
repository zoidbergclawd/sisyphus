import type { NodeTypes } from "reactflow";
import { NumericControlNode } from "./NumericControlNode";
import { NumericIndicatorNode } from "./NumericIndicatorNode";
import { AddNode } from "./AddNode";
import { SubtractNode } from "./SubtractNode";
import { WhileLoopNode } from "./WhileLoopNode";

export { NumericControlNode } from "./NumericControlNode";
export { NumericIndicatorNode } from "./NumericIndicatorNode";
export { AddNode } from "./AddNode";
export { SubtractNode } from "./SubtractNode";
export { WhileLoopNode } from "./WhileLoopNode";

/** Registry of custom node types for React Flow */
export const NODE_TYPES: NodeTypes = {
  NumericControl: NumericControlNode,
  NumericIndicator: NumericIndicatorNode,
  Add: AddNode,
  Subtract: SubtractNode,
  WhileLoop: WhileLoopNode,
};
