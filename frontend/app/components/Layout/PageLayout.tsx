import type { ReactNode } from "react";
import Sidebar from "../Sidebar";

interface PageLayoutProps {
  children: ReactNode;
  activePath: string;
  backgroundImage?: string;
}

export function PageLayout({ children, activePath, backgroundImage }: PageLayoutProps) {
  const bgStyle = backgroundImage ? {
    backgroundImage: `url(${backgroundImage})`,
    backgroundSize: "cover",
    backgroundPosition: "center top",
  } : { background: "var(--bg-dark)" };

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "var(--font-body)", ...bgStyle }}>
      <Sidebar activePath={activePath} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {children}
      </div>
    </div>
  );
}
