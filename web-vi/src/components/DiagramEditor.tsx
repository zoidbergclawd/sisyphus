"use client";

import { useCallback, useRef, useMemo } from "react";
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  type Connection,
  type Edge,
  type Node,
  type ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";
import { NODE_TYPES } from "./nodes";

/** Initial demo nodes to populate the canvas */
const INITIAL_NODES: Node[] = [
  {
    id: "ctrl-a",
    type: "NumericControl",
    position: { x: 80, y: 100 },
    data: { label: "A", value: 3 },
  },
  {
    id: "ctrl-b",
    type: "NumericControl",
    position: { x: 80, y: 260 },
    data: { label: "B", value: 7 },
  },
  {
    id: "add-1",
    type: "Add",
    position: { x: 320, y: 160 },
    data: { label: "Add" },
  },
  {
    id: "ind-result",
    type: "NumericIndicator",
    position: { x: 520, y: 160 },
    data: { label: "Result", value: 0 },
  },
];

const INITIAL_EDGES: Edge[] = [];

/** Unique ID counter for new nodes dragged from the palette */
let idCounter = 0;
function nextId(prefix: string): string {
  return `${prefix}-${++idCounter}`;
}

/** Palette items that can be dragged onto the canvas */
const PALETTE_ITEMS = [
  { type: "NumericControl", label: "Numeric Control" },
  { type: "NumericIndicator", label: "Numeric Indicator" },
  { type: "Add", label: "Add" },
  { type: "Subtract", label: "Subtract" },
] as const;

/** Default data for each node type when created via palette drag */
const DEFAULT_DATA: Record<string, Record<string, unknown>> = {
  NumericControl: { label: "Value", value: 0 },
  NumericIndicator: { label: "Output", value: 0 },
  Add: { label: "Add" },
  Subtract: { label: "Subtract" },
};

export default function DiagramEditor() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);

  /** Handle new connections between nodes */
  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            style: { stroke: "#22d3ee", strokeWidth: 2 },
            animated: true,
          },
          eds
        )
      );
    },
    [setEdges]
  );

  /** Update node data (e.g. when a NumericControl value changes) */
  const updateNodeData = useCallback(
    (nodeId: string, newData: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, ...newData } } : n
        )
      );
    },
    [setNodes]
  );

  /** Inject onChange callbacks into NumericControl nodes */
  const nodesWithCallbacks = useMemo(
    () =>
      nodes.map((node) => {
        if (node.type === "NumericControl") {
          return {
            ...node,
            data: {
              ...node.data,
              onChange: (value: number) =>
                updateNodeData(node.id, { value }),
            },
          };
        }
        return node;
      }),
    [nodes, updateNodeData]
  );

  /** Palette drag start — store the node type in the drag transfer */
  const onDragStart = useCallback(
    (event: React.DragEvent, nodeType: string) => {
      event.dataTransfer.setData("application/reactflow", nodeType);
      event.dataTransfer.effectAllowed = "move";
    },
    []
  );

  /** Handle drop from palette onto the canvas */
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const nodeType = event.dataTransfer.getData("application/reactflow");
      if (!nodeType || !reactFlowInstance.current || !reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.current.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      const newNode: Node = {
        id: nextId(nodeType.toLowerCase()),
        type: nodeType,
        position,
        data: { ...DEFAULT_DATA[nodeType] },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [setNodes]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  return (
    <div className="flex h-screen w-screen bg-gray-950">
      {/* Palette sidebar */}
      <aside className="flex w-52 flex-col border-r border-gray-800 bg-gray-900 p-3">
        <h2 className="mb-3 text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500">
          Palette
        </h2>
        <div className="flex flex-col gap-1.5">
          {PALETTE_ITEMS.map((item) => (
            <div
              key={item.type}
              className="cursor-grab rounded border border-gray-700 bg-gray-800 px-3 py-2 text-xs font-medium text-gray-300 transition-colors hover:border-cyan-700 hover:bg-gray-750 hover:text-cyan-300 active:cursor-grabbing"
              draggable
              onDragStart={(e) => onDragStart(e, item.type)}
            >
              {item.label}
            </div>
          ))}
        </div>
        <div className="mt-auto pt-4 text-[10px] text-gray-600">
          Drag nodes onto the canvas. Connect outputs to inputs.
        </div>
      </aside>

      {/* React Flow canvas */}
      <div className="flex-1" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodesWithCallbacks}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={(instance) => {
            reactFlowInstance.current = instance;
          }}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={NODE_TYPES}
          fitView
          snapToGrid
          snapGrid={[16, 16]}
          defaultEdgeOptions={{
            style: { stroke: "#22d3ee", strokeWidth: 2 },
            animated: true,
          }}
          proOptions={{ hideAttribution: true }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={16}
            size={1}
            color="#1e293b"
          />
          <Controls
            className="!bg-gray-800 !border-gray-700 !shadow-lg [&>button]:!bg-gray-800 [&>button]:!border-gray-700 [&>button]:!text-gray-400 [&>button:hover]:!bg-gray-700"
          />
        </ReactFlow>
      </div>
    </div>
  );
}
