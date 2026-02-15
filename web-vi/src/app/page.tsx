import dynamic from "next/dynamic";

/** React Flow requires browser APIs — load client-only */
const DiagramEditor = dynamic(
  () => import("@/components/DiagramEditor"),
  { ssr: false }
);

export default function Home() {
  return <DiagramEditor />;
}
