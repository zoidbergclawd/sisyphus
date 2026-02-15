import dynamic from "next/dynamic";

/** React Flow requires browser APIs — load client-only */
const VIWorkspace = dynamic(
  () => import("@/components/VIWorkspace"),
  { ssr: false }
);

export default function Home() {
  return <VIWorkspace />;
}
