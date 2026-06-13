import type { ReactNode } from "react";

interface TopBarProps {
  title: string;
  subtitle?: string;
  rightElement?: ReactNode;
}

export function TopBar({ title, subtitle = "MLB · 2026", rightElement }: TopBarProps) {
  return (
    <div className="top-bar" style={{
      padding: "18px 24px",
      borderBottom: "0.5px solid rgba(255,255,255,0.06)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      flexShrink: 0,
    }}>
      <div>
        <div style={{
          fontSize: 14,
          fontWeight: 600,
          color: "rgba(255,255,255,0.65)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          marginBottom: 4,
        }}>
          {subtitle}
        </div>
        <h1 style={{
          fontFamily: "var(--font-display)",
          fontSize: 36,
          fontWeight: 700,
          color: "var(--text-primary)",
          margin: 0,
        }}>
          {title}
        </h1>
      </div>
      {rightElement || (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          background: "rgba(255,255,255,0.04)",
          border: "0.5px solid rgba(255,255,255,0.2)",
          borderRadius: 6,
          padding: "6px 12px",
          fontSize: 14,
          color: "white",
        }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--mlb-green)" }} />
          2026 Season
        </div>
      )}
    </div>
  );
}
