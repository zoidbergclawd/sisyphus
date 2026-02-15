import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ReactFlowProvider } from "reactflow";
import { NumericControlNode } from "./NumericControlNode";
import { NumericIndicatorNode } from "./NumericIndicatorNode";
import { AddNode } from "./AddNode";
import { SubtractNode } from "./SubtractNode";
import { WhileLoopNode } from "./WhileLoopNode";
import { NODE_TYPES } from "./index";

/** Wrapper to provide ReactFlow context required by Handle components */
function FlowWrapper({ children }: { children: React.ReactNode }) {
  return <ReactFlowProvider>{children}</ReactFlowProvider>;
}

describe("Custom Node Types", () => {
  describe("NumericControlNode", () => {
    it("renders with a label and editable input", () => {
      render(
        <FlowWrapper>
          <NumericControlNode
            id="ctrl-1"
            data={{ label: "X", value: 42 }}
            selected={false}
            type="NumericControl"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      expect(screen.getByText("X")).toBeInTheDocument();
      const input = screen.getByRole("spinbutton") as HTMLInputElement;
      expect(input.value).toBe("42");
    });

    it("calls onChange when value is edited", () => {
      const onChange = vi.fn();
      const { container } = render(
        <FlowWrapper>
          <NumericControlNode
            id="ctrl-1"
            data={{ label: "X", value: 0, onChange }}
            selected={false}
            type="NumericControl"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const input = container.querySelector(
        'input[type="number"]'
      ) as HTMLInputElement;
      fireEvent.change(input, { target: { value: "99" } });
      expect(onChange).toHaveBeenCalledWith(99);
    });

    it("has an output handle", () => {
      const { container } = render(
        <FlowWrapper>
          <NumericControlNode
            id="ctrl-1"
            data={{ label: "X", value: 0 }}
            selected={false}
            type="NumericControl"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const sourceHandle = container.querySelector(
        '.react-flow__handle[data-handlepos="right"]'
      );
      expect(sourceHandle).toBeInTheDocument();
    });

    it("shows selection ring when selected", () => {
      const { container } = render(
        <FlowWrapper>
          <NumericControlNode
            id="ctrl-1"
            data={{ label: "X", value: 0 }}
            selected={true}
            type="NumericControl"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const nodeEl = container.firstElementChild as HTMLElement;
      expect(nodeEl.className).toContain("ring-2");
    });
  });

  describe("NumericIndicatorNode", () => {
    it("renders with a label and displays the value", () => {
      render(
        <FlowWrapper>
          <NumericIndicatorNode
            id="ind-1"
            data={{ label: "Result", value: 10 }}
            selected={false}
            type="NumericIndicator"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      expect(screen.getByText("Result")).toBeInTheDocument();
      expect(screen.getByText("10")).toBeInTheDocument();
    });

    it("has an input handle", () => {
      const { container } = render(
        <FlowWrapper>
          <NumericIndicatorNode
            id="ind-1"
            data={{ label: "Result", value: 0 }}
            selected={false}
            type="NumericIndicator"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const targetHandle = container.querySelector(
        '.react-flow__handle[data-handlepos="left"]'
      );
      expect(targetHandle).toBeInTheDocument();
    });

    it("shows selection ring when selected", () => {
      const { container } = render(
        <FlowWrapper>
          <NumericIndicatorNode
            id="ind-1"
            data={{ label: "Result", value: 0 }}
            selected={true}
            type="NumericIndicator"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const nodeEl = container.firstElementChild as HTMLElement;
      expect(nodeEl.className).toContain("ring-2");
    });
  });

  describe("AddNode", () => {
    it("renders with Add label", () => {
      render(
        <FlowWrapper>
          <AddNode
            id="add-1"
            data={{ label: "Add" }}
            selected={false}
            type="Add"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      expect(screen.getByText("+")).toBeInTheDocument();
    });

    it("has two input handles and one output handle", () => {
      const { container } = render(
        <FlowWrapper>
          <AddNode
            id="add-1"
            data={{ label: "Add" }}
            selected={false}
            type="Add"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const targetHandles = container.querySelectorAll(
        '.react-flow__handle[data-handlepos="left"]'
      );
      const sourceHandles = container.querySelectorAll(
        '.react-flow__handle[data-handlepos="right"]'
      );
      expect(targetHandles).toHaveLength(2);
      expect(sourceHandles).toHaveLength(1);
    });
  });

  describe("SubtractNode", () => {
    it("renders with Subtract label", () => {
      render(
        <FlowWrapper>
          <SubtractNode
            id="sub-1"
            data={{ label: "Subtract" }}
            selected={false}
            type="Subtract"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      expect(screen.getByText("−")).toBeInTheDocument();
    });

    it("has two input handles and one output handle", () => {
      const { container } = render(
        <FlowWrapper>
          <SubtractNode
            id="sub-1"
            data={{ label: "Subtract" }}
            selected={false}
            type="Subtract"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const targetHandles = container.querySelectorAll(
        '.react-flow__handle[data-handlepos="left"]'
      );
      const sourceHandles = container.querySelectorAll(
        '.react-flow__handle[data-handlepos="right"]'
      );
      expect(targetHandles).toHaveLength(2);
      expect(sourceHandles).toHaveLength(1);
    });
  });

  describe("WhileLoopNode", () => {
    it("renders with While Loop label", () => {
      render(
        <FlowWrapper>
          <WhileLoopNode
            id="loop-1"
            data={{ label: "While Loop" }}
            selected={false}
            type="WhileLoop"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      expect(screen.getByText(/While Loop/)).toBeInTheDocument();
    });

    it("has an input tunnel (target handle) and output tunnel (source handle)", () => {
      const { container } = render(
        <FlowWrapper>
          <WhileLoopNode
            id="loop-1"
            data={{ label: "While Loop" }}
            selected={false}
            type="WhileLoop"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const targetHandles = container.querySelectorAll(
        '.react-flow__handle[data-handlepos="left"]'
      );
      const sourceHandles = container.querySelectorAll(
        '.react-flow__handle[data-handlepos="right"]'
      );
      expect(targetHandles).toHaveLength(1);
      expect(sourceHandles).toHaveLength(1);
    });

    it("shows selection visual feedback when selected", () => {
      const { container } = render(
        <FlowWrapper>
          <WhileLoopNode
            id="loop-1"
            data={{ label: "While Loop" }}
            selected={true}
            type="WhileLoop"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const nodeEl = container.firstElementChild as HTMLElement;
      expect(nodeEl.className).toContain("border-cyan-500");
    });

    it("renders at default size when no dimensions specified", () => {
      const { container } = render(
        <FlowWrapper>
          <WhileLoopNode
            id="loop-1"
            data={{ label: "While Loop" }}
            selected={false}
            type="WhileLoop"
            zIndex={0}
            isConnectable={true}
            xPos={0}
            yPos={0}
            dragging={false}
          />
        </FlowWrapper>
      );
      const nodeEl = container.firstElementChild as HTMLElement;
      expect(nodeEl.style.width).toBe("320px");
      expect(nodeEl.style.height).toBe("220px");
    });
  });

  describe("NODE_TYPES registry", () => {
    it("exports all five custom node types including WhileLoop", () => {
      expect(NODE_TYPES).toHaveProperty("NumericControl");
      expect(NODE_TYPES).toHaveProperty("NumericIndicator");
      expect(NODE_TYPES).toHaveProperty("Add");
      expect(NODE_TYPES).toHaveProperty("Subtract");
      expect(NODE_TYPES).toHaveProperty("WhileLoop");
    });
  });
});
