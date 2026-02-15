import type { NodeTypes } from "reactflow";
import { NumericControlNode } from "./NumericControlNode";
import { NumericIndicatorNode } from "./NumericIndicatorNode";
import { AddNode } from "./AddNode";
import { SubtractNode } from "./SubtractNode";

export { NumericControlNode } from "./NumericControlNode";
export { NumericIndicatorNode } from "./NumericIndicatorNode";
export { AddNode } from "./AddNode";
export { SubtractNode } from "./SubtractNode";

/** Registry of custom node types for React Flow */
export const NODE_TYPES: NodeTypes = {
  NumericControl: NumericControlNode,
  NumericIndicator: NumericIndicatorNode,
  Add: AddNode,
  Subtract: SubtractNode,
};
