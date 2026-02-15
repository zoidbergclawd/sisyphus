import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useState, useCallback } from "react";
import VIWorkspace from "./VIWorkspace";
import type { Node, Edge } from "reactflow";

/**
 * Mock React Flow — it requires browser layout APIs unavailable in jsdom.
 * We provide stateful mocks for useNodesState/useEdgesState so that
 * VIWorkspace can manage real data flow between DiagramEditor and FrontPanel.
 */
vi.mock("reactflow", async () => {
  const actual = await vi.importActual<typeof import("reactflow")>("reactflow");

  function useNodesStateMock(initialNodes: Node[]) {
    const [nodes, setNodes] = useState<Node[]>(initialNodes);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const onNodesChange = useCallback((..._args: unknown[]) => {}, []);
    return [nodes, setNodes, onNodesChange] as const;
  }

  function useEdgesStateMock(initialEdges: Edge[]) {
    const [edges, setEdges] = useState<Edge[]>(initialEdges);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const onEdgesChange = useCallback((..._args: unknown[]) => {}, []);
    return [edges, setEdges, onEdgesChange] as const;
  }

  return {
    ...actual,
    default: ({ nodes }: { nodes: Node[] }) => (
      <div data-testid="react-flow-mock">{JSON.stringify(nodes.map((n) => n.id))}</div>
    ),
    ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    useNodesState: useNodesStateMock,
    useEdgesState: useEdgesStateMock,
    Controls: () => null,
    Background: () => null,
  };
});

describe("VIWorkspace", () => {
  it("renders the diagram view by default", () => {
    render(<VIWorkspace />);
    expect(screen.getByText("Palette")).toBeInTheDocument();
  });

  it("has a Panel toggle button", () => {
    render(<VIWorkspace />);
    expect(screen.getByRole("button", { name: /panel/i })).toBeInTheDocument();
  });

  it("shows the Front Panel when the Panel toggle is clicked", () => {
    render(<VIWorkspace />);
    const toggle = screen.getByRole("button", { name: /panel/i });
    fireEvent.click(toggle);
    expect(screen.getByTestId("front-panel")).toBeInTheDocument();
  });

  it("renders controls from diagram nodes on the Front Panel", () => {
    render(<VIWorkspace />);
    const toggle = screen.getByRole("button", { name: /panel/i });
    fireEvent.click(toggle);
    // The initial nodes include ctrl-a (A=3) and ctrl-b (B=7) which are NumericControls
    expect(screen.getByLabelText("A")).toBeInTheDocument();
    expect(screen.getByLabelText("B")).toBeInTheDocument();
  });

  it("renders indicators from diagram nodes on the Front Panel", () => {
    render(<VIWorkspace />);
    const toggle = screen.getByRole("button", { name: /panel/i });
    fireEvent.click(toggle);
    // The initial nodes include ind-result (Result=0) which is a NumericIndicator
    expect(screen.getByTestId("panel-ind-ind-result")).toHaveTextContent("0");
  });

  it("updates diagram node data when a Front Panel control value changes", () => {
    render(<VIWorkspace />);
    const toggle = screen.getByRole("button", { name: /panel/i });
    fireEvent.click(toggle);

    const input = screen.getByLabelText("A") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "42" } });

    // The control should now show the updated value
    expect(input.value).toBe("42");
  });

  it("can hide the Front Panel by clicking the toggle again", () => {
    render(<VIWorkspace />);
    const toggle = screen.getByRole("button", { name: /panel/i });
    fireEvent.click(toggle); // show
    expect(screen.getByTestId("front-panel")).toBeInTheDocument();
    fireEvent.click(toggle); // hide
    expect(screen.queryByTestId("front-panel")).not.toBeInTheDocument();
  });
});
