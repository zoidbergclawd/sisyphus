import { describe, it, expect } from "vitest";
import type { Node } from "reactflow";
import { findContainingLoop, reparentNode } from "./parentChildHelpers";

describe("While Loop Container — Parent-Child Data Model", () => {
  const whileLoopNode: Node = {
    id: "loop-1",
    type: "WhileLoop",
    position: { x: 100, y: 100 },
    data: { label: "While Loop" },
    style: { width: 320, height: 220 },
  };

  const addNodeInside: Node = {
    id: "add-1",
    type: "Add",
    position: { x: 150, y: 160 },
    data: { label: "Add" },
  };

  const addNodeOutside: Node = {
    id: "add-2",
    type: "Add",
    position: { x: 500, y: 500 },
    data: { label: "Add" },
  };

  describe("findContainingLoop", () => {
    it("detects when a node is inside a While Loop's bounds", () => {
      const allNodes = [whileLoopNode, addNodeInside, addNodeOutside];
      const container = findContainingLoop(addNodeInside, allNodes);
      expect(container).toBe("loop-1");
    });

    it("returns null when a node is outside all While Loops", () => {
      const allNodes = [whileLoopNode, addNodeInside, addNodeOutside];
      const container = findContainingLoop(addNodeOutside, allNodes);
      expect(container).toBeNull();
    });

    it("does not detect a While Loop as contained within itself", () => {
      const allNodes = [whileLoopNode];
      const container = findContainingLoop(whileLoopNode, allNodes);
      expect(container).toBeNull();
    });
  });

  describe("reparentNode", () => {
    it("sets parentNode and converts position to parent-relative when dropped inside a loop", () => {
      const result = reparentNode(addNodeInside, "loop-1", whileLoopNode);
      expect(result.parentNode).toBe("loop-1");
      // Position should be relative to parent: 150-100=50, 160-100=60
      expect(result.position.x).toBe(50);
      expect(result.position.y).toBe(60);
      expect(result.extent).toBe("parent");
    });

    it("clears parentNode and converts position to absolute when moved out", () => {
      const childNode: Node = {
        id: "add-1",
        type: "Add",
        position: { x: 50, y: 60 },
        data: { label: "Add" },
        parentNode: "loop-1",
        extent: "parent",
      };
      const result = reparentNode(childNode, null, whileLoopNode);
      expect(result.parentNode).toBeUndefined();
      // Position should be absolute: 50+100=150, 60+100=160
      expect(result.position.x).toBe(150);
      expect(result.position.y).toBe(160);
      expect(result.extent).toBeUndefined();
    });

    it("keeps node unchanged when parent stays the same", () => {
      const childNode: Node = {
        id: "add-1",
        type: "Add",
        position: { x: 50, y: 60 },
        data: { label: "Add" },
        parentNode: "loop-1",
        extent: "parent",
      };
      const result = reparentNode(childNode, "loop-1", whileLoopNode);
      expect(result.parentNode).toBe("loop-1");
      expect(result.position.x).toBe(50);
      expect(result.position.y).toBe(60);
    });
  });
});
