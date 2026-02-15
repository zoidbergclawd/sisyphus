import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FrontPanel from "./FrontPanel";
import type { Node } from "reactflow";

/** Helper to create test nodes */
function makeControl(id: string, label: string, value: number): Node {
  return { id, type: "NumericControl", position: { x: 0, y: 0 }, data: { label, value } };
}

function makeIndicator(id: string, label: string, value: number): Node {
  return { id, type: "NumericIndicator", position: { x: 0, y: 0 }, data: { label, value } };
}

function makeAdd(id: string): Node {
  return { id, type: "Add", position: { x: 0, y: 0 }, data: { label: "Add" } };
}

describe("FrontPanel", () => {
  it("renders controls and indicators from diagram nodes", () => {
    const nodes: Node[] = [
      makeControl("ctrl-a", "A", 3),
      makeControl("ctrl-b", "B", 7),
      makeAdd("add-1"),
      makeIndicator("ind-result", "Result", 10),
    ];
    const onChange = vi.fn();

    render(<FrontPanel nodes={nodes} onNodeDataChange={onChange} isRunning={false} />);

    // Controls section shows both controls
    expect(screen.getByLabelText("A")).toBeInTheDocument();
    expect(screen.getByLabelText("B")).toBeInTheDocument();

    // Indicator section shows the indicator
    expect(screen.getByText("Result")).toBeInTheDocument();
    expect(screen.getByTestId("panel-ind-ind-result")).toHaveTextContent("10");

    // Non-control/indicator nodes (Add) should NOT appear
    expect(screen.queryByText("Add")).not.toBeInTheDocument();
  });

  it("only shows NumericControl nodes in Controls section, not other types", () => {
    const nodes: Node[] = [
      makeControl("ctrl-a", "Speed", 50),
      makeAdd("add-1"),
      makeIndicator("ind-out", "Output", 0),
    ];
    const onChange = vi.fn();

    render(<FrontPanel nodes={nodes} onNodeDataChange={onChange} isRunning={false} />);

    // Only one control input should exist
    const inputs = screen.getAllByRole("spinbutton");
    expect(inputs).toHaveLength(1);
    expect(screen.getByLabelText("Speed")).toBeInTheDocument();
  });

  it("calls onNodeDataChange when a control value is edited", () => {
    const nodes: Node[] = [makeControl("ctrl-a", "A", 3)];
    const onChange = vi.fn();

    render(<FrontPanel nodes={nodes} onNodeDataChange={onChange} isRunning={false} />);

    const input = screen.getByLabelText("A") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "42" } });

    expect(onChange).toHaveBeenCalledWith("ctrl-a", { value: 42 });
  });

  it("displays indicator values as read-only (no input element)", () => {
    const nodes: Node[] = [makeIndicator("ind-1", "Result", 99)];
    const onChange = vi.fn();

    render(<FrontPanel nodes={nodes} onNodeDataChange={onChange} isRunning={false} />);

    // The indicator value should be displayed as text, not an input
    expect(screen.getByTestId("panel-ind-ind-1")).toHaveTextContent("99");
    // No spinbutton for indicators
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  });

  it("shows empty state messages when no controls or indicators exist", () => {
    const nodes: Node[] = [makeAdd("add-1")];
    const onChange = vi.fn();

    render(<FrontPanel nodes={nodes} onNodeDataChange={onChange} isRunning={false} />);

    expect(screen.getByText(/No controls on diagram/)).toBeInTheDocument();
    expect(screen.getByText(/No indicators on diagram/)).toBeInTheDocument();
  });

  it("shows running indicator when isRunning is true", () => {
    const nodes: Node[] = [makeControl("ctrl-a", "A", 0)];
    const onChange = vi.fn();

    render(<FrontPanel nodes={nodes} onNodeDataChange={onChange} isRunning={true} />);

    expect(screen.getByTestId("panel-running")).toBeInTheDocument();
    expect(screen.getByText("Executing...")).toBeInTheDocument();
  });

  it("does not show running indicator when isRunning is false", () => {
    const nodes: Node[] = [makeControl("ctrl-a", "A", 0)];
    const onChange = vi.fn();

    render(<FrontPanel nodes={nodes} onNodeDataChange={onChange} isRunning={false} />);

    expect(screen.queryByTestId("panel-running")).not.toBeInTheDocument();
  });

  it("updates displayed indicator values when nodes prop changes", () => {
    const nodes: Node[] = [makeIndicator("ind-1", "Result", 0)];
    const onChange = vi.fn();

    const { rerender } = render(
      <FrontPanel nodes={nodes} onNodeDataChange={onChange} isRunning={false} />
    );

    expect(screen.getByTestId("panel-ind-ind-1")).toHaveTextContent("0");

    // Simulate new value after execution
    const updatedNodes: Node[] = [makeIndicator("ind-1", "Result", 42)];
    rerender(
      <FrontPanel nodes={updatedNodes} onNodeDataChange={onChange} isRunning={false} />
    );

    expect(screen.getByTestId("panel-ind-ind-1")).toHaveTextContent("42");
  });

  it("renders the front-panel container", () => {
    const nodes: Node[] = [];
    const onChange = vi.fn();

    render(<FrontPanel nodes={nodes} onNodeDataChange={onChange} isRunning={false} />);

    expect(screen.getByTestId("front-panel")).toBeInTheDocument();
  });
});
